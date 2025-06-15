# frontend/controller_integrated.py

"""
Updated controller menggunakan integrated backend dengan caching system.
"""

import sys
import os
import time

# Add backend path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, '..', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    # Import integrated backend
    from backend.integrated_ats_backend import (
        get_integrated_backend,
        search_cvs_integrated,
        get_cv_summary_integrated,
        get_stats_integrated,
        add_cv_integrated,
        refresh_cache_integrated
    )
    print("✅ Successfully imported integrated backend!")
except ImportError as e:
    print(f"❌ Failed to import integrated backend: {e}")
    # Fallback to old backend
    try:
        from main_be import get_ats_backend
        print("⚠️ Using fallback backend")
    except ImportError:
        raise ImportError("No backend available")

def resolve_cv_path(cv_path: str) -> str:
    """Resolve CV path to absolute path."""
    if not cv_path:
        return ""
    
    # If already absolute and exists, return it
    if os.path.isabs(cv_path) and os.path.exists(cv_path):
        return cv_path
    
    # Get the current script directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try different base paths
    possible_bases = [
        current_dir,  # frontend/
        os.path.dirname(current_dir),  # src/
        os.path.dirname(os.path.dirname(current_dir)),  # project root/
    ]
    
    # Clean the cv_path (remove leading ../ or ./)
    clean_path = cv_path
    while clean_path.startswith('../') or clean_path.startswith('./'):
        if clean_path.startswith('../'):
            clean_path = clean_path[3:]
        elif clean_path.startswith('./'):
            clean_path = clean_path[2:]
    
    # Try each base path
    for base in possible_bases:
        # Try direct join
        full_path = os.path.join(base, clean_path)
        if os.path.exists(full_path):
            return os.path.abspath(full_path)
        
        # Try with 'data' prepended if not already there
        if not clean_path.startswith('data'):
            data_path = os.path.join(base, 'data', clean_path)
            if os.path.exists(data_path):
                return os.path.abspath(data_path)
    
    # Try searching by filename only
    if '/' in clean_path or '\\' in clean_path:
        filename = os.path.basename(clean_path)
        found_path = find_cv_by_filename(filename)
        if found_path:
            return found_path
    
    return ""

def find_cv_by_filename(filename: str) -> str:
    """Search for CV file by filename in data directory."""
    if not filename:
        return ""
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    possible_roots = [
        os.path.dirname(current_dir),  # src/
        os.path.dirname(os.path.dirname(current_dir)),  # project root/
    ]
    
    for root in possible_roots:
        data_dir = os.path.join(root, 'data')
        if os.path.exists(data_dir):
            for dirpath, dirnames, filenames in os.walk(data_dir):
                if filename in filenames:
                    return os.path.join(dirpath, filename)
    
    return ""

class IntegratedATSController:
    """Controller untuk ATS frontend menggunakan integrated backend."""
    
    def __init__(self):
        self.backend = get_integrated_backend()
        self.initialized = False
        self.cache_stats = {}
    
    def initialize(self):
        """Initialize the integrated backend."""
        if not self.initialized:
            print("🚀 Initializing Integrated ATS Controller...")
            start_time = time.time()
            
            self.initialized = self.backend.initialize()
            
            if self.initialized:
                init_time = (time.time() - start_time) * 1000
                print(f"✅ Controller initialized successfully in {init_time:.1f}ms!")
                
                # Get initial stats
                stats_result = get_stats_integrated()
                if stats_result.get('success'):
                    self.cache_stats = stats_result['stats']
                    print(f"📊 Loaded {self.cache_stats.get('total_cvs', 0)} CVs into cache")
            else:
                print("❌ Controller initialization failed!")
        
        return self.initialized
    
    def search_top_matches(self, keywords: str, algorithm: str, top_n: int):
        """Search for top CV matches menggunakan integrated backend."""
        if not self.initialize():
            return {
                "matches": [],
                "metadata": {
                    "error": "Backend not initialized",
                    "algorithm_used": algorithm,
                    "exact_time_ms": 0,
                    "fuzzy_time_ms": 0,
                    "cvs_scanned": 0
                }
            }
        
        # Map frontend algorithm names to backend names
        algorithm_map = {
            "KMP": "kmp",
            "BM": "boyer_moore", 
            "AC": "aho_corasick"
        }
        
        backend_algorithm = algorithm_map.get(algorithm, "kmp")
        
        try:
            # Use integrated search
            start_time = time.time()
            results = search_cvs_integrated(
                keywords=keywords,
                algorithm=backend_algorithm,
                top_n=top_n,
                fuzzy_threshold=70.0
            )
            total_time = (time.time() - start_time) * 1000
            
            if not results.get('success'):
                print(f"❌ Search failed: {results.get('error')}")
                return {
                    "matches": [],
                    "metadata": {
                        "error": results.get('error'),
                        "algorithm_used": backend_algorithm,
                        "exact_time_ms": 0,
                        "fuzzy_time_ms": 0,
                        "cvs_scanned": 0
                    }
                }
            
            # Convert backend results to frontend format dengan resolved paths
            frontend_results = []
            for cv in results['cv_results']:
                # Get the CV path dan resolve
                original_cv_path = ""
                
                # Try to get CV path from summary first
                summary_result = get_cv_summary_integrated(cv['detail_id'])
                if summary_result.get('success'):
                    original_cv_path = summary_result['summary'].get('cv_path', '')
                
                # Resolve the path to an absolute path
                resolved_cv_path = resolve_cv_path(original_cv_path)
                
                # Debug path resolution
                if not resolved_cv_path and original_cv_path:
                    print(f"⚠️ Could not resolve path for {cv['applicant_name']}: {original_cv_path}")
                    
                    # Try alternative: search by filename
                    if original_cv_path:
                        filename = os.path.basename(original_cv_path)
                        resolved_cv_path = find_cv_by_filename(filename)
                        if resolved_cv_path:
                            print(f"✅ Found by filename: {resolved_cv_path}")
                
                frontend_results.append({
                    "detail_id": cv['detail_id'],
                    "applicant_name": cv['applicant_name'],
                    "application_role": cv['application_role'],
                    "match": cv['total_matches'],
                    "keywords": cv['keyword_matches'],
                    "cv_path": resolved_cv_path,  # Use resolved path
                    "original_path": original_cv_path,  # Keep original for debugging
                    "similarity_score": cv.get('similarity_score', 0),
                    "match_sources": cv.get('match_sources', ['Cache'])
                })
            
            # Add search metadata untuk display
            metadata = results['search_metadata']
            return {
                "matches": frontend_results,
                "metadata": {
                    "algorithm_used": metadata['algorithm_used'],
                    "exact_time_ms": metadata['exact_match_time_ms'],
                    "fuzzy_time_ms": metadata['fuzzy_match_time_ms'],
                    "cvs_scanned": metadata['total_cvs_scanned'],
                    "total_exact_matches": sum(results['exact_matches'].values()),
                    "fuzzy_matches_found": len([k for k, v in results['fuzzy_matches'].items() if v]),
                    "total_search_time_ms": round(total_time, 2),
                    "keywords_searched": metadata['keywords_searched'],
                    "exact_matches_detail": results['exact_matches'],
                    "fuzzy_matches_detail": results['fuzzy_matches']
                }
            }
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "matches": [],
                "metadata": {
                    "error": str(e),
                    "algorithm_used": backend_algorithm,
                    "exact_time_ms": 0,
                    "fuzzy_time_ms": 0,
                    "cvs_scanned": 0
                }
            }
    
    def get_applicant_summary_from_detail_id(self, detail_id: int):
        """Get applicant summary menggunakan detail_id dari integrated backend."""
        if not self.initialize():
            return None
        
        try:
            result = get_cv_summary_integrated(detail_id)
            
            if result.get('success'):
                summary = result['summary']
                
                # Resolve CV path
                original_cv_path = summary.get('cv_path', '')
                resolved_cv_path = resolve_cv_path(original_cv_path)
                
                if not resolved_cv_path and original_cv_path:
                    # Try to find by filename
                    filename = os.path.basename(original_cv_path)
                    resolved_cv_path = find_cv_by_filename(filename)
                
                # Format untuk frontend display
                name_parts = summary.get('name', '').split(' ')
                first_name = name_parts[0] if name_parts else 'Unknown'
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                
                return {
                    "detail_id": detail_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": summary.get('phone', 'Not available'),
                    "address": summary.get('address', 'Not available'),
                    "role": summary.get('role', 'Not specified'),
                    "summary": summary.get('summary', 'No summary available'),
                    "skills": summary.get('skills', 'No skills listed'),
                    "experience": summary.get('experience', 'No experience listed'),
                    "education": summary.get('education', 'No education listed'),
                    "accomplishments": summary.get('accomplishments', 'No accomplishments listed'),
                    "cv_path": resolved_cv_path,  # Use resolved path
                    "original_path": original_cv_path,  # Keep original for debugging
                    "cache_hit": True  # Indicate this came from cache
                }
            else:
                print(f"❌ Failed to get summary: {result.get('error')}")
                return None
                
        except Exception as e:
            print(f"❌ Summary error: {e}")
            return None
    
    def add_new_cv(self, applicant_data: dict, cv_file_path: str):
        """Add new CV to system dengan automatic caching."""
        if not self.initialize():
            return {"success": False, "error": "Backend not initialized"}
        
        try:
            result = add_cv_integrated(applicant_data, cv_file_path)
            
            if result.get('success'):
                # Update cache stats
                stats_result = get_stats_integrated()
                if stats_result.get('success'):
                    self.cache_stats = stats_result['stats']
                
                print(f"✅ Successfully added CV: {applicant_data.get('first_name')} {applicant_data.get('last_name')}")
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to add CV: {str(e)}"
            }
    
    def refresh_cache(self):
        """Refresh entire cache system."""
        try:
            print("🔄 Refreshing cache...")
            result = refresh_cache_integrated()
            
            if result.get('success'):
                self.cache_stats = result.get('stats', {})
                print(f"✅ Cache refreshed successfully")
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to refresh cache: {str(e)}"
            }
    
    def get_database_stats(self):
        """Get database dan cache statistics untuk display."""
        if not self.initialize():
            return {}
        
        try:
            result = get_stats_integrated()
            if result.get('success'):
                self.cache_stats = result['stats']
                return result['stats']
            return {}
        except Exception as e:
            print(f"❌ Stats error: {e}")
            return {}
    
    def validate_keywords(self, keywords: str):
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
    
    def get_available_algorithms(self):
        """Get available algorithms untuk dropdown."""
        return ["KMP", "BM", "AC"]  # Frontend names
    
    def get_cache_info(self):
        """Get cache information untuk debug/monitoring."""
        return {
            "initialized": self.initialized,
            "cache_stats": self.cache_stats,
            "backend_type": "Integrated with Caching"
        }

# Global controller instance
integrated_controller = IntegratedATSController()

# Legacy function wrappers untuk compatibility
def search_top_matches(keywords: str, algorithm: str, top_n: int):
    """Legacy wrapper for search function."""
    result = integrated_controller.search_top_matches(keywords, algorithm, top_n)
    
    if isinstance(result, dict) and "matches" in result:
        return result["matches"]
    elif isinstance(result, list):
        return result
    else:
        return []

def get_applicant_summary_from_detail_id(detail_id: int):
    """Function untuk getting summary by detail_id."""
    return integrated_controller.get_applicant_summary_from_detail_id(detail_id)

def get_controller():
    """Get the integrated ATS controller instance."""
    return integrated_controller

def add_cv_to_system(applicant_data: dict, cv_file_path: str):
    """Add new CV to system."""
    return integrated_controller.add_new_cv(applicant_data, cv_file_path)

def refresh_system_cache():
    """Refresh system cache."""
    return integrated_controller.refresh_cache()

# Performance monitoring functions
def get_performance_metrics():
    """Get performance metrics untuk monitoring."""
    controller = get_controller()
    stats = controller.get_database_stats()
    cache_info = controller.get_cache_info()
    
    return {
        "system_status": "Ready" if controller.initialized else "Not Ready",
        "total_cvs_cached": stats.get('total_cvs', 0),
        "cache_size_mb": stats.get('cache_size_mb', 0),
        "cache_hit_rate": stats.get('cache_hit_rate', 0),
        "last_cache_update": stats.get('last_update'),
        "backend_type": cache_info["backend_type"],
        "available_algorithms": controller.get_available_algorithms()
    }

# Test function
def test_integrated_controller():
    """Test integrated controller functionality."""
    print("🧪 TESTING INTEGRATED CONTROLLER")
    print("=" * 40)
    
    controller = get_controller()
    
    # Test initialization
    print("1. Testing initialization...")
    if controller.initialize():
        print("   ✅ Initialization successful")
    else:
        print("   ❌ Initialization failed")
        return
    
    # Test search
    print("\n2. Testing search...")
    result = controller.search_top_matches("Python, engineer", "KMP", 3)
    if result["matches"]:
        print(f"   ✅ Found {len(result['matches'])} matches")
        print(f"   ⏱️ Search time: {result['metadata']['total_search_time_ms']:.1f}ms")
    else:
        print("   ⚠️ No matches found")
    
    # Test summary
    if result["matches"]:
        print("\n3. Testing summary...")
        detail_id = result["matches"][0]["detail_id"]
        summary = controller.get_applicant_summary_from_detail_id(detail_id)
        if summary:
            print(f"   ✅ Summary retrieved for {summary['first_name']} {summary['last_name']}")
        else:
            print("   ❌ Summary retrieval failed")
    
    # Test stats
    print("\n4. Testing statistics...")
    stats = controller.get_database_stats()
    if stats:
        print(f"   ✅ Stats retrieved: {stats.get('total_applications', 0)} applications")
        print(f"   📊 Cache size: {stats.get('cache_size_mb', 0):.2f} MB")
    else:
        print("   ❌ Stats retrieval failed")
    
    # Performance metrics
    print("\n5. Performance metrics...")
    metrics = get_performance_metrics()
    print(f"   🚀 System status: {metrics['system_status']}")
    print(f"   💾 CVs cached: {metrics['total_cvs_cached']}")
    print(f"   🎯 Cache hit rate: {metrics['cache_hit_rate']:.1f}%")
    
    print("\n✅ Controller testing completed!")

if __name__ == "__main__":
    test_integrated_controller()