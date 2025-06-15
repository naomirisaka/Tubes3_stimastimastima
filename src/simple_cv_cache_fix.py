#!/usr/bin/env python3
"""
Simple fix untuk cv_cache_manager.py
Update path resolution berdasarkan test yang berhasil
"""

import os

def create_fixed_method():
    """Create the correct method to add to cv_cache_manager.py"""
    
    method_code = '''
    def _resolve_cv_path(self, cv_path: str) -> str:
        """Correct path resolution for CV files"""
        if not cv_path:
            return ""
        
        # If already exists, return as-is
        if os.path.exists(cv_path):
            return os.path.abspath(cv_path)
        
        # Database format: "data/FOLDER/file.pdf" 
        # Convert to: "../data/FOLDER/file.pdf"
        if cv_path.startswith('data/'):
            relative_path = cv_path[5:]  # Remove 'data/' prefix
            candidate = os.path.join('..', 'data', relative_path)
            if os.path.exists(candidate):
                return os.path.abspath(candidate)
        
        return ""
    
    def extract_cv_if_needed(self, cv_data: Dict) -> Optional[CVCacheEntry]:
        """Extract CV dengan path resolution yang benar"""
        detail_id = cv_data['detail_id']
        cv_path = cv_data['cv_path']
        
        # RESOLVE PATH CORRECTLY
        resolved_path = self._resolve_cv_path(cv_path)
        
        if not resolved_path:
            print(f"❌ CV file not found: {cv_path}")
            return None
        
        print(f"✅ Found CV: {os.path.basename(resolved_path)}")
        
        # Check if extraction needed
        if not self._needs_extraction(detail_id, resolved_path):
            return self.memory_cache[detail_id]
        
        print(f"🔄 Extracting: {cv_data['applicant_name']}")
        
        try:
            extraction_result = extract_realtime(resolved_path)
            
            if not extraction_result.success:
                print(f"❌ Extraction failed: {extraction_result.error_message}")
                return None
            
            # Create cache entry
            entry = CVCacheEntry(
                detail_id=detail_id,
                cv_path=cv_path,
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
            
            self.memory_cache[detail_id] = entry
            self._save_cache_entry(entry)
            
            print(f"✅ Successfully cached: {cv_data['applicant_name']}")
            return entry
            
        except Exception as e:
            print(f"❌ Error extracting CV: {e}")
            return None
'''
    
    return method_code

def manual_fix_instructions():
    """Provide manual fix instructions"""
    print("🔧 MANUAL FIX INSTRUCTIONS")
    print("=" * 30)
    print()
    print("1. Open file: backend/cv_cache_manager.py")
    print()
    print("2. Find class CVCacheManager and add this method:")
    print()
    
    method = create_fixed_method()
    print(method)
    
    print()
    print("3. Save the file")
    print()
    print("4. Run: python cache_diagnostics.py")

def test_correct_path():
    """Test the correct path format"""
    print("🧪 TESTING CORRECT PATH FORMAT")
    print("=" * 35)
    
    test_paths = [
        "data/BPO/38707449.pdf",
        "data/INFORMATION-TECHNOLOGY/15118506.pdf",
        "data/CHEF/11121498.pdf"
    ]
    
    for db_path in test_paths:
        print(f"\n🔍 Database path: {db_path}")
        
        if db_path.startswith('data/'):
            relative_path = db_path[5:]  # Remove 'data/'
            correct_path = os.path.join('..', 'data', relative_path)
            
            exists = os.path.exists(correct_path)
            status = "✅" if exists else "❌"
            print(f"   {status} Resolved: {correct_path}")
            
            if exists:
                abs_path = os.path.abspath(correct_path)
                print(f"      Absolute: {abs_path}")

if __name__ == "__main__":
    print("🔧 CV CACHE MANAGER FIX")
    print("=" * 40)
    
    test_correct_path()
    manual_fix_instructions()
    
    print("\n📝 SUMMARY:")
    print("The issue is that cv_cache_manager.py doesn't have the correct")
    print("_resolve_cv_path method. Add the method above to fix it.")