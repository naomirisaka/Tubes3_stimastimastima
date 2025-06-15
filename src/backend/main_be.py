from typing import List, Dict, Tuple, Optional
from dataclasses import asdict
import os

import database
import search_engine
from data_extractor.extractor import extract_realtime, insert_application_detail, insert_applicant_profile, EncryptionManager, ExtractionResult
# Add this to the TOP of main_be.py after other imports

try:
    from cv_cache_manager import cv_cache_manager, initialize_cv_cache
    print("✅ Successfully imported cv_cache_manager")
    USE_CACHE_MANAGER = True
except ImportError as e:
    print(f"⚠️ Could not import cv_cache_manager: {e}")
    USE_CACHE_MANAGER = False

class ATSBackend:
    def __init__(self):
        self.search_engine = search_engine.DatabaseCVSearchEngine()
        self.db_manager = database.get_database_connection()
        self._cache_loaded = False
        self.encryption = EncryptionManager()
        self.encryption.initialize()  # Bisa tambahkan password jika terenkripsi

    def extract_and_insert_cv(self, cv_path: str, applicant_profile: dict) -> Dict:
        try:
            # Lakukan ekstraksi PDF
            result: ExtractionResult = extract_realtime(cv_path)

            if not result.success:
                return {
                    "success": False,
                    "error": f"Extraction failed: {result.error_message}"
                }

            # Masukkan profil pelamar ke DB
            applicant_id = insert_applicant_profile(applicant_profile, encrypt=self.encryption.encryption_enabled)

            # Masukkan detail aplikasi
            insert_application_detail(applicant_id, cv_path, result, encrypt=self.encryption.encryption_enabled)

            return {
                "success": True,
                "applicant_id": applicant_id
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Exception occurred: {str(e)}"
            }

    def search_cvs(self, keywords: str, algorithm: str = "kmp", 
                top_results: int = 10, fuzzy_threshold: float = 70.0) -> Dict:

        if not self._cache_loaded:
            if not self.initialize():
                return {"error": "Backend not initialized"}
        
        try:
            if USE_CACHE_MANAGER:
                print("🔍 Using cv_cache_manager for search...")
                # Use the cache manager's search functionality
                keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
                
                # Get cached results
                results = cv_cache_manager.search_keywords(keyword_list, algorithm)
                
                # Convert to expected format
                return {
                    "success": True,
                    "search_metadata": {
                        "keywords_searched": keyword_list,
                        "algorithm_used": algorithm,
                        "exact_match_time_ms": 0.0,  # Cache manager doesn't track time separately
                        "fuzzy_match_time_ms": 0.0,
                        "total_cvs_scanned": len(cv_cache_manager.memory_cache)
                    },
                    "exact_matches": {kw: 0 for kw in keyword_list},  # Simplified
                    "fuzzy_matches": {},
                    "cv_results": results[:top_results]
                }
            else:
                # Fall back to original search engine
                result, cv_matches = search_engine.search_database_cvs(
                    keywords=keywords,
                    algorithm=algorithm,
                    top_n=top_results,
                    fuzzy_threshold=fuzzy_threshold
                )
                
                # Convert to dictionary format for easy GUI consumption
                return {
                    "success": True,
                    "search_metadata": {
                        "keywords_searched": result.keywords_searched,
                        "algorithm_used": result.algorithm_used,
                        "exact_match_time_ms": round(result.exact_match_time, 2),
                        "fuzzy_match_time_ms": round(result.fuzzy_match_time, 2),
                        "total_cvs_scanned": result.total_cvs_scanned
                    },
                    "exact_matches": result.exact_matches,
                    "fuzzy_matches": result.fuzzy_matches,
                    "cv_results": [
                        {
                            "detail_id": cv.detail_id,
                            "applicant_name": cv.applicant_name,
                            "application_role": cv.application_role,
                            "total_matches": cv.total_matches,
                            "keyword_matches": cv.keyword_matches,
                            "similarity_score": cv.similarity_score
                        }
                        for cv in cv_matches
                    ]
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Search failed: {str(e)}"
            }
    
    def get_cv_summary(self, detail_id: int) -> Dict:
        try:
            summary = search_engine.get_cv_summary_by_id(detail_id)
            
            if not summary:
                return {
                    "success": False,
                    "error": "CV summary not found"
                }
            
            return {
                "success": True,
                "summary": summary
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get summary: {str(e)}"
            }
    
    def get_cv_file_path(self, detail_id: int) -> str:
        try:
            summary = search_engine.get_cv_summary_by_id(detail_id)
            return summary.get('cv_path', '') if summary else ''
        
        except Exception as e:
            print(f"Error getting CV path: {e}")
            return ''
    
    def get_database_statistics(self) -> Dict:
        try:
            stats = self.search_engine.get_database_stats()
            return {
                "success": True,
                "stats": stats
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get stats: {str(e)}"
            }
    
    def get_available_algorithms(self) -> List[str]:
        return ["kmp", "boyer_moore", "aho_corasick"]
    
    def validate_keywords(self, keywords: str) -> Dict:
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

# Global backend instance
ats_backend = ATSBackend()

def get_ats_backend() -> ATSBackend:
    return ats_backend

# Convenience functions for simple usage
def quick_search(keywords: str, algorithm: str = "kmp", top_n: int = 10) -> Dict:
    backend = get_ats_backend()
    if not backend._cache_loaded:
        backend.initialize()
    
    return backend.search_cvs(keywords, algorithm, top_n)

def get_summary(detail_id: int) -> Dict:
    backend = get_ats_backend()
    return backend.get_cv_summary(detail_id)

# Example usage functions for testing
def demo_search_scenarios():
    print("DEMONSTRATING ATS BACKEND SEARCH SCENARIOS")
    print("=" * 60)
    
    backend = get_ats_backend()
    
    if not backend.initialize():
        print("Failed to initialize backend")
        return
    
    # Demo scenarios
    scenarios = [
        {
            "name": "Software Developer Search",
            "keywords": "Python, JavaScript, React, programming",
            "algorithm": "kmp"
        },
        {
            "name": "Data Science Search",
            "keywords": "machine learning, data analysis, Python",
            "algorithm": "boyer_moore"
        },
        {
            "name": "Multi-Pattern Search (Aho-Corasick)",
            "keywords": "Java, Spring, REST, API, microservices",
            "algorithm": "aho_corasick"
        },
        {
            "name": "Fuzzy Search Demo",
            "keywords": "Pyhton, Javscript, databse",  # Intentional typos
            "algorithm": "kmp"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Keywords: {scenario['keywords']}")
        print(f"   Algorithm: {scenario['algorithm']}")
        
        # Perform search
        results = backend.search_cvs(
            keywords=scenario['keywords'],
            algorithm=scenario['algorithm'],
            top_results=5,
            fuzzy_threshold=75.0
        )
        
        if results.get('success'):
            metadata = results['search_metadata']
            print(f"   Search completed in {metadata['exact_match_time_ms']}ms")
            print(f"   Scanned {metadata['total_cvs_scanned']} CVs")
            
            # Show exact matches
            exact_total = sum(results['exact_matches'].values())
            print(f"   Total exact matches: {exact_total}")
            
            # Show top results
            cv_results = results['cv_results']
            if cv_results:
                print(f"   Top result: {cv_results[0]['applicant_name']}")
                print(f"      Role: {cv_results[0]['application_role']}")
                print(f"      Score: {cv_results[0]['total_matches']}")
            else:
                print("   📝 No matching CVs found")
            
            # Show fuzzy matches if any
            fuzzy_count = sum(len(matches) for matches in results['fuzzy_matches'].values())
            if fuzzy_count > 0:
                print(f"   🔍 Fuzzy matches found: {fuzzy_count}")
        
        else:
            print(f"   Search failed: {results.get('error')}")

def demo_cv_summary():
    print("\nDEMONSTRATING CV SUMMARY RETRIEVAL")
    print("=" * 50)
    
    backend = get_ats_backend()
    
    search_results = backend.search_cvs("Python, engineer", "kmp", 3)
    
    if search_results.get('success') and search_results.get('cv_results'):
        cv_result = search_results['cv_results'][0]
        detail_id = cv_result['detail_id']
        
        print(f"Getting summary for: {cv_result['applicant_name']}")
        print(f"Detail ID: {detail_id}")
        
        summary_result = backend.get_cv_summary(detail_id)
        
        if summary_result.get('success'):
            summary = summary_result['summary']
            
            print(f"Summary retrieved successfully")
            print(f"   Name: {summary.get('name')}")
            print(f"   Phone: {summary.get('phone')}")
            print(f"   Role: {summary.get('role')}")

            sections = ['summary', 'skills', 'experience', 'education']
            for section in sections:
                content = summary.get(section, '')
                if content:
                    preview = content[:100] + "..." if len(content) > 100 else content
                    print(f"   {section.title()}: {preview}")

            cv_path = summary.get('cv_path', '')
            if cv_path:
                print(f"   CV File: {cv_path}")
        
        else:
            print(f"Failed to get summary: {summary_result.get('error')}")
    
    else:
        print("No search results available for summary demo")

if __name__ == "__main__":
    print("ATS BACKEND MAIN INTERFACE DEMO")
    print("=" * 60)
    
    try:
        demo_search_scenarios()
        demo_cv_summary()

        backend = get_ats_backend()
        stats_result = backend.get_database_statistics()
        
        if stats_result.get('success'):
            stats = stats_result['stats']
            print(f"\nDATABASE STATISTICS")
            print(f"   Total Applicants: {stats.get('total_applicants', 0)}")
            print(f"   Total Applications: {stats.get('total_applications', 0)}")
            
            roles_by_count = stats.get('applications_by_role', {})
            if roles_by_count:
                print(f"   Top Roles:")
                sorted_roles = sorted(roles_by_count.items(), key=lambda x: x[1], reverse=True)
                for role, count in sorted_roles[:5]:
                    print(f"     - {role}: {count}")
        
        print(f"\nBACKEND DEMO COMPLETED SUCCESSFULLY!")
        print(f"Your backend is ready for GUI integration!")
        
        print(f"\nQUICK INTEGRATION GUIDE:")
        print(f"   1. Import: from backend.main_be import get_ats_backend")
        print(f"   2. Initialize: backend = get_ats_backend()")
        print(f"   3. Setup: backend.initialize()")
        print(f"   4. Search: results = backend.search_cvs(keywords, algorithm)")
        print(f"   5. Summary: summary = backend.get_cv_summary(detail_id)")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()