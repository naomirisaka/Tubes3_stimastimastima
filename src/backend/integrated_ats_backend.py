# integrated_ats_backend.py - Backend ATS dengan sistem caching

import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import os

from backend.cv_cache_manager import ( 
    realtime_cv_cache_manager as cv_cache_manager,
    initialize_realtime_cv_cache, 
    search_cvs_realtime, 
    get_cv_summary_realtime_cached
)
import database
# from backend import search_engine
from data_extractor.extractor import extract_realtime
from levenshtein import fuzzy_search_keywords, parse_keywords

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

class IntegratedATSBackend:
    """Backend ATS yang terintegrasi dengan caching system"""
    
    def __init__(self):
        self.cache_manager = cv_cache_manager
        self.db_manager = database.get_database_connection()
        self._cache_initialized = False
        self.fuzzy_threshold = 70.0
    
    def initialize(self) -> bool:
        """Initialize backend dengan loading cache"""
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
        
        # Exact matching menggunakan cache
        start_time = time.time()
        cached_results = search_cvs_realtime(keywords, algorithm, top_n * 2)  # Get more for fuzzy fallback
        exact_time = (time.time() - start_time) * 1000
        
        # Count exact matches per keyword
        exact_matches = {}
        for keyword in keyword_list:
            exact_matches[keyword] = sum(
                result['keyword_matches'].get(keyword, 0) 
                for result in cached_results
            )
        
        # Fuzzy matching untuk keywords yang tidak ditemukan
        start_fuzzy = time.time()
        fuzzy_matches = {}
        missing_keywords = [kw for kw in keyword_list if exact_matches.get(kw, 0) == 0]
        
        if missing_keywords:
            print(f"Performing fuzzy search for: {missing_keywords}")
            
            # Fuzzy search pada cached text
            for detail_id, cache_entry in self.cache_manager.memory_cache.items():
                fuzzy_result = fuzzy_search_keywords(
                    cache_entry.raw_text, 
                    missing_keywords, 
                    fuzzy_threshold
                )
                
                for keyword, similar_words in fuzzy_result.items():
                    if similar_words and keyword not in fuzzy_matches:
                        fuzzy_matches[keyword] = similar_words[:3]  # Top 3 similar words
        
        fuzzy_time = (time.time() - start_fuzzy) * 1000
        
        # Convert results to CVMatch objects
        cv_matches = []
        for i, result in enumerate(cached_results[:top_n]):
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
        summary = get_cv_summary_realtime_cached(detail_id)
        if summary:
            return summary
        
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
                    'phone': result[2],
                    'address': result[3],
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
    
    def refresh_cache_for_cv(self, detail_id: int) -> bool:
        """Refresh cache untuk specific CV"""
        try:
            cv_data_list = self.cache_manager.load_cv_metadata_from_database()
            target_cv = next((cv for cv in cv_data_list if cv['detail_id'] == detail_id), None)
            
            if target_cv:
                entry = self.cache_manager.extract_cv_realtime(target_cv)
                return entry is not None
            
            return False
            
        except Exception as e:
            print(f"Error refreshing cache for CV {detail_id}: {e}")
            return False
    
    def add_new_cv_to_cache(self, applicant_data: Dict, cv_file_path: str) -> Dict:
        """Add new CV to database dan cache"""
        try:
            # Extract CV terlebih dahulu
            extraction_result = extract_realtime(cv_file_path)
            
            if not extraction_result.success:
                return {
                    "success": False,
                    "error": f"CV extraction failed: {extraction_result.error_message}"
                }
            
            # Insert ke database
            if not self.db_manager.connect():
                return {"success": False, "error": "Database connection failed"}
            
            cursor = self.db_manager.connection.cursor()
            
            # Insert applicant profile
            cursor.execute("""
                INSERT INTO ApplicantProfile (first_name, last_name, phone_number, address)
                VALUES (%s, %s, %s, %s)
            """, (
                applicant_data.get('first_name', ''),
                applicant_data.get('last_name', ''),
                applicant_data.get('phone', ''),
                applicant_data.get('address', '')
            ))
            
            applicant_id = cursor.lastrowid
            
            # Insert application detail
            cursor.execute("""
                INSERT INTO ApplicationDetail 
                (applicant_id, application_role, cv_path, cv_raw_text, 
                 summary_section, skills_section, experience_section, 
                 education_section, accomplishments_section, extraction_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                applicant_id,
                applicant_data.get('role', 'General'),
                cv_file_path,
                extraction_result.cv_raw_text,
                extraction_result.summary_section,
                extraction_result.skills_section,
                extraction_result.experience_section,
                extraction_result.education_section,
                extraction_result.accomplishments_section,
                'completed'
            ))
            
            detail_id = cursor.lastrowid
            self.db_manager.connection.commit()
            
            # Update cache
            cv_data = {
                'detail_id': detail_id,
                'cv_path': cv_file_path,
                'applicant_name': f"{applicant_data.get('first_name', '')} {applicant_data.get('last_name', '')}",
                'application_role': applicant_data.get('role', 'General')
            }
            
            self.cache_manager.extract_cv_realtime(cv_data)
            
            return {
                "success": True,
                "detail_id": detail_id,
                "applicant_id": applicant_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error adding CV: {str(e)}"
            }
        finally:
            self.db_manager.disconnect()
    
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
                'cache_hit_rate': len(cache_stats) / max(total_applications, 1) * 100
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

def add_cv_integrated(applicant_data: Dict, cv_file_path: str) -> Dict:
    """Add new CV API"""
    backend = get_integrated_backend()
    return backend.add_new_cv_to_cache(applicant_data, cv_file_path)

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

# Demo dan testing functions
def demo_integrated_search():
    """Demo integrated search functionality"""
    print("DEMO: Integrated ATS Search with Caching")
    print("=" * 50)
    
    backend = get_integrated_backend()
    
    # Initialize
    if not backend.initialize():
        print("Failed to initialize backend")
        return
    
    # Demo search scenarios
    test_scenarios = [
        {
            "name": "Python Developer Search",
            "keywords": "Python, programming, software",
            "algorithm": "kmp"
        },
        {
            "name": "Data Analyst Search", 
            "keywords": "data, analysis, SQL",
            "algorithm": "boyer_moore"
        },
        {
            "name": "Multi-keyword Search (Aho-Corasick)",
            "keywords": "Java, Spring, REST, API",
            "algorithm": "aho_corasick"
        },
        {
            "name": "Fuzzy Search (with typos)",
            "keywords": "Pyhton, programing, databse",  # Intentional typos
            "algorithm": "kmp"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Keywords: {scenario['keywords']}")
        print(f"   Algorithm: {scenario['algorithm']}")
        
        # Perform search
        start_time = time.time()
        results = search_cvs_integrated(
            keywords=scenario['keywords'],
            algorithm=scenario['algorithm'],
            top_n=5,
            fuzzy_threshold=75.0
        )
        search_time = (time.time() - start_time) * 1000
        
        if results.get('success'):
            metadata = results['search_metadata']
            print(f"   ✅ Search completed in {search_time:.1f}ms")
            print(f"   📊 Algorithm time: {metadata['exact_match_time_ms']:.1f}ms")
            print(f"   📄 Scanned: {metadata['total_cvs_scanned']} CVs")
            
            # Show exact matches
            exact_total = sum(results['exact_matches'].values())
            print(f"   🎯 Total exact matches: {exact_total}")
            
            # Show top results
            cv_results = results['cv_results']
            if cv_results:
                print(f"   🏆 Top result: {cv_results[0]['applicant_name']}")
                print(f"      Role: {cv_results[0]['application_role']}")
                print(f"      Score: {cv_results[0]['total_matches']} matches")
                print(f"      Keywords found: {list(cv_results[0]['keyword_matches'].keys())}")
            else:
                print("   📝 No matching CVs found")
            
            # Show fuzzy matches if any
            fuzzy_count = sum(len(matches) for matches in results['fuzzy_matches'].values())
            if fuzzy_count > 0:
                print(f"   🔍 Fuzzy matches found: {fuzzy_count} similar words")
                for keyword, similar in results['fuzzy_matches'].items():
                    if similar:
                        similar_words = [f"{word}({score:.1f}%)" for word, score in similar[:2]]
                        print(f"      '{keyword}' → {', '.join(similar_words)}")
        
        else:
            print(f"   ❌ Search failed: {results.get('error')}")

def demo_cv_summary():
    """Demo CV summary functionality"""
    print("\n" + "=" * 50)
    print("DEMO: CV Summary Retrieval")
    print("=" * 50)
    
    # Get a sample CV for summary demo
    search_results = search_cvs_integrated("engineer, software", "kmp", 3)
    
    if search_results.get('success') and search_results.get('cv_results'):
        cv_result = search_results['cv_results'][0]
        detail_id = cv_result['detail_id']
        
        print(f"\nGetting summary for: {cv_result['applicant_name']}")
        print(f"Detail ID: {detail_id}")
        print(f"Role: {cv_result['application_role']}")
        print(f"Matches: {cv_result['total_matches']}")
        
        # Get detailed summary
        summary_result = get_cv_summary_integrated(detail_id)
        
        if summary_result.get('success'):
            summary = summary_result['summary']
            
            print(f"\n📋 DETAILED CV SUMMARY")
            print(f"   👤 Name: {summary.get('name')}")
            print(f"   📞 Phone: {summary.get('phone', 'N/A')}")
            print(f"   🏢 Role: {summary.get('role')}")
            
            # Show content previews
            sections = {
                'Summary': summary.get('summary', ''),
                'Skills': summary.get('skills', ''),
                'Experience': summary.get('experience', ''),
                'Education': summary.get('education', '')
            }
            
            for section_name, content in sections.items():
                if content and content.strip():
                    preview = content[:100] + "..." if len(content) > 100 else content
                    print(f"   📝 {section_name}: {preview}")
                else:
                    print(f"   📝 {section_name}: Not available")
            
            cv_path = summary.get('cv_path', '')
            if cv_path:
                print(f"   📁 CV File: {cv_path}")
                print(f"   📁 File exists: {os.path.exists(cv_path)}")
        
        else:
            print(f"❌ Failed to get summary: {summary_result.get('error')}")
    
    else:
        print("❌ No search results available for summary demo")

def show_system_stats():
    """Show comprehensive system statistics"""
    print("\n" + "=" * 50)
    print("SYSTEM STATISTICS")
    print("=" * 50)
    
    stats_result = get_stats_integrated()
    
    if stats_result.get('success'):
        stats = stats_result['stats']
        
        print(f"📊 DATABASE STATS:")
        print(f"   👥 Total Applicants: {stats.get('total_applicants', 0)}")
        print(f"   📄 Total Applications: {stats.get('total_applications', 0)}")
        print(f"   💾 Cache Size: {stats.get('cache_size_mb', 0):.2f} MB")
        print(f"   🎯 Cache Hit Rate: {stats.get('cache_hit_rate', 0):.1f}%")
        
        if stats.get('last_update'):
            print(f"   🕒 Last Cache Update: {stats['last_update']}")
        
        print(f"\n🏢 TOP APPLICATION ROLES:")
        roles_by_count = stats.get('applications_by_role', {})
        if roles_by_count:
            for i, (role, count) in enumerate(list(roles_by_count.items())[:10], 1):
                print(f"   {i:2d}. {role}: {count} applications")
        else:
            print("   No role data available")
    
    else:
        print(f"❌ Failed to get stats: {stats_result.get('error')}")

if __name__ == "__main__":
    print("🚀 INTEGRATED ATS BACKEND DEMO")
    print("=" * 60)
    
    try:
        # Run comprehensive demo
        demo_integrated_search()
        demo_cv_summary()
        show_system_stats()
        
        print(f"\n✅ DEMO COMPLETED SUCCESSFULLY!")
        print(f"\n📖 INTEGRATION GUIDE:")
        print(f"   1. Import: from integrated_ats_backend import search_cvs_integrated")
        print(f"   2. Search: results = search_cvs_integrated(keywords, algorithm)")
        print(f"   3. Summary: summary = get_cv_summary_integrated(detail_id)")
        print(f"   4. Stats: stats = get_stats_integrated()")
        print(f"   5. Add CV: result = add_cv_integrated(applicant_data, cv_path)")
        
        print(f"\n🎯 PERFORMANCE BENEFITS:")
        print(f"   - Fast searches using pre-extracted text cache")
        print(f"   - No repeated PDF extraction on each search")
        print(f"   - Supports all three algorithms: KMP, Boyer-Moore, Aho-Corasick")
        print(f"   - Automatic fuzzy matching for typos")
        print(f"   - Real-time cache updates when new CVs added")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()