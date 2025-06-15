#!/usr/bin/env python3
"""
CV Cache Diagnostics Script
Check why CVs are not loading into cache properly.
"""

import os
import sys

# Add backend path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from backend.database import get_database_connection
except ImportError:
    sys.path.append('.')
    from database import get_database_connection

def check_database_records():
    """Check what's actually in the database"""
    print("🔍 CHECKING DATABASE RECORDS")
    print("=" * 40)
    
    db_manager = get_database_connection()
    if not db_manager.connect():
        print("❌ Failed to connect to database")
        return
    
    try:
        cursor = db_manager.connection.cursor()
        
        # Count total records
        cursor.execute("SELECT COUNT(*) FROM ApplicationDetail")
        total_count = cursor.fetchone()[0]
        print(f"📊 Total ApplicationDetail records: {total_count}")
        
        # Check cv_path distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN cv_path IS NULL THEN 'NULL'
                    WHEN cv_path = '' THEN 'EMPTY'
                    ELSE 'HAS_PATH'
                END as path_status,
                COUNT(*) as count
            FROM ApplicationDetail 
            GROUP BY path_status
        """)
        
        print("\n📁 CV Path Status:")
        for status, count in cursor.fetchall():
            print(f"   {status}: {count} records")
        
        # Show sample cv_paths
        cursor.execute("""
            SELECT cv_path, cv_raw_text IS NOT NULL as has_text, 
                   LENGTH(cv_raw_text) as text_length
            FROM ApplicationDetail 
            WHERE cv_path IS NOT NULL AND cv_path != ''
            LIMIT 10
        """)
        
        print("\n📄 Sample CV Paths:")
        for cv_path, has_text, text_length in cursor.fetchall():
            text_status = f"✅ {text_length} chars" if has_text else "❌ No text"
            file_exists = "📁 ✅" if os.path.exists(cv_path) else "📁 ❌"
            print(f"   {cv_path} | {text_status} | {file_exists}")
        
        # Check text extraction status
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN cv_raw_text IS NULL OR cv_raw_text = '' THEN 'NO_TEXT'
                    WHEN LENGTH(cv_raw_text) < 100 THEN 'SHORT_TEXT'
                    ELSE 'GOOD_TEXT'
                END as text_status,
                COUNT(*) as count
            FROM ApplicationDetail 
            GROUP BY text_status
        """)
        
        print("\n📝 Text Extraction Status:")
        for status, count in cursor.fetchall():
            print(f"   {status}: {count} records")
        
        # Check file paths that exist vs don't exist
        cursor.execute("SELECT cv_path FROM ApplicationDetail WHERE cv_path IS NOT NULL AND cv_path != ''")
        paths = cursor.fetchall()
        
        existing_files = 0
        missing_files = 0
        
        for (cv_path,) in paths:
            if os.path.exists(cv_path):
                existing_files += 1
            else:
                missing_files += 1
        
        print(f"\n📂 File System Check:")
        print(f"   ✅ Files that exist: {existing_files}")
        print(f"   ❌ Files missing: {missing_files}")
        
    finally:
        db_manager.disconnect()

def check_data_directory():
    """Check the data directory structure"""
    print("\n📁 CHECKING DATA DIRECTORY")
    print("=" * 40)
    
    # Check different possible data directory locations
    possible_data_dirs = ['data', '../data', '../../data']
    
    for data_dir in possible_data_dirs:
        if os.path.exists(data_dir):
            print(f"✅ Found data directory: {data_dir}")
            
            # List subdirectories and PDF counts
            for item in os.listdir(data_dir):
                item_path = os.path.join(data_dir, item)
                if os.path.isdir(item_path):
                    pdf_files = [f for f in os.listdir(item_path) if f.lower().endswith('.pdf')]
                    print(f"   📂 {item}: {len(pdf_files)} PDF files")
                    
                    # Show first few files
                    for pdf in pdf_files[:3]:
                        full_path = os.path.join(item_path, pdf)
                        relative_path = os.path.join(item, pdf)
                        print(f"      📄 {pdf} (exists: {os.path.exists(full_path)})")
                        print(f"         Relative: {relative_path}")
            break
    else:
        print("❌ No data directory found")

def test_cache_loading_logic():
    """Test the cache loading logic"""
    print("\n🔄 TESTING CACHE LOADING LOGIC")
    print("=" * 40)
    
    try:
        # Try to import and test the cache manager
        from backend.cv_cache_manager import cv_cache_manager
        
        print("✅ Successfully imported cv_cache_manager")
        
        # Load CV data
        cv_data_list = cv_cache_manager.load_cv_data_from_database()
        print(f"📊 Loaded {len(cv_data_list)} CV records from database")
        
        if cv_data_list:
            # Test processing first few CVs
            print("\n🧪 Testing CV processing:")
            
            for i, cv_data in enumerate(cv_data_list[:3]):
                print(f"\n   CV {i+1}: {cv_data.get('applicant_name', 'Unknown')}")
                print(f"      Path: {cv_data.get('cv_path', 'No path')}")
                print(f"      Has existing text: {bool(cv_data.get('existing_raw_text'))}")
                
                # FIXED PATH RESOLUTION TEST
                cv_path = cv_data.get('cv_path', '')
                if cv_path:
                    resolved_path = test_path_resolution_fixed(cv_path)
                    
                    if resolved_path:
                        print(f"      ✅ File found at: {resolved_path}")
                        
                        # Try to extract CV
                        try:
                            entry = cv_cache_manager.extract_cv_if_needed(cv_data)
                            if entry:
                                print(f"      ✅ CV processed successfully")
                                print(f"         Text length: {len(entry.raw_text)} chars")
                            else:
                                print(f"      ❌ CV processing failed")
                        except Exception as e:
                            print(f"      ❌ CV processing error: {e}")
                    else:
                        print(f"      ❌ File not found after path resolution")
        
        # Get cache stats
        stats = cv_cache_manager.get_cache_stats()
        print(f"\n📈 Cache Stats:")
        print(f"   Total CVs in cache: {stats.get('total_cvs', 0)}")
        print(f"   Cache size: {stats.get('cache_size_mb', 0):.2f} MB")
        
    except ImportError as e:
        print(f"❌ Failed to import cache manager: {e}")
    except Exception as e:
        print(f"❌ Error testing cache: {e}")

def test_path_resolution_fixed(cv_path: str) -> str:
    """Fixed path resolution for testing"""
    if not cv_path:
        return ""
    
    # If already exists, return as-is
    if os.path.exists(cv_path):
        return os.path.abspath(cv_path)
    
    # Database format: "data/FOLDER/file.pdf"
    # Convert to: "../data/FOLDER/file.pdf"
    if cv_path.startswith('data/'):
        # Remove 'data/' prefix
        relative_path = cv_path[5:]  # Remove 'data/'
        
        # Based on our successful test, use this pattern:
        candidate = os.path.join('..', 'data', relative_path)
        if os.path.exists(candidate):
            return os.path.abspath(candidate)
        
        print(f"         Tried: {candidate} (not found)")
    
    return ""

# Also update the cv_cache_manager.py file with correct path resolution:
def update_cv_cache_manager():
    """Update cv_cache_manager.py with correct path resolution"""
    
    cache_manager_code = '''
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
            # Remove 'data/' prefix
            relative_path = cv_path[5:]  # Remove 'data/'
            
            # From our test, we know this works:
            candidate = os.path.join('..', 'data', relative_path)
            if os.path.exists(candidate):
                return os.path.abspath(candidate)
        
        return ""
    '''
    
    print("📝 Copy this method to cv_cache_manager.py:")
    print(cache_manager_code)

def suggest_fixes():
    """Suggest potential fixes"""
    print("\n💡 POTENTIAL FIXES")
    print("=" * 40)
    
    print("Based on the diagnostics above, here are potential issues and fixes:")
    print()
    print("1. 📁 File Path Issues:")
    print("   - If files are missing, the cv_path in database might be wrong")
    print("   - Try running from the correct directory (project root)")
    print("   - Check if data/ directory is in the right location")
    print()
    print("2. 📝 Text Extraction Issues:")
    print("   - If files exist but no text, PDFs might be corrupted or image-only")
    print("   - Check if PyMuPDF is installed: pip install PyMuPDF")
    print()
    print("3. 🔄 Cache Loading Issues:")
    print("   - Cache might be looking in wrong directory")
    print("   - Path resolution in cache manager might need fixing")
    print()
    print("4. 🗄️ Database Issues:")
    print("   - If cv_path is NULL or empty, re-run the SQL script")
    print("   - Check if the SQL script populated paths correctly")

def main():
    """Main diagnostic function"""
    print("🔍 ATS CV CACHE DIAGNOSTICS")
    print("=" * 50)
    print("This script will help diagnose why CVs aren't loading into cache")
    print()
    
    # Run all diagnostics
    check_database_records()
    check_data_directory()
    test_cache_loading_logic()
    suggest_fixes()
    
    print("\n✅ Diagnostics completed!")
    print("Review the output above to identify the issue.")

if __name__ == "__main__":
    main()