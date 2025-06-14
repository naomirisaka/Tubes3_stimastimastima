# cv_cache_manager.py - Sistem caching untuk ATS

import os
import json
import time
import threading
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import sqlite3
import hashlib

from data_extractor.extractor import extract_realtime, ExtractionResult
import database

@dataclass
class CVCacheEntry:
    """Cache entry untuk setiap CV"""
    detail_id: int
    cv_path: str
    applicant_name: str
    application_role: str
    raw_text: str
    summary: str
    skills: str
    experience: str
    education: str
    accomplishments: str
    file_hash: str
    last_modified: float
    extraction_time: datetime
    keywords_index: Dict[str, List[int]]  # keyword -> positions

class CVCacheManager:
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            print(f"🔄 Creating NEW CVCacheManager instance")
            cls._instance = super(CVCacheManager, cls).__new__(cls)
        else:
            print(f"♻️ Returning EXISTING CVCacheManager instance (ID: {id(cls._instance)})")
        return cls._instance
        
    def __init__(self, cache_file: str = "cv_cache.db"):
        if CVCacheManager._initialized:
            print(f"⚠️ CVCacheManager already initialized, skipping init")
            return
            
        print(f"🔄 Initializing CVCacheManager (ID: {id(self)})")
        self.cache_file = cache_file
        self.memory_cache: Dict[int, CVCacheEntry] = {}
        self.keyword_index: Dict[str, Set[int]] = defaultdict(set)
        self.extraction_queue: List[int] = []
        self.extraction_lock = threading.Lock()
        self.is_extracting = False
        
        # Initialize cache database
        self._init_cache_db()
        
        # Load existing cache with cleanup
        self.initialize_cache_with_cleanup()
        
        # IMPORTANT: Load all CVs from database and extract missing ones
        print(f"🔄 Processing all CVs from database...")
        self.bulk_extract_all_cvs()
        
        CVCacheManager._initialized = True
        print(f"✅ CVCacheManager initialization complete with {len(self.memory_cache)} CVs")

    def _init_cache_db(self):
        """Initialize SQLite cache database"""
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cv_cache (
                detail_id INTEGER PRIMARY KEY,
                cv_path TEXT,
                applicant_name TEXT,
                application_role TEXT,
                raw_text TEXT,
                summary TEXT,
                skills TEXT,
                experience TEXT,
                education TEXT,
                accomplishments TEXT,
                file_hash TEXT,
                last_modified REAL,
                extraction_time TEXT,
                keywords_index TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_keywords ON cv_cache(keywords_index)
        ''')
        
        conn.commit()
        conn.close()
        
    def _load_cache_from_db(self):
        """Load cache dari database ke memory with error handling"""
        print(f"🔄 Loading cache from database...")
        
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM cv_cache')
            rows = cursor.fetchall()
            
            loaded_count = 0
            error_count = 0
            
            for row in rows:
                try:
                    detail_id = row[0]
                    
                    # Safely parse keywords_index JSON
                    keywords_index = {}
                    if row[12]:  # If keywords_index is not None/empty
                        try:
                            keywords_index = json.loads(row[12])
                        except json.JSONDecodeError as e:
                            print(f"⚠️ JSON decode error for detail_id {detail_id}: {e}")
                            print(f"   Problematic data: {repr(row[12][:100])}")
                            keywords_index = {}  # Use empty dict as fallback
                            error_count += 1
                    
                    # Safely parse extraction_time
                    try:
                        extraction_time = datetime.fromisoformat(row[12]) if row[12] else datetime.now()
                    except (ValueError, TypeError):
                        extraction_time = datetime.now()
                    
                    entry = CVCacheEntry(
                        detail_id=detail_id,
                        cv_path=row[1],
                        applicant_name=row[2],
                        application_role=row[3],
                        raw_text=row[4] or "",
                        summary=row[5] or "",
                        skills=row[6] or "",
                        experience=row[7] or "",
                        education=row[8] or "",
                        accomplishments=row[9] or "",
                        file_hash=row[10] or "",
                        last_modified=row[11] or 0.0,
                        extraction_time=extraction_time,
                        keywords_index=keywords_index
                    )
                    
                    self.memory_cache[detail_id] = entry
                    
                    # Build keyword index
                    for keyword, positions in keywords_index.items():
                        if positions:  # Only if keyword found
                            self.keyword_index[keyword.lower()].add(detail_id)
                    
                    loaded_count += 1
                    
                except Exception as e:
                    print(f"⚠️ Error loading cache entry {row[0] if row else 'unknown'}: {e}")
                    error_count += 1
                    continue
            
            print(f"✅ Loaded {loaded_count} CV entries from cache")
            if error_count > 0:
                print(f"⚠️ Skipped {error_count} corrupted cache entries")
                
        except Exception as e:
            print(f"❌ Error loading cache from database: {e}")
            print("🔄 Starting with empty cache...")
            self.memory_cache = {}
            self.keyword_index = defaultdict(set)
        
        finally:
            conn.close()
    def clear_corrupted_cache(self):
        """Clear corrupted cache entries from database"""
        print("🧹 Clearing corrupted cache entries...")
        
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        
        try:
            # Delete entries with malformed JSON
            cursor.execute('SELECT detail_id, keywords_index FROM cv_cache')
            rows = cursor.fetchall()
            
            corrupted_ids = []
            for detail_id, keywords_index in rows:
                if keywords_index:
                    try:
                        json.loads(keywords_index)
                    except json.JSONDecodeError:
                        corrupted_ids.append(detail_id)
            
            if corrupted_ids:
                placeholders = ','.join('?' * len(corrupted_ids))
                cursor.execute(f'DELETE FROM cv_cache WHERE detail_id IN ({placeholders})', corrupted_ids)
                conn.commit()
                print(f"🗑️ Deleted {len(corrupted_ids)} corrupted cache entries")
            else:
                print("✅ No corrupted entries found")
                
        except Exception as e:
            print(f"❌ Error clearing corrupted cache: {e}")
        finally:
            conn.close()

    # Add this method to handle cache initialization with cleanup
    def initialize_cache_with_cleanup(self):
        """Initialize cache with automatic cleanup of corrupted data"""
        try:
            # Try to load cache normally
            self._load_cache_from_db()
            print(f"✅ Loaded {len(self.memory_cache)} entries from SQLite cache")
            
        except Exception as e:
            print(f"❌ Cache loading failed: {e}")
            print("🧹 Attempting to clean corrupted cache...")
            
            # Clear corrupted entries and try again
            self.clear_corrupted_cache()
            
            # Reset cache and try loading again
            self.memory_cache = {}
            self.keyword_index = defaultdict(set)
            
            try:
                self._load_cache_from_db()
                print(f"✅ Loaded {len(self.memory_cache)} entries after cleanup")
            except Exception as e2:
                print(f"❌ Cache loading still failed after cleanup: {e2}")
                print("🔄 Starting with completely fresh cache...")
                
                # If all else fails, clear the entire cache file
                try:
                    conn = sqlite3.connect(self.cache_file)
                    cursor = conn.cursor()
                    cursor.execute('DROP TABLE IF EXISTS cv_cache')
                    conn.commit()
                    conn.close()
                    
                    # Reinitialize the database
                    self._init_cache_db()
                    print("✅ Created fresh cache database")
                    
                except Exception as e3:
                    print(f"❌ Could not create fresh cache: {e3}")

    def _save_cache_entry(self, entry: CVCacheEntry):
        """Save single cache entry to database"""
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO cv_cache 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.detail_id,
            entry.cv_path,
            entry.applicant_name,
            entry.application_role,
            entry.raw_text,
            entry.summary,
            entry.skills,
            entry.experience,
            entry.education,
            entry.accomplishments,
            entry.file_hash,
            entry.last_modified,
            entry.extraction_time.isoformat(),
            json.dumps(entry.keywords_index)
        ))
        
        conn.commit()
        conn.close()
    
    def _get_file_hash(self, filepath: str) -> str:
        """Get file hash untuk detect perubahan"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def _needs_extraction(self, detail_id: int, cv_path: str) -> bool:
        """Check if CV needs extraction or re-extraction"""
        if detail_id not in self.memory_cache:
            return True
        
        if not os.path.exists(cv_path):
            return False
        
        entry = self.memory_cache[detail_id]
        current_hash = self._get_file_hash(cv_path)
        
        return entry.file_hash != current_hash
    
    def load_cv_data_from_database(self) -> List[Dict]:
        """Load CV data dari database dan return list untuk processing"""
        db_manager = database.get_database_connection()
        
        if not db_manager.connect():
            return []
        
        try:
            cursor = db_manager.connection.cursor()
            
            # Get all CV data dengan join
            query = """
                SELECT 
                    ad.detail_id,
                    ad.cv_path,
                    CONCAT(ap.first_name, ' ', ap.last_name) as applicant_name,
                    ad.application_role,
                    ad.cv_raw_text,
                    ad.summary_section,
                    ad.skills_section,
                    ad.experience_section,
                    ad.education_section,
                    ad.accomplishments_section
                FROM ApplicationDetail ad
                JOIN ApplicantProfile ap ON ad.applicant_id = ap.applicant_id
                WHERE ad.cv_path IS NOT NULL
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            cv_data = []
            for row in results:
                cv_data.append({
                    'detail_id': row[0],
                    'cv_path': row[1],
                    'applicant_name': row[2],
                    'application_role': row[3] or 'Not specified',
                    'existing_raw_text': row[4],
                    'existing_summary': row[5],
                    'existing_skills': row[6],
                    'existing_experience': row[7],
                    'existing_education': row[8],
                    'existing_accomplishments': row[9]
                })
            
            return cv_data
            
        except Exception as e:
            print(f"Error loading CV data: {e}")
            return []
        finally:
            db_manager.disconnect()
        
        
    def _resolve_cv_path(self, cv_path: str) -> str:
        """Correct path resolution for CV files"""
        if not cv_path:
            return ""
        
        # If already absolute and exists, return it
        if os.path.isabs(cv_path) and os.path.exists(cv_path):
            return os.path.abspath(cv_path)
        
        # Get current working directory (where the script is running from)
        current_dir = os.getcwd()
        
        # Database format: "data/FOLDER/file.pdf"
        # We need to find where this maps to in the filesystem
        
        # Try different relative path combinations
        path_candidates = []
        
        if cv_path.startswith('data/'):
            # Remove 'data/' prefix and try different bases
            relative_path = cv_path[5:]  # Remove 'data/'
            
            # Try these combinations:
            path_candidates = [
                # From current directory
                os.path.join(current_dir, cv_path),                    # ./data/FOLDER/file.pdf
                os.path.join(current_dir, '..', cv_path),              # ../data/FOLDER/file.pdf
                os.path.join(current_dir, '..', '..', cv_path),        # ../../data/FOLDER/file.pdf
                
                # Direct relative paths
                cv_path,                                               # data/FOLDER/file.pdf
                os.path.join('..', cv_path),                          # ../data/FOLDER/file.pdf
                os.path.join('..', '..', cv_path),                    # ../../data/FOLDER/file.pdf
                
                # With data folder
                os.path.join(current_dir, 'data', relative_path),      # ./data/FOLDER/file.pdf
                os.path.join(current_dir, '..', 'data', relative_path), # ../data/FOLDER/file.pdf
                os.path.join(current_dir, '..', '..', 'data', relative_path), # ../../data/FOLDER/file.pdf
            ]
        else:
            # If path doesn't start with 'data/', try some generic approaches
            path_candidates = [
                os.path.join(current_dir, cv_path),
                os.path.join(current_dir, '..', cv_path),
                os.path.join(current_dir, '..', '..', cv_path),
                os.path.join(current_dir, 'data', cv_path),
                os.path.join(current_dir, '..', 'data', cv_path),
            ]
        
        # Test each candidate
        for candidate in path_candidates:
            if os.path.exists(candidate):
                resolved = os.path.abspath(candidate)
                print(f"✅ Resolved: {cv_path} -> {resolved}")
                return resolved
        
        # If no candidates work, try searching by filename
        if '/' in cv_path or '\\' in cv_path:
            filename = os.path.basename(cv_path)
            found_path = self._find_cv_by_filename(filename)
            if found_path:
                print(f"✅ Found by filename: {cv_path} -> {found_path}")
                return found_path
        
        print(f"❌ Could not resolve path: {cv_path}")
        print(f"   Tried these candidates:")
        for candidate in path_candidates:
            print(f"     - {candidate} ({'exists' if os.path.exists(candidate) else 'not found'})")
        
        return ""

    def _find_cv_by_filename(self, filename: str) -> str:
        """Search for CV file by filename in data directories"""
        if not filename:
            return ""
        
        current_dir = os.getcwd()
        
        # Search in multiple possible data directory locations
        search_roots = [
            os.path.join(current_dir, 'data'),              # ./data
            os.path.join(current_dir, '..', 'data'),        # ../data
            os.path.join(current_dir, '..', '..', 'data'),  # ../../data
            'data',                                         # Relative data
            '../data',                                      # Relative ../data
            '../../data',                                   # Relative ../../data
        ]
        
        for root in search_roots:
            if os.path.exists(root):
                print(f"   🔍 Searching in: {root}")
                for dirpath, dirnames, filenames in os.walk(root):
                    if filename in filenames:
                        found = os.path.abspath(os.path.join(dirpath, filename))
                        print(f"   ✅ Found: {found}")
                        return found
        
        return ""

    def extract_cv_if_needed(self, cv_data: Dict) -> Optional[CVCacheEntry]:
        """Extract CV jika diperlukan dan return cache entry"""
        detail_id = cv_data['detail_id']
        cv_path = cv_data['cv_path']
        
        # RESOLVE PATH
        resolved_path = self._resolve_cv_path(cv_path)
        
        if not resolved_path:
            print(f"❌ CV file not found: {cv_path}")
            return None
        
        print(f"✅ Found CV: {os.path.basename(resolved_path)}")
        
        # Check if extraction needed
        if not self._needs_extraction(detail_id, resolved_path):
            return self.memory_cache[detail_id]
        
        print(f"🔄 Extracting: {cv_data['applicant_name']}")
        
        # Extract CV
        try:
            extraction_result = extract_realtime(resolved_path)
            
            if not extraction_result.success:
                print(f"❌ Extraction failed: {extraction_result.error_message}")
                return None
            
            # Create cache entry
            entry = CVCacheEntry(
                detail_id=detail_id,
                cv_path=cv_path,  # Keep original database path
                applicant_name=cv_data['applicant_name'],
                application_role=cv_data['application_role'],
                raw_text=extraction_result.cv_raw_text,
                summary=extraction_result.summary_section,
                skills=extraction_result.skills_section,
                experience=extraction_result.experience_section,
                education=extraction_result.education_section,
                accomplishments=extraction_result.accomplishments_section,
                file_hash=self._get_file_hash(resolved_path),
                last_modified=os.path.getmtime(resolved_path),
                extraction_time=datetime.now(),
                keywords_index={}
            )
            
            # Save to cache
            self.memory_cache[detail_id] = entry
            self._save_cache_entry(entry)
            
            print(f"✅ Successfully cached: {cv_data['applicant_name']}")
            return entry
            
        except Exception as e:
            print(f"❌ Error extracting CV: {e}")
            return None
    def _get_file_hash(self, filepath: str) -> str:
        """Get file hash untuk detect perubahan - with path resolution"""
        try:
            # Resolve path first if needed
            if not os.path.exists(filepath):
                filepath = self._resolve_cv_path(filepath)
            
            if not filepath or not os.path.exists(filepath):
                return ""
            
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            print(f"⚠️ Error getting file hash: {e}")
            return ""

    def _needs_extraction(self, detail_id: int, cv_path: str) -> bool:
        """Check if CV needs extraction or re-extraction - with path resolution"""
        if detail_id not in self.memory_cache:
            return True
        
        # Resolve path for checking
        resolved_path = self._resolve_cv_path(cv_path)
        if not resolved_path or not os.path.exists(resolved_path):
            return False
        
        entry = self.memory_cache[detail_id]
        current_hash = self._get_file_hash(resolved_path)
        
        return entry.file_hash != current_hash

    # Add this debug code to your cv_cache_manager.py to see what's happening

    def bulk_extract_all_cvs(self):
        """Extract semua CV dari database secara bulk"""
        print("🔄 Starting bulk CV extraction...")
        start_time = time.time()
        
        cv_data_list = self.load_cv_data_from_database()
        total_cvs = len(cv_data_list)
        
        print(f"📊 Found {total_cvs} CVs in database to process")
        print(f"📊 Current cache size: {len(self.memory_cache)} entries")
        
        extracted_count = 0
        skipped_count = 0
        failed_count = 0
        
        for i, cv_data in enumerate(cv_data_list, 1):
            detail_id = cv_data['detail_id']
            
            # Show progress every 50 CVs
            if i % 50 == 0 or i <= 10:
                print(f"🔄 Processing {i}/{total_cvs}: {cv_data['applicant_name']}")
            
            try:
                # Check if already in cache
                if detail_id in self.memory_cache:
                    skipped_count += 1
                    if i <= 5:
                        print(f"   ⏭️ Already cached (ID: {detail_id})")
                    continue
                
                # Extract CV if needed
                entry = self.extract_cv_if_needed(cv_data)
                if entry:
                    extracted_count += 1
                    if i <= 5:
                        print(f"   ✅ Newly extracted and cached (ID: {entry.detail_id})")
                else:
                    failed_count += 1
                    if i <= 5:
                        print(f"   ❌ Extraction failed for {cv_data['applicant_name']}")
                        
            except Exception as e:
                print(f"❌ Error processing CV {cv_data['detail_id']}: {e}")
                failed_count += 1
        
        elapsed_time = time.time() - start_time
        
        print(f"\n📈 Bulk extraction completed in {elapsed_time:.2f} seconds:")
        print(f"   - Newly extracted: {extracted_count}")
        print(f"   - Already cached (skipped): {skipped_count}")
        print(f"   - Failed: {failed_count}")
        print(f"   - Total in memory cache: {len(self.memory_cache)}")
        print(f"   - Cache manager ID: {id(self)}")

    def force_refresh_all_cvs(self):
        """Force refresh all CVs by clearing cache and re-extracting everything"""
        print("🔄 Force refreshing all CVs...")
        
        # Clear memory cache
        self.memory_cache.clear()
        self.keyword_index.clear()
        
        # Clear database cache
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cv_cache')
        conn.commit()
        conn.close()
        
        print("🗑️ Cleared all existing cache")
        
        # Re-extract everything
        self.bulk_extract_all_cvs()
            
    def load_cv_cache(self):
        """Load CV cache - with debugging"""
        print(f"🔄 Loading CV cache... (Manager ID: {id(self)})")
        print(f"📊 Current cache size before loading: {len(self.memory_cache)}")
        
        # If cache is empty or very small, do full extraction
        if len(self.memory_cache) < 50:  # Assuming you should have way more than 50 CVs
            print(f"⚠️ Cache seems incomplete ({len(self.memory_cache)} entries), doing full extraction...")
            self.bulk_extract_all_cvs()
        else:
            print(f"✅ Cache seems complete with {len(self.memory_cache)} entries")
        
        print(f"📊 Cache size after loading: {len(self.memory_cache)}")
        return len(self.memory_cache)
    
    def debug_database_contents(self):
        """Debug method to check what's in the database"""
        print("🔍 DEBUGGING DATABASE CONTENTS:")
        
        cv_data_list = self.load_cv_data_from_database()
        print(f"📊 Total CVs in database: {len(cv_data_list)}")
        
        # Show first 5 entries
        for i, cv_data in enumerate(cv_data_list[:5], 1):
            print(f"   {i}. ID {cv_data['detail_id']}: {cv_data['applicant_name']}")
            print(f"      Path: {cv_data['cv_path']}")
            
            # Test path resolution
            resolved_path = self._resolve_cv_path(cv_data['cv_path'])
            print(f"      Resolved: {resolved_path}")
            print(f"      Exists: {bool(resolved_path and os.path.exists(resolved_path))}")
            print()
        
        print(f"📊 Cache status:")
        print(f"   - Memory cache: {len(self.memory_cache)} entries")
        print(f"   - Should have: {len(cv_data_list)} entries")
        print(f"   - Missing: {len(cv_data_list) - len(self.memory_cache)} entries")

    def search_keywords(self, keywords: List[str], algorithm: str = "kmp") -> List[Dict]:
        """Search keywords dalam cached CV data"""
        from backend import search_engine
        
        results = []
        
        for detail_id, entry in self.memory_cache.items():
            # Use search algorithms untuk exact matching
            keyword_matches = {}
            total_matches = 0
            
            for keyword in keywords:
                if algorithm == "kmp":
                    from kmp import kmp_search
                    matches = kmp_search(entry.raw_text.lower(), keyword.lower())
                elif algorithm == "boyer_moore":
                    from boyer_moore import boyer_moore_search
                    matches = boyer_moore_search(entry.raw_text.lower(), keyword.lower())
                elif algorithm == "aho_corasick":
                    from aho_corasick import aho_corasick_search
                    matches = aho_corasick_search(entry.raw_text.lower(), [keyword.lower()])
                    matches = matches.get(keyword.lower(), [])
                else:
                    matches = []
                
                if matches:
                    keyword_matches[keyword] = len(matches)
                    total_matches += len(matches)
            
            if total_matches > 0:
                results.append({
                    'detail_id': detail_id,
                    'applicant_name': entry.applicant_name,
                    'application_role': entry.application_role,
                    'total_matches': total_matches,
                    'keyword_matches': keyword_matches,
                    'cv_path': entry.cv_path
                })
        
        # Sort by total matches (descending)
        results.sort(key=lambda x: x['total_matches'], reverse=True)
        
        return results
    
    def get_cv_summary(self, detail_id: int) -> Optional[Dict]:
        """Get CV summary dari cache"""
        if detail_id not in self.memory_cache:
            return None
        
        entry = self.memory_cache[detail_id]
        
        return {
            'detail_id': detail_id,
            'name': entry.applicant_name,
            'role': entry.application_role,
            'summary': entry.summary,
            'skills': entry.skills,
            'experience': entry.experience,
            'education': entry.education,
            'accomplishments': entry.accomplishments,
            'cv_path': entry.cv_path
        }
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'total_cvs': len(self.memory_cache),
            'last_update': max([entry.extraction_time for entry in self.memory_cache.values()]) if self.memory_cache else None,
            'cache_size_mb': os.path.getsize(self.cache_file) / (1024*1024) if os.path.exists(self.cache_file) else 0
        }
    
    def test_path_resolution(self):
        """Test path resolution for first few CVs"""
        print("🧪 TESTING PATH RESOLUTION:")
        
        cv_data_list = self.load_cv_data_from_database()
        
        for i, cv_data in enumerate(cv_data_list[:3], 1):
            cv_path = cv_data['cv_path']
            print(f"\n{i}. Testing: {cv_path}")
            
            resolved_path = self._resolve_cv_path(cv_path)
            
            if resolved_path:
                print(f"   ✅ Resolved to: {resolved_path}")
                print(f"   📁 File exists: {os.path.exists(resolved_path)}")
                
                if os.path.exists(resolved_path):
                    file_size = os.path.getsize(resolved_path)
                    print(f"   📊 File size: {file_size} bytes")
                else:
                    print(f"   ❌ File not found at resolved path")
            else:
                print(f"   ❌ Could not resolve path")
                
                # Try to find by filename
                filename = os.path.basename(cv_path)
                found_path = self._find_cv_by_filename(filename)
                if found_path:
                    print(f"   🔍 Found by filename: {found_path}")
                else:
                    print(f"   ❌ Could not find file anywhere")

# Global instance
print("🔄 Creating global cv_cache_manager instance...")
cv_cache_manager = CVCacheManager()
print(f"✅ Global cv_cache_manager created (ID: {id(cv_cache_manager)})")

def initialize_cv_cache():
    """Initialize dan load semua CV data"""
    cv_cache_manager.bulk_extract_all_cvs()
    return cv_cache_manager

def search_cvs_cached(keywords: str, algorithm: str = "kmp", top_n: int = 10) -> List[Dict]:
    """Search function yang menggunakan cache"""
    keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
    results = cv_cache_manager.search_keywords(keyword_list, algorithm)
    return results[:top_n]

def get_cv_summary_cached(detail_id: int) -> Optional[Dict]:
    """Get CV summary dari cache"""
    return cv_cache_manager.get_cv_summary(detail_id)

if __name__ == "__main__":
    # Test the cache manager
    print("Testing CV Cache Manager...")
    
    # Initialize cache
    cache_manager = initialize_cv_cache()
    
    # Test search
    results = search_cvs_cached("Python, engineer", "kmp", 5)
    print(f"\nSearch results: {len(results)}")
    
    for result in results:
        print(f"  - {result['applicant_name']}: {result['total_matches']} matches")
    
    # Cache stats
    stats = cache_manager.get_cache_stats()
    print(f"\nCache stats: {stats}")