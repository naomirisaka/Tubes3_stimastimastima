# cv_cache_manager.py - Fixed version

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
from backend import database  # Fixed import path

@dataclass
class CVCacheEntry:
    """Cache entry untuk setiap CV dengan real-time extraction support"""
    detail_id: int
    cv_path: str
    applicant_name: str
    application_role: str
    file_hash: str
    last_modified: float
    cache_time: datetime
    raw_text: str = ""  # Added raw_text field
    summary_section: str = ""
    skills_section: str = ""
    experience_section: str = ""
    education_section: str = ""
    accomplishments_section: str = ""

class RealTimeCVCacheManager:
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            print(f"🔄 Creating NEW RealTimeCVCacheManager instance")
            cls._instance = super(RealTimeCVCacheManager, cls).__new__(cls)
        else:
            print(f"♻️ Returning EXISTING RealTimeCVCacheManager instance (ID: {id(cls._instance)})")
        return cls._instance
        
    def __init__(self, cache_file: str = "cv_realtime_cache.db"):
        if RealTimeCVCacheManager._initialized:
            print(f"⚠️ RealTimeCVCacheManager already initialized, skipping init")
            return
            
        print(f"🔄 Initializing RealTimeCVCacheManager (ID: {id(self)})")
        self.cache_file = cache_file
        self.memory_cache: Dict[int, CVCacheEntry] = {}
        self.extraction_lock = threading.Lock()
        
        # Initialize cache database
        self._init_cache_db()
        
        # Load existing cache
        self.initialize_cache()
        
        # Load all CVs from database
        print(f"🔄 Loading CVs from database...")
        self.load_cv_metadata_from_database()
        
        RealTimeCVCacheManager._initialized = True
        print(f"✅ RealTimeCVCacheManager initialization complete with {len(self.memory_cache)} CVs")

    def _init_cache_db(self):
        """Initialize SQLite cache database"""
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        
        # Fixed SQL syntax - removed missing comma
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cv_realtime_cache (
                detail_id INTEGER PRIMARY KEY,
                cv_path TEXT,
                applicant_name TEXT,
                application_role TEXT,
                file_hash TEXT,
                last_modified REAL,
                cache_time TEXT,
                raw_text TEXT,
                summary_section TEXT,
                skills_section TEXT,
                experience_section TEXT,
                education_section TEXT,
                accomplishments_section TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_detail_id ON cv_realtime_cache(detail_id)
        ''')
        
        conn.commit()
        conn.close()
        
    def initialize_cache(self):
        """Initialize cache dengan loading dari database"""
        try:
            self._load_cache_from_db()
            print(f"✅ Loaded {len(self.memory_cache)} entries from cache database")
            
        except Exception as e:
            print(f"❌ Cache loading failed: {e}")
            print("🔄 Starting with fresh cache...")
            
            # Clear cache and start fresh
            self.memory_cache = {}
            
            try:
                conn = sqlite3.connect(self.cache_file)
                cursor = conn.cursor()
                cursor.execute('DROP TABLE IF EXISTS cv_realtime_cache')
                conn.commit()
                conn.close()
                
                # Reinitialize the database
                self._init_cache_db()
                print("✅ Created fresh cache database")
                
            except Exception as e2:
                print(f"❌ Could not create fresh cache: {e2}")

    def _load_cache_from_db(self):
        """Load cache dari database ke memory"""
        print(f"🔄 Loading cache from database...")
        
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM cv_realtime_cache')
            rows = cursor.fetchall()
            
            loaded_count = 0
            error_count = 0
            
            for row in rows:
                try:
                    detail_id = row[0]
                    
                    # Safely parse cache_time
                    try:
                        cache_time = datetime.fromisoformat(row[6]) if row[6] else datetime.now()
                    except (ValueError, TypeError):
                        cache_time = datetime.now()
                    
                    entry = CVCacheEntry(
                        detail_id=detail_id,
                        cv_path=row[1] or "",
                        applicant_name=row[2] or "",
                        application_role=row[3] or "",
                        file_hash=row[4] or "",
                        last_modified=row[5] or 0.0,
                        cache_time=cache_time,
                        raw_text=row[7] or "",
                        summary_section=row[8] or "",
                        skills_section=row[9] or "",
                        experience_section=row[10] or "",
                        education_section=row[11] or "",
                        accomplishments_section=row[12] or ""
                    )
                    
                    self.memory_cache[detail_id] = entry
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
            self.memory_cache = {}
        
        finally:
            conn.close()

    def _save_cache_entry(self, entry: CVCacheEntry):
        """Save single cache entry to database"""
        conn = sqlite3.connect(self.cache_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO cv_realtime_cache 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.detail_id,
            entry.cv_path,
            entry.applicant_name,
            entry.application_role,
            entry.file_hash,
            entry.last_modified,
            entry.cache_time.isoformat(),
            entry.raw_text,
            entry.summary_section,
            entry.skills_section,
            entry.experience_section,
            entry.education_section,
            entry.accomplishments_section
        ))
        
        conn.commit()
        conn.close()
    
    def _get_file_hash(self, filepath: str) -> str:
        """Get file hash untuk detect perubahan"""
        try:
            # Resolve path first if needed
            resolved_path = self._resolve_cv_path(filepath)
            
            if not resolved_path or not os.path.exists(resolved_path):
                return ""
            
            with open(resolved_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            print(f"⚠️ Error getting file hash: {e}")
            return ""

    def _resolve_cv_path(self, cv_path: str) -> str:
        """Resolve CV path to absolute path"""
        if not cv_path:
            return ""
        
        # If already absolute and exists, return it
        if os.path.isabs(cv_path) and os.path.exists(cv_path):
            return os.path.abspath(cv_path)
        
        # Get current working directory
        current_dir = os.getcwd()
        
        # Try different relative path combinations
        path_candidates = []
        
        if cv_path.startswith('data/'):
            # Remove 'data/' prefix and try different bases
            relative_path = cv_path[5:]  # Remove 'data/'
            
            path_candidates = [
                # From current directory
                os.path.join(current_dir, cv_path),                    
                os.path.join(current_dir, '..', cv_path),              
                os.path.join(current_dir, '..', '..', cv_path),        
                
                # Direct relative paths
                cv_path,                                               
                os.path.join('..', cv_path),                          
                os.path.join('..', '..', cv_path),                    
                
                # With data folder
                os.path.join(current_dir, 'data', relative_path),      
                os.path.join(current_dir, '..', 'data', relative_path), 
                os.path.join(current_dir, '..', '..', 'data', relative_path), 
            ]
        else:
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
                return resolved
        
        # If no candidates work, try searching by filename
        if '/' in cv_path or '\\' in cv_path:
            filename = os.path.basename(cv_path)
            found_path = self._find_cv_by_filename(filename)
            if found_path:
                return found_path
        
        return ""

    def _find_cv_by_filename(self, filename: str) -> str:
        """Search for CV file by filename in data directories"""
        if not filename:
            return ""
        
        current_dir = os.getcwd()
        
        search_roots = [
            os.path.join(current_dir, 'data'),              
            os.path.join(current_dir, '..', 'data'),        
            os.path.join(current_dir, '..', '..', 'data'),  
            'data',                                         
            '../data',                                      
            '../../data',                                   
        ]
        
        for root in search_roots:
            if os.path.exists(root):
                for dirpath, dirnames, filenames in os.walk(root):
                    if filename in filenames:
                        found = os.path.abspath(os.path.join(dirpath, filename))
                        return found
        
        return ""

    def load_cv_metadata_from_database(self):
        """Load CV metadata dari database tanpa extract content"""
        db_manager = database.get_database_connection()
        
        if not db_manager.connect():
            print("❌ Could not connect to database")
            return
        
        try:
            cv_data = db_manager.get_cv_data_for_search()
            
            updated_count = 0
            new_count = 0
            
            for detail_id, cv_path, applicant_name, application_role in cv_data:
                # Resolve path untuk check file
                resolved_path = self._resolve_cv_path(cv_path)
                
                if not resolved_path:
                    print(f"⚠️ CV file not found: {cv_path}")
                    continue
                
                # Get file info
                file_hash = self._get_file_hash(resolved_path)
                last_modified = os.path.getmtime(resolved_path) if os.path.exists(resolved_path) else 0
                
                # Check if we need to update cache
                if detail_id in self.memory_cache:
                    existing = self.memory_cache[detail_id]
                    if existing.file_hash != file_hash:
                        # File changed, need re-extraction
                        self._extract_and_cache_cv(detail_id, cv_path, applicant_name, application_role)
                        updated_count += 1
                else:
                    # New entry - extract immediately
                    self._extract_and_cache_cv(detail_id, cv_path, applicant_name, application_role)
                    new_count += 1
            
            print(f"📊 CV Metadata loaded: {new_count} new, {updated_count} updated")
            print(f"📄 Total CVs in cache: {len(self.memory_cache)}")
            
        except Exception as e:
            print(f"❌ Error loading CV metadata: {e}")
        finally:
            db_manager.disconnect()

    def _extract_and_cache_cv(self, detail_id: int, cv_path: str, applicant_name: str, application_role: str):
        """Extract CV and cache the results"""
        resolved_path = self._resolve_cv_path(cv_path)
        
        if not resolved_path:
            print(f"❌ CV file not found: {cv_path}")
            return
        
        try:
            print(f"🔄 Extracting: {applicant_name}")
            extraction_result = extract_realtime(resolved_path)
            
            if not extraction_result or not extraction_result.success:
                print(f"❌ Extraction failed: {extraction_result.error_message if extraction_result else 'Unknown error'}")
                return
            
            # Create cache entry with extracted content
            entry = CVCacheEntry(
                detail_id=detail_id,
                cv_path=cv_path,
                applicant_name=applicant_name,
                application_role=application_role,
                file_hash=self._get_file_hash(resolved_path),
                last_modified=os.path.getmtime(resolved_path),
                cache_time=datetime.now(),
                raw_text=extraction_result.cv_raw_text or "",
                summary_section=extraction_result.summary_section or "",
                skills_section=extraction_result.skills_section or "",
                experience_section=extraction_result.experience_section or "",
                education_section=extraction_result.education_section or "",
                accomplishments_section=extraction_result.accomplishments_section or ""
            )
            
            self.memory_cache[detail_id] = entry
            self._save_cache_entry(entry)
            
            print(f"✅ Successfully cached: {applicant_name}")
            
        except Exception as e:
            print(f"❌ Error extracting CV {applicant_name}: {e}")

    def search_keywords_realtime(self, keywords: List[str], algorithm: str = "kmp") -> List[Dict]:
        """Search keywords dalam cached content"""
        if not keywords:
            return []
        
        results = []
        
        for detail_id, entry in self.memory_cache.items():
            # Use cached raw text
            cv_text = entry.raw_text.lower()
            
            if not cv_text:
                # If no cached text, skip this CV
                continue
            
            # Search for keywords using specified algorithm
            keyword_matches = {}
            total_matches = 0
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                
                if algorithm == "kmp":
                    from kmp import kmp_search
                    matches = kmp_search(cv_text, keyword_lower)
                elif algorithm == "boyer_moore":
                    from boyer_moore import boyer_moore_search
                    matches = boyer_moore_search(cv_text, keyword_lower)
                elif algorithm == "aho_corasick":
                    from aho_corasick import aho_corasick_search
                    matches = aho_corasick_search(cv_text, [keyword_lower])
                    matches = matches.get(keyword_lower, [])
                else:
                    # Simple search fallback
                    matches = []
                    start = 0
                    while True:
                        pos = cv_text.find(keyword_lower, start)
                        if pos == -1:
                            break
                        matches.append(pos)
                        start = pos + 1
                
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

    def get_cv_summary_realtime(self, detail_id: int) -> Optional[Dict]:
        """Get CV summary dari cached content"""
        if detail_id not in self.memory_cache:
            return None
        
        entry = self.memory_cache[detail_id]
        
        # Get additional profile data from database
        db_manager = database.get_database_connection()
        phone = 'Not available'
        address = 'Not available'
        
        if db_manager.connect():
            try:
                basic_data = db_manager.get_application_basic_data(detail_id)
                phone = basic_data.get('phone', 'Not available')
                address = basic_data.get('address', 'Not available')
            except:
                pass
            finally:
                db_manager.disconnect()
        
        return {
            'detail_id': detail_id,
            'name': entry.applicant_name,
            'phone': phone,
            'address': address,
            'role': entry.application_role,
            'cv_path': entry.cv_path,
            'summary': entry.summary_section or 'No summary available',
            'skills': entry.skills_section or 'No skills listed',
            'experience': entry.experience_section or 'No experience listed',
            'education': entry.education_section or 'No education listed',
            'accomplishments': entry.accomplishments_section or 'No accomplishments listed'
        }
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        file_exists_count = 0
        total_size = 0
        
        for entry in self.memory_cache.values():
            resolved_path = self._resolve_cv_path(entry.cv_path)
            if resolved_path and os.path.exists(resolved_path):
                file_exists_count += 1
                try:
                    total_size += os.path.getsize(resolved_path)
                except:
                    pass
        
        return {
            'total_cvs': len(self.memory_cache),
            'files_found': file_exists_count,
            'files_missing': len(self.memory_cache) - file_exists_count,
            'total_file_size_mb': total_size / (1024*1024),
            'cache_size_mb': os.path.getsize(self.cache_file) / (1024*1024) if os.path.exists(self.cache_file) else 0,
            'last_update': max([entry.cache_time for entry in self.memory_cache.values()]) if self.memory_cache else None
        }

# Global instance
print("🔄 Creating global realtime_cv_cache_manager instance...")
realtime_cv_cache_manager = RealTimeCVCacheManager()
print(f"✅ Global realtime_cv_cache_manager created (ID: {id(realtime_cv_cache_manager)})")

def initialize_realtime_cv_cache():
    """Initialize dan load semua CV metadata"""
    realtime_cv_cache_manager.load_cv_metadata_from_database()
    return realtime_cv_cache_manager

def search_cvs_realtime(keywords: str, algorithm: str = "kmp", top_n: int = 10) -> List[Dict]:
    """Search function yang menggunakan cached content"""
    keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
    results = realtime_cv_cache_manager.search_keywords_realtime(keyword_list, algorithm)
    return results[:top_n]

def get_cv_summary_realtime_cached(detail_id: int) -> Optional[Dict]:
    """Get CV summary dari cached content"""
    return realtime_cv_cache_manager.get_cv_summary_realtime(detail_id)