#!/usr/bin/env python3
"""
Simple fix untuk cache loading error
Update cv_cache_manager.py dengan path resolution yang bekerja
"""

import os
import sys

# Add backend path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def fix_cache_manager():
    """Update cv_cache_manager.py dengan fix yang diperlukan"""
    
    cache_manager_path = os.path.join('backend', 'cv_cache_manager.py')
    
    if not os.path.exists(cache_manager_path):
        print(f"❌ File not found: {cache_manager_path}")
        return
    
    # Read current file
    with open(cache_manager_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple path resolution method to add
    path_resolution_code = '''
    def _resolve_cv_path(self, cv_path: str) -> str:
        """Simple path resolution for CV files"""
        if not cv_path:
            return ""
        
        # If already exists, return as-is
        if os.path.exists(cv_path):
            return os.path.abspath(cv_path)
        
        # Database format: "data/FOLDER/file.pdf"
        # Convert to: "../data/FOLDER/file.pdf"
        if cv_path.startswith('data/'):
            # Remove 'data/' prefix  
            relative_path = cv_path[5:]
            
            # From test results, we know this works:
            candidate = os.path.join('..', 'data', relative_path)
            if os.path.exists(candidate):
                return os.path.abspath(candidate)
        
        return ""
'''
    
    # Check if method already exists
    if '_resolve_cv_path' not in content:
        # Find the class definition
        class_pos = content.find('class CVCacheManager:')
        if class_pos != -1:
            # Find the end of __init__ method
            init_end = content.find('\n    def ', class_pos + content[class_pos:].find('def __init__'))
            if init_end != -1:
                # Insert the method after __init__
                content = content[:init_end] + path_resolution_code + content[init_end:]
                print("✅ Added _resolve_cv_path method")
    
    # Fix extract_cv_if_needed method
    extract_method = '''    def extract_cv_if_needed(self, cv_data: Dict) -> Optional[CVCacheEntry]:
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
            return None'''
    
    # Replace extract_cv_if_needed method if exists
    start_marker = 'def extract_cv_if_needed(self, cv_data: Dict) -> Optional[CVCacheEntry]:'
    if start_marker in content:
        start_pos = content.find(start_marker)
        if start_pos != -1:
            # Find the next method or end of class
            next_method_pos = content.find('\n    def ', start_pos + 1)
            if next_method_pos == -1:
                next_method_pos = len(content)
            
            # Replace the method
            content = content[:start_pos] + extract_method[4:] + content[next_method_pos:]
            print("✅ Updated extract_cv_if_needed method")
    
    # Write back to file
    with open(cache_manager_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Updated {cache_manager_path}")

def remove_corrupted_cache():
    """Remove corrupted cache file"""
    cache_files = [
        'backend/cv_cache.db',
        'cv_cache.db'
    ]
    
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
                print(f"✅ Removed corrupted cache: {cache_file}")
            except Exception as e:
                print(f"❌ Could not remove {cache_file}: {e}")

def test_simple_extraction():
    """Test simple PDF extraction"""
    print(f"\n🧪 TESTING SIMPLE PDF EXTRACTION")
    print("=" * 35)
    
    test_file = "../data/INFORMATION-TECHNOLOGY/15118506.pdf"
    
    if os.path.exists(test_file):
        try:
            # Try importing the extractor
            sys.path.append('data_extractor')
            from extractor import extract_realtime
            
            result = extract_realtime(test_file)
            if result.success:
                print(f"✅ PDF extraction works!")
                print(f"   Text length: {len(result.cv_raw_text)} chars")
                print(f"   Summary: {result.summary_section[:50]}...")
            else:
                print(f"❌ PDF extraction failed: {result.error_message}")
                
        except ImportError as e:
            print(f"❌ Could not import extractor: {e}")
        except Exception as e:
            print(f"❌ Extraction error: {e}")
    else:
        print(f"❌ Test file not found: {test_file}")

if __name__ == "__main__":
    print("🔧 FIXING CACHE LOADING ERROR")
    print("=" * 40)
    
    # Step 1: Remove corrupted cache
    remove_corrupted_cache()
    
    # Step 2: Fix cache manager code
    fix_cache_manager()
    
    # Step 3: Test PDF extraction
    test_simple_extraction()
    
    print(f"\n✅ FIXES APPLIED!")
    print(f"📝 Now run: python cache_diagnostics.py")