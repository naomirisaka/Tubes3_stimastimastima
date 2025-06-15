# integrated_ats_backend.py - Fixed version

import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import os

# Import algoritma pencarian
from kmp import kmp_search
from boyer_moore import boyer_moore_search  
from aho_corasick import aho_corasick_search
from levenshtein import fuzzy_search_keywords, parse_keywords

# Import cache manager dan database
from backend.cv_cache_manager import ( 
    realtime_cv_cache_manager as cv_cache_manager,
    initialize_realtime_cv_cache, 
    search_cvs_realtime, 
    get_cv_summary_realtime_cached
)
from backend import database
# Import extractor as module untuk avoid circular import
import data_extractor.extractor as extractor_module

@dataclass
class SearchResult:
    """Result dari search operation"""
    keywords_searched: List[str]
    algorithm_used: str
    exact_match_time: float
    fuzzy_match_time: float
    total_cvs_scanned: int
    exact_matches: Dict[str, int]
    fuzzy_matches: Dict[str, List[Tuple[str, float]]]

@dataclass
class CVMatch:
    """CV match result"""
    detail_id: int
    applicant_name: str
    application_role: str
    total_matches: int
    keyword_matches: Dict[str, int]
    similarity_score: float
    match_sources: List[str]

# Wrapper functions untuk memastikan konsistensi output
def standardized_kmp_search(text: str, pattern: str) -> List[int]:
    """Wrapper untuk KMP search yang mengembalikan list posisi"""
    try:
        return kmp_search(text, pattern)
    except:
        return []

def standardized_boyer_moore_search(text: str, pattern: str) -> List[int]:
    """Wrapper untuk Boyer-Moore search yang mengembalikan list posisi"""
    try:
        return boyer_moore_search(text, pattern)
    except:
        return []

def standardized_aho_corasick_search(text: str, patterns: List[str]) -> Dict[str, List[int]]:
    """Wrapper untuk Aho-Corasick search yang mengembalikan dict"""
    try:
        return aho_corasick_search(text, patterns)
    except:
        return {pattern: [] for pattern in patterns}

class IntegratedATSBackend:
    
    def __init__(self):
        self.cache_manager = cv_cache_manager
        self.db_manager = database.get_database_connection()
        self._cache_initialized = False
        self.fuzzy_threshold = 70.0
    
    def initialize(self) -> bool:
        try:
            print("Initializing Integrated ATS Backend...")
            
            # Test database connection
            if not self.db_manager.connect():
                print("Failed to connect to database")
                return False
            
            self.db_manager.disconnect()
            
            # Initialize CV cache jika belum
            if not self._cache_initialized:
                print("Loading CV cache...")
                initialize_realtime_cv_cache()
                self._cache_initialized = True
                print("Cache initialized successfully")
            
            print("Backend initialization completed")
            return True
        
        except Exception as e:
            print(f"Backend initialization failed: {e}")
            return False
    
    def search_cvs_with_cache(
        self, 
        keywords: str, 
        algorithm: str = "kmp", 
        top_n: int = 10,
        fuzzy_threshold: float = 70.0
    ) -> Tuple[SearchResult, List[CVMatch]]:
        """Main search function menggunakan cache"""
        
        # Parse keywords
        keyword_list = parse_keywords(keywords)
        
        # Pastikan cache sudah diinisialisasi
        if not self._cache_initialized:
            self.initialize()
        
        # Exact matching menggunakan algoritma yang dipilih
        start_time = time.time()
        
        # Gunakan algoritma yang sesuai untuk pencarian
        algorithm_map = {
            "kmp": standardized_kmp_search,
            "boyer_moore": standardized_boyer_moore_search, 
            "aho_corasick": standardized_aho_corasick_search
        }
        
        if algorithm not in algorithm_map:
            algorithm = "kmp"  # Default fallback
        
        search_func = algorithm_map[algorithm]
        
        # Lakukan pencarian di cache untuk setiap CV
        cv_results = []
        exact_matches = {keyword: 0 for keyword in keyword_list}
        
        for detail_id, cache_entry in self.cache_manager.memory_cache.items():
            # Ambil raw text dari cache
            cv_text = getattr(cache_entry, 'raw_text', '')
            
            if not cv_text:
                # If no cached text, try to get from cache using real-time extraction
                print(f"No cached text for {cache_entry.applicant_name}, trying real-time extraction...")
                cv_data = {
                    'detail_id': cache_entry.detail_id,
                    'cv_path': cache_entry.cv_path,
                    'applicant_name': cache_entry.applicant_name,
                    'application_role': cache_entry.application_role
                }
                extraction_result = self.cache_manager.extract_cv_realtime(cv_data)
                if extraction_result and extraction_result.success:
                    cv_text = extraction_result.cv_raw_text.lower()
                else:
                    continue  # Skip if extraction fails
            else:
                cv_text = cv_text.lower()
            
            # Hitung matches untuk setiap keyword
            keyword_matches = {}
            total_matches = 0
            
            if algorithm == "aho_corasick":
                # Untuk Aho-Corasick, cari semua keyword sekaligus
                keyword_list_lower = [kw.lower() for kw in keyword_list]
                matches = search_func(cv_text, keyword_list_lower)
                
                for keyword in keyword_list:
                    keyword_lower = keyword.lower()
                    count = len(matches.get(keyword_lower, []))
                    keyword_matches[keyword] = count
                    total_matches += count
                    exact_matches[keyword] += count
            else:
                # Untuk KMP dan Boyer-Moore, cari satu per satu
                for keyword in keyword_list:
                    keyword_lower = keyword.lower()
                    positions = search_func(cv_text, keyword_lower)
                    count = len(positions)
                    keyword_matches[keyword] = count
                    total_matches += count
                    exact_matches[keyword] += count
            
            # Hanya simpan CV yang memiliki matches
            if total_matches > 0:
                cv_results.append({
                    'detail_id': detail_id,
                    'applicant_name': cache_entry.applicant_name,
                    'application_role': cache_entry.application_role,
                    'total_matches': total_matches,
                    'keyword_matches': keyword_matches,
                    'cv_path': cache_entry.cv_path
                })
        
        exact_time = (time.time() - start_time) * 1000
        
        # Sort results by total matches (descending)
        cv_results.sort(key=lambda x: x['total_matches'], reverse=True)
        
        # Fuzzy matching untuk keywords yang tidak ditemukan
        start_fuzzy = time.time()
        fuzzy_matches = {}
        missing_keywords = [kw for kw in keyword_list if exact_matches.get(kw, 0) == 0]
        
        if missing_keywords:
            print(f"Performing fuzzy search for: {missing_keywords}")
            
            # Fuzzy search pada cached text
            for detail_id, cache_entry in self.cache_manager.memory_cache.items():
                if not cache_entry.raw_text:
                    continue
                    
                fuzzy_result = fuzzy_search_keywords(
                    cache_entry.raw_text, 
                    missing_keywords, 
                    fuzzy_threshold
                )
                
                for keyword, similar_words in fuzzy_result.items():
                    if similar_words and keyword not in fuzzy_matches:
                        fuzzy_matches[keyword] = similar_words[:3]  # Top 3 similar words
        
        fuzzy_time = (time.time() - start_fuzzy) * 1000
        
        # Ambil top N results
        top_results = cv_results[:top_n]
        
        # Convert results to CVMatch objects
        cv_matches = []
        for result in top_results:
            # Calculate similarity score
            similarity_score = min(100.0, (result['total_matches'] / len(keyword_list)) * 20)
            
            cv_match = CVMatch(
                detail_id=result['detail_id'],
                applicant_name=result['applicant_name'],
                application_role=result['application_role'],
                total_matches=result['total_matches'],
                keyword_matches=result['keyword_matches'],
                similarity_score=similarity_score,
                match_sources=['CV Cache']
            )
            cv_matches.append(cv_match)
        
        # Create search result
        search_result = SearchResult(
            keywords_searched=keyword_list,
            algorithm_used=algorithm,
            exact_match_time=exact_time,
            fuzzy_match_time=fuzzy_time,
            total_cvs_scanned=len(self.cache_manager.memory_cache),
            exact_matches=exact_matches,
            fuzzy_matches=fuzzy_matches
        )
        
        return search_result, cv_matches
    
    def get_cv_summary_enhanced(self, detail_id: int) -> Optional[Dict]:
        """Get enhanced CV summary dari cache dengan fallback ke database"""
        
        # Try cache first
        if detail_id in self.cache_manager.memory_cache:
            cache_entry = self.cache_manager.memory_cache[detail_id]
            
            # Get additional profile data from database
            phone = 'Not available'
            address = 'Not available'
            
            try:
                if self.db_manager.connect():
                    basic_data = self.db_manager.get_application_basic_data(detail_id)
                    phone = basic_data.get('phone', 'Not available')
                    address = basic_data.get('address', 'Not available')
                    self.db_manager.disconnect()
            except:
                pass
            
            # Return data dalam format yang konsisten
            return {
                'detail_id': detail_id,
                'name': cache_entry.applicant_name,
                'phone': phone,
                'address': address, 
                'role': cache_entry.application_role or 'Not specified',
                'summary': cache_entry.summary_section or 'No summary available',
                'skills': cache_entry.skills_section or 'No skills listed',
                'experience': cache_entry.experience_section or 'No experience listed',
                'education': cache_entry.education_section or 'No education listed',
                'accomplishments': cache_entry.accomplishments_section or 'No accomplishments listed',
                'cv_path': cache_entry.cv_path
            }
        
        # Fallback ke database query
        try:
            if not self.db_manager.connect():
                return None
            
            cursor = self.db_manager.connection.cursor()
            
            query = """
                SELECT 
                    ad.detail_id,
                    CONCAT(ap.first_name, ' ', ap.last_name) as name,
                    ap.phone_number as phone,
                    ap.address as address,
                    ad.application_role as role,
                    ad.summary_section as summary,
                    ad.skills_section as skills,
                    ad.experience_section as experience,
                    ad.education_section as education,
                    ad.accomplishments_section as accomplishments,
                    ad.cv_path
                FROM ApplicationDetail ad
                JOIN ApplicantProfile ap ON ad.applicant_id = ap.applicant_id
                WHERE ad.detail_id = %s
            """
            
            cursor.execute(query, (detail_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'detail_id': result[0],
                    'name': result[1],
                    'phone': result[2] or 'Not available',
                    'address': result[3] or 'Not available',
                    'role': result[4] or 'Not specified',
                    'summary': result[5] or 'No summary available',
                    'skills': result[6] or 'No skills listed',
                    'experience': result[7] or 'No experience listed',
                    'education': result[8] or 'No education listed',
                    'accomplishments': result[9] or 'No accomplishments listed',
                    'cv_path': result[10]
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting CV summary: {e}")
            return None
        finally:
            self.db_manager.disconnect()
    
    def get_cv_file_path(self, detail_id: int) -> str:
        """Get CV file path untuk detail_id tertentu"""
        try:
            summary = self.get_cv_summary_enhanced(detail_id)
            return summary.get('cv_path', '') if summary else ''
        
        except Exception as e:
            print(f"Error getting CV path: {e}")
            return ''
    
    def get_database_stats(self) -> Dict:
        """Get database dan cache statistics"""
        try:
            cache_stats = self.cache_manager.get_cache_stats()
            
            if not self.db_manager.connect():
                return cache_stats
            
            cursor = self.db_manager.connection.cursor()
            
            # Get database stats
            cursor.execute("SELECT COUNT(*) FROM ApplicantProfile")
            total_applicants = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ApplicationDetail")
            total_applications = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT application_role, COUNT(*) 
                FROM ApplicationDetail 
                WHERE application_role IS NOT NULL 
                GROUP BY application_role 
                ORDER BY COUNT(*) DESC 
                LIMIT 10
            """)
            roles_data = cursor.fetchall()
            applications_by_role = {role: count for role, count in roles_data}
            
            return {
                **cache_stats,
                'total_applicants': total_applicants,
                'total_applications': total_applications,
                'applications_by_role': applications_by_role,
                'cache_hit_rate': len(self.cache_manager.memory_cache) / max(total_applications, 1) * 100
            }
            
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {}
        finally:
            self.db_manager.disconnect()
    
    def validate_keywords(self, keywords: str) -> Dict:
        """Validate keywords input"""
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
integrated_backend = IntegratedATSBackend()

def get_integrated_backend() -> IntegratedATSBackend:
    """Get integrated backend instance"""
    return integrated_backend

# Main API functions
def search_cvs_integrated(
    keywords: str, 
    algorithm: str = "kmp", 
    top_n: int = 10,
    fuzzy_threshold: float = 70.0
) -> Dict:
    """Main search API dengan caching"""
    
    backend = get_integrated_backend()
    
    if not backend._cache_initialized:
        backend.initialize()
    
    try:
        search_result, cv_matches = backend.search_cvs_with_cache(
            keywords, algorithm, top_n, fuzzy_threshold
        )
        
        return {
            "success": True,
            "search_metadata": {
                "keywords_searched": search_result.keywords_searched,
                "algorithm_used": search_result.algorithm_used,
                "exact_match_time_ms": round(search_result.exact_match_time, 2),
                "fuzzy_match_time_ms": round(search_result.fuzzy_match_time, 2),
                "total_cvs_scanned": search_result.total_cvs_scanned
            },
            "exact_matches": search_result.exact_matches,
            "fuzzy_matches": search_result.fuzzy_matches,
            "cv_results": [
                {
                    "detail_id": cv.detail_id,
                    "applicant_name": cv.applicant_name,
                    "application_role": cv.application_role,
                    "total_matches": cv.total_matches,
                    "keyword_matches": cv.keyword_matches,
                    "similarity_score": cv.similarity_score,
                    "match_sources": cv.match_sources
                }
                for cv in cv_matches
            ]
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {str(e)}"
        }

def get_cv_summary_integrated(detail_id: int) -> Dict:
    """Get CV summary API"""
    backend = get_integrated_backend()
    
    try:
        summary = backend.get_cv_summary_enhanced(detail_id)
        
        if summary:
            return {
                "success": True,
                "summary": summary
            }
        else:
            return {
                "success": False,
                "error": "CV summary not found"
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get summary: {str(e)}"
        }

def get_stats_integrated() -> Dict:
    """Get statistics API"""
    backend = get_integrated_backend()
    
    try:
        stats = backend.get_database_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get stats: {str(e)}"
        }

def refresh_cache_integrated() -> Dict:
    """Refresh entire cache API"""
    backend = get_integrated_backend()
    
    try:
        # Reinitialize cache
        initialize_realtime_cv_cache()
        backend._cache_initialized = True
        
        stats = backend.get_database_stats()
        
        return {
            "success": True,
            "message": "Cache refreshed successfully",
            "stats": stats
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to refresh cache: {str(e)}"
        }