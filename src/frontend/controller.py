import sys
import os

# Add backend path to imports - Fixed path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, '..', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

print(f"Looking for backend at: {backend_path}")

try:
    # Import the new backend
    from main_be import get_ats_backend
    print("Successfully imported backend!")
except ImportError as e:
    print(f"Failed to import backend: {e}")
    print(f"Available files in backend directory:")
    try:
        for file in os.listdir(backend_path):
            if file.endswith('.py'):
                print(f"   - {file}")
    except:
        print("   (Cannot list directory)")
    
    print("Trying alternative imports...")
    raise e

class ATSController:
    def __init__(self):
        self.backend = get_ats_backend()
        self.initialized = False
    
    def initialize(self):
        if not self.initialized:
            print("🔧 Initializing ATS backend...")
            self.initialized = self.backend.initialize()
            if self.initialized:
                print("Backend initialized successfully!")
            else:
                print("Backend initialization failed!")
        return self.initialized
    
    def search_top_matches(self, keywords: str, algorithm: str, top_n: int):
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
            # Use the new backend search
            results = self.backend.search_cvs(
                keywords=keywords,
                algorithm=backend_algorithm,
                top_results=top_n,
                fuzzy_threshold=75.0
            )
            
            if not results.get('success'):
                print(f"Search failed: {results.get('error')}")
                return []
            
            # Convert backend results to frontend format
            frontend_results = []
            for cv in results['cv_results']:
                frontend_results.append({
                    "detail_id": cv['detail_id'],
                    "applicant_name": cv['applicant_name'],
                    "application_role": cv['application_role'],
                    "match": cv['total_matches'],
                    "keywords": cv['keyword_matches'],
                    "cv_path": self.backend.get_cv_file_path(cv['detail_id'])
                })
            
            # Add search metadata for display
            metadata = results['search_metadata']
            return {
                "matches": frontend_results,
                "metadata": {
                    "algorithm_used": metadata['algorithm_used'],
                    "exact_time_ms": metadata['exact_match_time_ms'],
                    "fuzzy_time_ms": metadata['fuzzy_match_time_ms'],
                    "cvs_scanned": metadata['total_cvs_scanned'],
                    "total_exact_matches": sum(results['exact_matches'].values()),
                    "fuzzy_matches_found": len([k for k, v in results['fuzzy_matches'].items() if v])
                }
            }
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def get_applicant_summary_from_detail_id(self, detail_id: int):
        if not self.initialize():
            return None
        
        try:
            result = self.backend.get_cv_summary(detail_id)
            
            if result.get('success'):
                summary = result['summary']
                
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
                    "cv_path": summary.get('cv_path', '')
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
                return result['stats']
            return {}
        except Exception as e:
            print(f"Stats error: {e}")
            return {}
    
    def validate_keywords(self, keywords: str):
        return self.backend.validate_keywords(keywords)
    
    def get_available_algorithms(self):
        return ["KMP", "BM", "AC"]  # Frontend names

# Global controller instance
ats_controller = ATSController()

# Legacy function wrappers for compatibility
def search_top_matches(keywords: str, algorithm: str, top_n: int):
    result = ats_controller.search_top_matches(keywords, algorithm, top_n)
    
    if isinstance(result, dict) and "matches" in result:
        return result["matches"]
    elif isinstance(result, list):
        return result
    else:
        return []

def get_applicant_summary_from_path(cv_path: str):
    # Try to extract detail_id from path or search for it
    # For now, we'll return None and encourage using the new method
    print("get_applicant_summary_from_path is deprecated")
    print("Use get_applicant_summary_from_detail_id instead")
    return None

def get_applicant_summary_from_detail_id(detail_id: int):
    return ats_controller.get_applicant_summary_from_detail_id(detail_id)

# Export the controller for direct use
def get_controller():
    return ats_controller