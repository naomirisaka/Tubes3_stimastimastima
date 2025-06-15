# Create this as backend/test_encryption.py

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_database_connection
from search_engine import DatabaseCVSearchEngine

def test_database_connection():
    """Test basic database connection and encryption setup."""
    print("=== TESTING DATABASE CONNECTION ===")
    
    db_manager = get_database_connection()
    
    if not db_manager.connect():
        print("❌ Failed to connect to database")
        return False
    
    print("✅ Database connection successful")
    
    # Test encryption status
    encryption_status = db_manager.get_encryption_status()
    print(f"Encryption enabled: {encryption_status['encryption_enabled']}")
    print(f"Encryption manager ready: {encryption_status['encryption_manager_ready']}")
    
    # Test basic queries
    try:
        stats = db_manager.get_database_stats()
        print(f"Total applicants: {stats['total_applicants']}")
        print(f"Total applications: {stats['total_applications']}")
        print(f"Encrypted applications: {stats['encrypted_applications']}")
        print(f"Encrypted profiles: {stats['encrypted_profiles']}")
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return False
    
    db_manager.disconnect()
    print("✅ Database test completed successfully")
    return True

def test_cv_loading():
    """Test CV loading and caching."""
    print("\n=== TESTING CV LOADING ===")
    
    try:
        search_engine = DatabaseCVSearchEngine()
        search_engine.load_cv_cache()
        
        print(f"✅ Loaded {len(search_engine.cv_cache)} CVs into cache")
        
        # Test a few CVs
        if search_engine.cv_cache:
            sample_ids = list(search_engine.cv_cache.keys())[:3]
            for detail_id in sample_ids:
                cv_text = search_engine.cv_cache[detail_id]
                print(f"  CV {detail_id}: {len(cv_text)} characters")
                if len(cv_text) > 100:
                    print(f"    Preview: {cv_text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading CVs: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_applicant_loading():
    """Test applicant profile loading."""
    print("\n=== TESTING APPLICANT LOADING ===")
    
    try:
        search_engine = DatabaseCVSearchEngine()
        search_engine.load_applicant_cache()
        
        print(f"✅ Loaded {len(search_engine.applicant_cache)} applicant profiles")
        
        # Test a few profiles
        if search_engine.applicant_cache:
            sample_ids = list(search_engine.applicant_cache.keys())[:3]
            for detail_id in sample_ids:
                profile = search_engine.applicant_cache[detail_id]
                print(f"  Profile {detail_id}: {profile['name']} - {profile['role']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading applicant profiles: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search_functionality():
    """Test basic search functionality."""
    print("\n=== TESTING SEARCH FUNCTIONALITY ===")
    
    try:
        search_engine = DatabaseCVSearchEngine()
        
        # Test search
        from search_engine import search_database_cvs
        
        result, cv_matches = search_database_cvs(
            keywords="engineer, python, developer",
            algorithm="kmp",
            top_n=5,
            fuzzy_threshold=70.0
        )
        
        print(f"✅ Search completed successfully")
        print(f"  Keywords searched: {result.keywords_searched}")
        print(f"  Algorithm used: {result.algorithm_used}")
        print(f"  CVs scanned: {result.total_cvs_scanned}")
        print(f"  Exact matches: {result.exact_matches}")
        print(f"  Results found: {len(cv_matches)}")
        
        # Show top result
        if cv_matches:
            top_result = cv_matches[0]
            print(f"  Top result: {top_result.applicant_name} - {top_result.application_role}")
            print(f"    Total matches: {top_result.total_matches}")
            print(f"    Keyword matches: {top_result.keyword_matches}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in search functionality: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 TESTING ATS BACKEND WITH ENCRYPTION SUPPORT")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Run all tests
    tests = [
        ("Database Connection", test_database_connection),
        ("CV Loading", test_cv_loading),
        ("Applicant Loading", test_applicant_loading),
        ("Search Functionality", test_search_functionality)
    ]
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                all_tests_passed = False
                print(f"❌ {test_name} FAILED")
            else:
                print(f"✅ {test_name} PASSED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            all_tests_passed = False
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED! Your ATS backend is ready to use.")
        print("\nYou can now run your frontend with:")
        print("python -m frontend.main")
    else:
        print("❌ SOME TESTS FAILED. Please check the errors above.")
        print("\nCommon issues to check:")
        print("1. Database connection credentials")
        print("2. Missing encryption files (ats_encryption.key, ats_config.json)")
        print("3. Database schema (missing is_encrypted columns)")
        print("4. Empty database (no CV data)")
    
    print("\nEncryption file locations:")
    db_manager = get_database_connection()
    file_locations = db_manager.encryption_manager.get_file_locations()
    print(f"  Key file: {file_locations['key_file'] or 'Not found'}")
    print(f"  Config file: {file_locations['config_file'] or 'Not found'}")
    print(f"  Search paths checked: {len(file_locations['search_paths'])}")