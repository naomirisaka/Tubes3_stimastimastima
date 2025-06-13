# frontend/controller.py
"""
Updated controller with encryption support.
This is a minimal change to your existing controller.py
"""

import sys
import os

# Add path resolution utilities (keep your existing functions)
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

# Add backend path to imports - Updated for encryption support
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, '..', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

print(f"Looking for backend at: {backend_path}")

# 🔐 ENCRYPTION SUPPORT: Check if encryption is enabled
USE_ENCRYPTION = os.getenv('ATS_USE_ENCRYPTION', 'false').lower() == 'true'

try:
    if USE_ENCRYPTION:
        print("🔐 Using ENCRYPTED backend")
        from backend.encrypted_main_be import get_ats_backend
        print("✅ Successfully imported encrypted backend!")
    else:
        print("🔓 Using STANDARD backend")
        from backend.main_be import get_ats_backend
        print("✅ Successfully imported standard backend!")
        
except ImportError as e:
    print(f"❌ Failed to import backend: {e}")
    
    # Fallback logic
    if USE_ENCRYPTION:
        print("🔄 Encrypted backend not available, trying standard...")
        try:
            from backend.main_be import get_ats_backend
            print("⚠️  Using standard backend as fallback")
        except ImportError:
            print("❌ No backend available!")
            raise e
    else:
        print("🔄 Standard backend not available, trying encrypted...")
        try:
            from backend.encrypted_main_be import get_ats_backend
            print("⚠️  Using encrypted backend as fallback")
        except ImportError:
            print("❌ No backend available!")
            raise e

class ATSController:
    """Controller for the ATS frontend using the appropriate backend."""
    
    def __init__(self):
        self.backend = get_ats_backend()
        self.initialized = False
        self.encryption_enabled = USE_ENCRYPTION
    
    def initialize(self):
        """Initialize the backend connection."""
        if not self.initialized:
            if self.encryption_enabled:
                print("🔐 Initializing encrypted ATS backend...")
            else:
                print("🔓 Initializing standard ATS backend...")
                
            self.initialized = self.backend.initialize()
            
            if self.initialized:
                print("✅ Backend initialized successfully!")
                if self.encryption_enabled:
                    print("🔐 All data will be decrypted during searches")
            else:
                print("❌ Backend initialization failed!")
        return self.initialized
    
    def search_top_matches(self, keywords: str, algorithm: str, top_n: int):
        """Search for top CV matches using the backend."""
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
            # Use the backend search (works with both encrypted and standard)
            results = self.backend.search_cvs(
                keywords=keywords,
                algorithm=backend_algorithm,
                top_results=top_n,
                fuzzy_threshold=60.0
            )
            
            if not results.get('success'):
                print(f"Search failed: {results.get('error')}")
                return []
            
            # Convert backend results to frontend format with resolved paths
            frontend_results = []
            for cv in results['cv_results']:
                # Get the original CV path from backend
                original_cv_path = self.backend.get_cv_file_path(cv['detail_id'])
                
                # Resolve the path to an absolute path
                resolved_cv_path = resolve_cv_path(original_cv_path)
                
                # Debug path resolution
                if not resolved_cv_path:
                    print(f"Could not resolve path for {cv['applicant_name']}: {original_cv_path}")
                    
                    # Try alternative: search by detail_id or applicant name
                    # Extract filename if possible
                    if original_cv_path:
                        filename = os.path.basename(original_cv_path)
                        resolved_cv_path = find_cv_by_filename(filename)
                        if resolved_cv_path:
                            print(f"Found by filename: {resolved_cv_path}")
                
                frontend_results.append({
                    "detail_id": cv['detail_id'],
                    "applicant_name": cv['applicant_name'],
                    "application_role": cv['application_role'],
                    "match": cv['total_matches'],
                    "keywords": cv['keyword_matches'],
                    "cv_path": resolved_cv_path,  # Use resolved path
                    "original_path": original_cv_path  # Keep original for debugging
                })
            
            # Add search metadata for display
            metadata = results['search_metadata']
            return {
                "matches": frontend_results,
                "metadata": {
                    "algorithm_used": metadata['algorithm_used'],
                    "exact_time_ms": metadata['exact_match_time_ms'],
                    "fuzzy_time_ms": metadata.get('fuzzy_match_time_ms', 0),
                    "cvs_scanned": metadata['total_cvs_scanned'],
                    "total_exact_matches": sum(results['exact_matches'].values()),
                    "fuzzy_matches_found": len([k for k, v in results.get('fuzzy_matches', {}).items() if v]),
                    "encryption_status": "🔐 ENCRYPTED" if self.encryption_enabled else "🔓 STANDARD"
                }
            }
            
        except Exception as e:
            print(f"Search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_applicant_summary_from_detail_id(self, detail_id: int):
        """Get applicant summary using detail_id from the backend."""
        if not self.initialize():
            return None
        
        try:
            result = self.backend.get_cv_summary(detail_id)
            
            if result.get('success'):
                summary = result['summary']
                
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
                    "original_path": original_cv_path,  # Keep original for debugging
                    "encryption_status": "🔐 DECRYPTED" if self.encryption_enabled else "🔓 STANDARD"
                }
            else:
                print(f"Failed to get summary: {result.get('error')}")
                return None
                
        except Exception as e:
            print(f"Summary error: {e}")
            return None
    
    def get_database_stats(self):
        """Get database statistics for display."""
        if not self.initialize():
            return {}
        
        try:
            result = self.backend.get_database_statistics()
            if result.get('success'):
                stats = result['stats']
                # Add encryption status to stats
                stats['encryption_enabled'] = self.encryption_enabled
                return stats
            return {}
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
def test_encryption_integration():
    """Test encryption integration with controller."""
    print("🧪 TESTING ENCRYPTION INTEGRATION")
    print("=" * 40)
    
    controller = get_controller()
    
    print(f"Encryption enabled: {controller.encryption_enabled}")
    print(f"Backend type: {type(controller.backend).__name__}")
    
    if controller.initialize():
        print("✅ Controller initialization: PASSED")
        
        # Test database stats
        stats = controller.get_database_stats()
        if stats:
            print(f"📊 Found {stats.get('total_applications', 0)} CVs")
            if 'encryption_status' in stats:
                print(f"🔐 Status: {stats['encryption_status']}")
            print("✅ Database stats: PASSED")
        else:
            print("⚠️  Database stats: No data")
        
        # Test keyword validation
        validation = controller.validate_keywords("Python, Java")
        if validation.get('valid'):
            print("✅ Keyword validation: PASSED")
        else:
            print("❌ Keyword validation: FAILED")
    else:
        print("❌ Controller initialization: FAILED")

if __name__ == "__main__":
    test_encryption_integration()