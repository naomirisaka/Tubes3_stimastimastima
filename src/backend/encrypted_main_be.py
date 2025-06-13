# backend/encrypted_main_be.py
"""
Encrypted backend adapter that maintains compatibility with existing frontend
Put this file in your backend/ folder to replace main_be.py when using encryption
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import asdict
import os
import sys
import time
from pathlib import Path

# Add path to data_extractor for encryption imports
data_extractor_path = Path(__file__).parent.parent / "data_extractor"
sys.path.insert(0, str(data_extractor_path))

try:
    from data_extractor.encryption import ATSCryptoManager, EncryptedDatabaseManager, get_crypto_manager, get_database_connection
    print("✅ Successfully imported encryption modules from data_extractor")
except ImportError as e:
    print(f"❌ Failed to import encryption modules: {e}")
    print("Make sure encryption.py is in your data_extractor folder")
    sys.exit(1)

# Import backend modules for string matching algorithms
try:
    import kmp
    import boyer_moore
    import aho_corasick
    import levenshtein
    print("✅ Successfully imported search algorithms from backend")
except ImportError as e:
    print(f"❌ Failed to import search algorithms: {e}")
    print("Make sure your backend folder has the algorithm files")
    sys.exit(1)

class EncryptedSearchEngine:
    """Search engine that works with encrypted CV data"""
    
    def __init__(self, crypto_manager: ATSCryptoManager):
        self.crypto = crypto_manager
        self.db = EncryptedDatabaseManager(crypto_manager)
        self.cv_cache = {}
        self.cache_loaded = False
    
    def load_encrypted_cv_cache(self):
        """Load and decrypt CVs into memory for searching"""
        if self.cache_loaded:
            return
        
        if not self.db.connect():
            raise Exception("Failed to connect to encrypted database")
        
        cursor = self.db.connection.cursor()
        
        try:
            print("🔓 Decrypting CV cache for search...")
            cursor.execute("SELECT detail_id, cv_raw_text_enc FROM ApplicationDetailEncrypted")
            encrypted_cvs = cursor.fetchall()
            
            self.cv_cache = {}
            decrypted_count = 0
            
            for detail_id, cv_raw_text_enc in encrypted_cvs:
                try:
                    # Decrypt CV text and store in cache
                    decrypted_text = self.crypto.decrypt_large_text(cv_raw_text_enc)
                    if decrypted_text:
                        self.cv_cache[detail_id] = decrypted_text.lower()
                        decrypted_count += 1
                except Exception as e:
                    print(f"Warning: Failed to decrypt CV {detail_id}: {e}")
                    continue
            
            self.cache_loaded = True
            print(f"✅ Loaded {decrypted_count} decrypted CVs into search cache")
            
        finally:
            cursor.close()
            self.db.disconnect()
    
    def search_keywords(self, keywords_str: str, algorithm: str = "kmp", top_n: int = 10):
        """Search keywords in encrypted CVs"""
        self.load_encrypted_cv_cache()
        
        keywords = [kw.strip().lower() for kw in keywords_str.split(',') if kw.strip()]
        if not keywords:
            return []
        
        # Search in decrypted cache
        cv_matches = {}
        
        for detail_id, cv_text in self.cv_cache.items():
            keyword_counts = {}
            
            for keyword in keywords:
                if algorithm == "kmp":
                    matches = kmp.kmp_search(cv_text, keyword)
                    keyword_counts[keyword] = len(matches)
                elif algorithm == "boyer_moore":
                    matches = boyer_moore.boyer_moore_search(cv_text, keyword)
                    keyword_counts[keyword] = len(matches)
                elif algorithm == "aho_corasick":
                    # For AC, we need to pass all keywords at once
                    if keyword not in cv_matches:  # Only run AC once per CV
                        ac_results = aho_corasick.aho_corasick_search(cv_text, keywords)
                        for kw in keywords:
                            keyword_counts[kw] = len(ac_results.get(kw, []))
                        break  # We've processed all keywords for this CV
                else:  # Simple count fallback
                    keyword_counts[keyword] = cv_text.count(keyword)
            
            total_matches = sum(keyword_counts.values())
            if total_matches > 0:
                cv_matches[detail_id] = {
                    'total_matches': total_matches,
                    'keyword_matches': keyword_counts
                }
        
        # Get top matches and decrypt their details
        sorted_matches = sorted(cv_matches.items(), key=lambda x: x[1]['total_matches'], reverse=True)
        top_matches = sorted_matches[:top_n]
        
        results = []
        for detail_id, match_data in top_matches:
            app_data = self.db.get_decrypted_application(detail_id)
            if app_data:
                app_data.update(match_data)
                results.append(app_data)
        
        return results
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics from encrypted database"""
        if not self.db.connect():
            return {}
        
        cursor = self.db.connection.cursor()
        
        try:
            # Get basic stats
            cursor.execute("SELECT COUNT(*) FROM ApplicantProfileEncrypted")
            total_applicants = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ApplicationDetailEncrypted")
            total_applications = cursor.fetchone()[0]
            
            return {
                "total_applicants": total_applicants,
                "total_applications": total_applications,
                "encryption_status": "🔐 ENCRYPTED"
            }
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
        finally:
            cursor.close()
            self.db.disconnect()

class EncryptedATSBackend:
    """
    Encrypted version of ATS Backend that maintains the same interface
    as the original backend but works with encrypted data.
    """
    
    def __init__(self):
        self.crypto_manager = get_crypto_manager()
        self.db_manager = get_database_connection()
        self.search_engine = EncryptedSearchEngine(self.crypto_manager)
        self._cache_loaded = False
    
    def initialize(self) -> bool:
        """Initialize the encrypted backend connection."""
        try:
            # Test database connection
            if not self.db_manager.connect():
                print("Failed to connect to encrypted database")
                return False
            
            self.db_manager.disconnect()
            
            # Load CV cache for faster searching (this decrypts CVs into memory)
            self.search_engine.load_encrypted_cv_cache()
            self._cache_loaded = True
            
            print("🔐 Encrypted ATS Backend initialized successfully")
            return True
        
        except Exception as e:
            print(f"Encrypted backend initialization failed: {e}")
            return False
    
    def search_cvs(self, keywords: str, algorithm: str = "kmp", 
                   top_results: int = 10, fuzzy_threshold: float = 70.0) -> Dict:
        """
        Search CVs using encrypted backend - maintains same interface as original.
        """
        if not self._cache_loaded:
            if not self.initialize():
                return {"error": "Encrypted backend not initialized"}
        
        try:
            start_time = time.time()
            
            # Use encrypted search engine
            cv_matches = self.search_engine.search_keywords(
                keywords_str=keywords,
                algorithm=algorithm,
                top_n=top_results
            )
            
            search_time = (time.time() - start_time) * 1000
            
            # Convert to original backend format
            keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
            
            # Calculate exact matches for compatibility
            exact_matches = {}
            for keyword in keywords_list:
                total_count = 0
                for cv in cv_matches:
                    total_count += cv.get('keyword_matches', {}).get(keyword, 0)
                exact_matches[keyword] = total_count
            
            return {
                "success": True,
                "search_metadata": {
                    "keywords_searched": keywords_list,
                    "algorithm_used": algorithm,
                    "exact_match_time_ms": round(search_time, 2),
                    "fuzzy_match_time_ms": 0.0,  # Not implemented in encrypted version
                    "total_cvs_scanned": len(self.search_engine.cv_cache)
                },
                "exact_matches": exact_matches,
                "fuzzy_matches": {},  # Not implemented in encrypted version
                "cv_results": [
                    {
                        "detail_id": cv['detail_id'],
                        "applicant_name": f"{cv['first_name']} {cv['last_name']}",
                        "application_role": cv['role'],
                        "total_matches": cv['total_matches'],
                        "keyword_matches": cv['keyword_matches'],
                        "similarity_score": cv['total_matches']
                    }
                    for cv in cv_matches
                ]
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Encrypted search failed: {str(e)}"
            }
    
    def get_cv_summary(self, detail_id: int) -> Dict:
        """Get CV summary from encrypted database."""
        try:
            app_data = self.db_manager.get_decrypted_application(detail_id)
            
            if not app_data:
                return {
                    "success": False,
                    "error": "CV summary not found"
                }
            
            return {
                "success": True,
                "summary": {
                    "name": f"{app_data['first_name']} {app_data['last_name']}",
                    "phone": app_data['phone'],
                    "address": app_data['address'],
                    "role": app_data['role'],
                    "summary": app_data['summary'],
                    "skills": app_data['skills'],
                    "experience": app_data['experience'],
                    "education": app_data['education'],
                    "accomplishments": app_data['accomplishments'],
                    "cv_path": app_data['cv_path']
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get encrypted summary: {str(e)}"
            }
    
    def get_cv_file_path(self, detail_id: int) -> str:
        """Get CV file path from encrypted database."""
        try:
            app_data = self.db_manager.get_decrypted_application(detail_id)
            return app_data.get('cv_path', '') if app_data else ''
        
        except Exception as e:
            print(f"Error getting encrypted CV path: {e}")
            return ''
    
    def get_database_statistics(self) -> Dict:
        """Get database statistics from encrypted database."""
        try:
            stats = self.search_engine.get_database_stats()
            return {
                "success": True,
                "stats": stats
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get encrypted stats: {str(e)}"
            }
    
    def get_available_algorithms(self) -> List[str]:
        """Get available search algorithms."""
        return ["kmp", "boyer_moore", "aho_corasick"]
    
    def validate_keywords(self, keywords: str) -> Dict:
        """Validate keywords input."""
        if not keywords or not keywords.strip():
            return {
                "valid": False,
                "error": "Keywords cannot be empty"
            }
        
        keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        
        if not keyword_list:
            return {
                "valid": False,
                "error": "No valid keywords found"
            }
        
        if len(keyword_list) > 20:
            return {
                "valid": False,
                "error": "Too many keywords (maximum 20)"
            }
        
        return {
            "valid": True,
            "keyword_count": len(keyword_list),
            "keywords": keyword_list
        }

# Global encrypted backend instance
encrypted_backend = EncryptedATSBackend()

def get_ats_backend():
    """
    Get the encrypted ATS backend.
    This function maintains compatibility with existing frontend code.
    """
    return encrypted_backend

# Convenience functions for easy usage (maintains original API)
def quick_search(keywords: str, algorithm: str = "kmp", top_n: int = 10) -> Dict:
    """Quick search using encrypted backend."""
    backend = get_ats_backend()
    if not backend._cache_loaded:
        backend.initialize()
    
    return backend.search_cvs(keywords, algorithm, top_n)

def get_summary(detail_id: int) -> Dict:
    """Get summary using encrypted backend."""
    backend = get_ats_backend()
    return backend.get_cv_summary(detail_id)

def demo_encrypted_backend():
    """Demo the encrypted backend functionality."""
    print("🔐 ENCRYPTED ATS BACKEND DEMO")
    print("=" * 50)
    
    backend = get_ats_backend()
    
    if not backend.initialize():
        print("❌ Failed to initialize encrypted backend")
        return
    
    # Demo search
    print("\n🔍 Testing encrypted search...")
    keywords = "Python, Java, programming"
    
    results = backend.search_cvs(keywords, "kmp", 3)
    
    if results.get('success'):
        metadata = results['search_metadata']
        print(f"✅ Search completed in {metadata['exact_match_time_ms']}ms")
        print(f"📊 Scanned {metadata['total_cvs_scanned']} encrypted CVs")
        
        cv_results = results['cv_results']
        if cv_results:
            print(f"🥇 Top result: {cv_results[0]['applicant_name']}")
            print(f"      Role: {cv_results[0]['application_role']}")
            print(f"      Score: {cv_results[0]['total_matches']}")
            
            # Get detailed summary
            detail_id = cv_results[0]['detail_id']
            summary_result = backend.get_cv_summary(detail_id)
            if summary_result.get('success'):
                summary = summary_result['summary']
                print(f"      Phone: {summary['phone']}")
                print(f"      Skills preview: {summary['skills'][:100]}...")
        else:
            print("   📝 No matching CVs found")
    else:
        print(f"   ❌ Search failed: {results.get('error')}")
    
    # Show database stats
    stats_result = backend.get_database_statistics()
    if stats_result.get('success'):
        stats = stats_result['stats']
        print(f"\n🔐 ENCRYPTED DATABASE STATISTICS:")
        print(f"   Total Applicants: {stats['total_applicants']}")
        print(f"   Total Applications: {stats['total_applications']}")
        print(f"   Status: {stats['encryption_status']}")
    
    print(f"\n✅ ENCRYPTED BACKEND DEMO COMPLETED!")
    print(f"🔐 All data was encrypted at rest and decrypted only for search!")

if __name__ == "__main__":
    print("🔐 ENCRYPTED ATS BACKEND SYSTEM")
    print("=" * 40)
    
    choice = input("Choose demo:\n1. Encrypted backend demo\n2. Test connection\n3. Quick search test\nChoice: ")
    
    if choice == "1":
        demo_encrypted_backend()
    
    elif choice == "2":
        print("\n🔌 Testing encrypted backend connection...")
        backend = get_ats_backend()
        if backend.initialize():
            print("✅ Connection successful!")
            stats = backend.get_database_statistics()
            if stats.get('success'):
                print(f"📊 Found {stats['stats']['total_applications']} encrypted CVs")
        else:
            print("❌ Connection failed!")
    
    elif choice == "3":
        print("\n🔍 Quick search test...")
        keywords = input("Enter keywords: ").strip()
        if keywords:
            results = quick_search(keywords, "kmp", 3)
            if results.get('success'):
                print(f"Found {len(results.get('cv_results', []))} matches")
                for cv in results.get('cv_results', [])[:3]:
                    print(f"- {cv['applicant_name']}: {cv['total_matches']} matches")
            else:
                print(f"Search failed: {results.get('error')}")
        else:
            print("No keywords provided")
    
    else:
        print("❌ Invalid choice")
        
    print(f"\n💡 To use encrypted backend in your frontend:")
    print(f"   1. Replace import: from main_be import get_ats_backend")
    print(f"   2. With: from encrypted_main_be import get_ats_backend")
    print(f"   3. Set: export ATS_MASTER_KEY='your_master_password'")