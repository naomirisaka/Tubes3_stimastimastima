# frontend/controller.py - Fixed version

"""
Updated controller dengan proper CV path resolution dan integrated backend.
"""

import sys
import os

# Add path resolution utilities
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

# Add backend path to imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, '..', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

print(f"Looking for backend at: {backend_path}")

try:
    # Import the integrated backend
    from integrated_ats_backend import get_integrated_backend
    print("Successfully imported integrated backend!")
except ImportError as e:
    print(f"Failed to import integrated backend: {e}")
    raise e

class ATSController:
    """Controller for the ATS frontend using the integrated backend."""
    
    def __init__(self):
        self.backend = get_integrated_backend()
        self.initialized = False
    
    def initialize(self):
        """Initialize the backend connection."""
        if not self.initialized:
            print("Initializing ATS backend...")
            self.initialized = self.backend.initialize()
            if self.initialized:
                print("Backend initialized successfully!")
            else:
                print("Backend initialization failed!")
        return self.initialized
    
    def search_top_matches(self, keywords: str, algorithm: str, top_n: int):
        """Search for top CV matches using the integrated backend."""
        if not self.initialize():
            return []
        
        # Map frontend algorithm names to backend names
        algorithm_map = {
            "KMP": "kmp",
            "BM": "boyer_moore", 
            "AC": "aho_corasick"
        }
        
        backend_algorithm = algorithm_map.get(algorithm, "kmp")
        
        try:
            # Use the integrated backend search
            results = self.backend.search_cvs_with_cache(
                keywords=keywords,
                algorithm=backend_algorithm,
                top_n=top_n,
                fuzzy_threshold=60.0
            )
            
            # Handle tuple return (SearchResult, List[CVMatch])
            if isinstance(results, tuple) and len(results) == 2:
                search_result, cv_matches = results
                
                # Convert backend results to frontend format with resolved paths
                frontend_results = []
                for cv in cv_matches:
                    # Get the original CV path from backend
                    original_cv_path = self.backend.get_cv_file_path(cv.detail_id)
                    
                    # Resolve the path to an absolute path
                    resolved_cv_path = resolve_cv_path(original_cv_path)
                    
                    # Debug path resolution
                    if not resolved_cv_path:
                        print(f"Could not resolve path for {cv.applicant_name}: {original_cv_path}")
                        
                        # Try alternative: search by filename
                        if original_cv_path:
                            filename = os.path.basename(original_cv_path)
                            resolved_cv_path = find_cv_by_filename(filename)
                            if resolved_cv_path:
                                print(f"Found by filename: {resolved_cv_path}")
                    
                    frontend_results.append({
                        "detail_id": cv.detail_id,
                        "applicant_name": cv.applicant_name,
                        "application_role": cv.application_role,
                        "match": cv.total_matches,
                        "keywords": cv.keyword_matches,
                        "cv_path": resolved_cv_path,  # Use resolved path
                        "original_path": original_cv_path  # Keep original for debugging
                    })
                
                # Add search metadata for display
                return {
                    "matches": frontend_results,
                    "metadata": {
                        "algorithm_used": search_result.algorithm_used,
                        "exact_time_ms": search_result.exact_match_time,
                        "fuzzy_time_ms": search_result.fuzzy_match_time,
                        "cvs_scanned": search_result.total_cvs_scanned,
                        "total_exact_matches": sum(search_result.exact_matches.values()),
                        "fuzzy_matches_found": len([k for k, v in search_result.fuzzy_matches.items() if v])
                    }
                }
            else:
                print(f"Unexpected backend return format: {type(results)}")
                return []
            
        except Exception as e:
            print(f"Search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_applicant_summary_from_detail_id(self, detail_id: int):
        """Get applicant summary using detail_id from the integrated backend."""
        if not self.initialize():
            return None
        
        try:
            summary = self.backend.get_cv_summary_enhanced(detail_id)
            
            if summary:
                # Resolve CV path
                original_cv_path = summary.get('cv_path', '')
                resolved_cv_path = resolve_cv_path(original_cv_path)
                
                if not resolved_cv_path and original_cv_path:
                    # Try to find by filename
                    filename = os.path.basename(original_cv_path)
                    resolved_cv_path = find_cv_by_filename(filename)
                
                # Format for frontend display
                return {
                    "detail_id": detail_id,
                    "first_name": summary.get('name', '').split(' ')[0] if summary.get('name') else 'Unknown',
                    "last_name": ' '.join(summary.get('name', '').split(' ')[1:]) if summary.get('name') and len(summary.get('name', '').split(' ')) > 1 else '',
                    "phone": summary.get('phone', 'Not available'),
                    "address": summary.get('address', 'Not available'),
                    "role": summary.get('role', 'Not specified'),
                    "summary": summary.get('summary', 'No summary available'),
                    "skills": summary.get('skills', 'No skills listed'),
                    "experience": summary.get('experience', 'No experience listed'),
                    "education": summary.get('education', 'No education listed'),
                    "accomplishments": summary.get('accomplishments', 'No accomplishments listed'),
                    "cv_path": resolved_cv_path,  # Use resolved path
                    "original_path": original_cv_path  # Keep original for debugging
                }
            else:
                print(f"No summary found for detail_id: {detail_id}")
                return None
                
        except Exception as e:
            print(f"Summary error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_database_stats(self):
        """Get database statistics for display."""
        if not self.initialize():
            return {}
        
        try:
            stats = self.backend.get_database_stats()
            return stats
        except Exception as e:
            print(f"Stats error: {e}")
            return {}
    
    def validate_keywords(self, keywords: str):
        """Validate keywords input."""
        return self.backend.validate_keywords(keywords)
    
    def get_available_algorithms(self):
        """Get available algorithms for the dropdown."""
        return ["KMP", "BM", "AC"]  # Frontend names

# Global controller instance
ats_controller = ATSController()

# Legacy function wrappers for compatibility
def search_top_matches(keywords: str, algorithm: str, top_n: int):
    """Legacy wrapper for search function."""
    result = ats_controller.search_top_matches(keywords, algorithm, top_n)
    
    if isinstance(result, dict) and "matches" in result:
        # Return just the matches for backward compatibility
        return result["matches"]
    elif isinstance(result, list):
        return result
    else:
        return []

def get_applicant_summary_from_detail_id(detail_id: int):
    """Function for getting summary by detail_id."""
    return ats_controller.get_applicant_summary_from_detail_id(detail_id)

# Export the controller for direct use
def get_controller():
    """Get the ATS controller instance."""
    return ats_controller

# Test function
def test_path_resolution():
    """Test CV path resolution."""
    print("TESTING CV PATH RESOLUTION")
    print("=" * 40)
    
    # Test with sample paths
    test_paths = [
        "../../data/ENGINEERING/13149176.pdf",
        "data/ENGINEERING/13149176.pdf",
        "ENGINEERING/13149176.pdf"
    ]
    
    for path in test_paths:
        resolved = resolve_cv_path(path)
        print(f"'{path}' -> '{resolved}' ({'Success' if resolved and os.path.exists(resolved) else 'Failed'})")


# Add this to your controller.py to test
def debug_search_issue():
    """Debug the specific search issue"""
    from backend.main_be import get_ats_backend
    
    backend = get_ats_backend()
    if not backend.initialize():
        print("Failed to initialize backend")
        return
    
    # Test the exact search that's failing
    keywords = "machine"  # The keyword from your screenshot
    algorithm = "boyer_moore"  # Algorithm from your screenshot
    
    print("🐛 DEBUGGING SEARCH ISSUE")
    print("=" * 40)
    print(f"Keywords: '{keywords}'")
    print(f"Algorithm: {algorithm}")
    
    # Run debug search
    if hasattr(backend, 'debug_fuzzy_search_flow'):
        results = backend.debug_fuzzy_search_flow(keywords, algorithm, 10)
    else:
        print("Debug method not available, running normal search...")
        results = backend.search_cvs(keywords, algorithm, 10, 60.0)
        print(f"Results: {results}")