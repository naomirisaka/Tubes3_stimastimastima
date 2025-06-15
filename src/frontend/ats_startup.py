# ats_startup.py - Script untuk auto-initialize ATS system

import os
import sys
import time
import argparse
from pathlib import Path

def setup_paths():
    """Setup paths untuk import modules."""
    current_dir = Path(__file__).parent.absolute()
    
    # Add all necessary paths
    paths_to_add = [
        current_dir,  # root
        current_dir / "backend",
        current_dir / "frontend", 
        current_dir / "data_extractor",
        current_dir / "src",
        current_dir / "src" / "backend",
        current_dir / "src" / "frontend"
    ]
    
    for path in paths_to_add:
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))
    
    print(f"📁 Working directory: {current_dir}")

def check_dependencies():
    """Check if all required dependencies are available."""
    print("🔍 Checking dependencies...")
    
    required_modules = [
        'mysql.connector',
        'fitz',  # PyMuPDF
        'flet',
        're'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except ImportError:
            print(f"   ❌ {module} - MISSING")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n⚠️ Missing dependencies: {', '.join(missing_modules)}")
        print("Please install them using:")
        print("pip install mysql-connector-python PyMuPDF flet")
        return False
    
    return True

def check_database_connection():
    """Check database connection."""
    print("\n🗄️ Checking database connection...")
    
    try:
        import database
        db_manager = database.get_database_connection()
        
        if db_manager.connect():
            print("   ✅ Database connection successful")
            
            # Check if tables exist
            cursor = db_manager.connection.cursor()
            
            tables_to_check = ['ApplicantProfile', 'ApplicationDetail']
            existing_tables = []
            
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    existing_tables.append(table)
                    print(f"   ✅ Table {table}: {count} records")
                except Exception as e:
                    print(f"   ❌ Table {table}: Not found or error")
            
            db_manager.disconnect()
            
            if len(existing_tables) == len(tables_to_check):
                return True
            else:
                print("   ⚠️ Some tables are missing. Please run the SQL schema first.")
                return False
        else:
            print("   ❌ Database connection failed")
            return False
            
    except ImportError:
        print("   ❌ Database module not found")
        return False
    except Exception as e:
        print(f"   ❌ Database check failed: {e}")
        return False

def check_data_directory():
    """Check if data directory exists and has CV files."""
    print("\n📁 Checking data directory...")
    
    current_dir = Path(__file__).parent.absolute()
    data_paths_to_check = [
        current_dir / "data",
        current_dir / "src" / "data",
        current_dir.parent / "data"
    ]
    
    data_dir = None
    for path in data_paths_to_check:
        if path.exists():
            data_dir = path
            print(f"   ✅ Found data directory: {path}")
            break
    
    if not data_dir:
        print("   ❌ Data directory not found")
        print("   Please create a 'data' directory with CV files")
        return False
    
    # Count PDF files
    pdf_count = 0
    subdirs = []
    
    for item in data_dir.iterdir():
        if item.is_dir():
            subdirs.append(item.name)
            pdf_files = list(item.glob("*.pdf"))
            pdf_count += len(pdf_files)
            if pdf_files:
                print(f"   📄 {item.name}: {len(pdf_files)} PDF files")
    
    if pdf_count > 0:
        print(f"   ✅ Total PDF files found: {pdf_count}")
        return True
    else:
        print("   ⚠️ No PDF files found in data directory")
        return False

def initialize_cache_system():
    """Initialize the CV cache system."""
    print("\n💾 Initializing cache system...")
    
    try:
        from cv_cache_manager import initialize_cv_cache
        
        start_time = time.time()
        cache_manager = initialize_cv_cache()
        init_time = time.time() - start_time
        
        stats = cache_manager.get_cache_stats()
        
        print(f"   ✅ Cache initialized in {init_time:.2f} seconds")
        print(f"   📊 Cached CVs: {stats.get('total_cvs', 0)}")
        print(f"   💾 Cache size: {stats.get('cache_size_mb', 0):.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Cache initialization failed: {e}")
        return False

def test_search_functionality():
    """Test basic search functionality."""
    print("\n🔍 Testing search functionality...")
    
    try:
        from integrated_ats_backend import search_cvs_integrated
        
        # Test simple search
        test_keywords = "engineer, software, developer"
        print(f"   🧪 Testing search with keywords: {test_keywords}")
        
        start_time = time.time()
        results = search_cvs_integrated(test_keywords, "kmp", 5)
        search_time = (time.time() - start_time) * 1000
        
        if results.get('success'):
            cv_results = results.get('cv_results', [])
            metadata = results.get('search_metadata', {})
            
            print(f"   ✅ Search completed in {search_time:.1f}ms")
            print(f"   📊 Algorithm time: {metadata.get('exact_match_time_ms', 0):.1f}ms")
            print(f"   📄 Scanned: {metadata.get('total_cvs_scanned', 0)} CVs")
            print(f"   🎯 Found: {len(cv_results)} matches")
            
            if cv_results:
                top_result = cv_results[0]
                print(f"   🏆 Top match: {top_result['applicant_name']} ({top_result['total_matches']} matches)")
            
            return True
        else:
            print(f"   ❌ Search failed: {results.get('error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Search test failed: {e}")
        return False

def run_startup_checks(skip_cache_init=False):
    """Run all startup checks."""
    print("🚀 ATS SYSTEM STARTUP CHECKS")
    print("=" * 50)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Database", check_database_connection),
        ("Data Directory", check_data_directory),
    ]
    
    if not skip_cache_init:
        checks.append(("Cache System", initialize_cache_system))
        checks.append(("Search Functionality", test_search_functionality))
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"   ❌ {check_name} check failed with exception: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL CHECKS PASSED - System ready!")
        print("\n🎯 NEXT STEPS:")
        print("   1. Run: python main.py (to start GUI)")
        print("   2. Or import: from frontend.controller_integrated import get_controller")
        print("   3. Or test: python integrated_ats_backend.py")
    else:
        print("❌ SOME CHECKS FAILED - Please fix issues above")
        print("\n🔧 COMMON SOLUTIONS:")
        print("   - Install missing dependencies with pip")
        print("   - Check database connection and run schema SQL")
        print("   - Ensure data directory contains PDF files")
        print("   - Verify file paths and permissions")
    
    return all_passed

def quick_search_demo():
    """Run a quick search demo."""
    print("\n🎬 QUICK SEARCH DEMO")
    print("=" * 30)
    
    try:
        from frontend.controller_integrated import get_controller
        
        controller = get_controller()
        
        if not controller.initialize():
            print("❌ Controller initialization failed")
            return
        
        # Demo searches
        demo_searches = [
            ("Python developer", "KMP"),
            ("data engineer", "BM"), 
            ("software engineer", "AC")
        ]
        
        for keywords, algorithm in demo_searches:
            print(f"\n🔍 Searching: '{keywords}' using {algorithm}")
            
            result = controller.search_top_matches(keywords, algorithm, 3)
            
            if result["matches"]:
                print(f"   ✅ Found {len(result['matches'])} matches")
                print(f"   ⏱️ Time: {result['metadata']['total_search_time_ms']:.1f}ms")
                
                top_match = result["matches"][0]
                print(f"   🏆 Top: {top_match['applicant_name']} ({top_match['match']} matches)")
            else:
                print("   📝 No matches found")
        
        # Show system stats
        stats = controller.get_database_stats()
        if stats:
            print(f"\n📊 SYSTEM STATS:")
            print(f"   📄 Total Applications: {stats.get('total_applications', 0)}")
            print(f"   💾 Cache Size: {stats.get('cache_size_mb', 0):.2f} MB")
            print(f"   🎯 Cache Hit Rate: {stats.get('cache_hit_rate', 0):.1f}%")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")

def main():
    """Main startup function."""
    parser = argparse.ArgumentParser(description='ATS System Startup Script')
    parser.add_argument('--skip-cache', action='store_true', 
                       help='Skip cache initialization (faster startup)')
    parser.add_argument('--demo', action='store_true',
                       help='Run quick search demo after checks')
    parser.add_argument('--check-only', action='store_true',
                       help='Only run checks, do not initialize cache')
    
    args = parser.parse_args()
    
    # Setup paths
    setup_paths()
    
    # Run startup checks
    skip_cache = args.skip_cache or args.check_only
    success = run_startup_checks(skip_cache_init=skip_cache)
    
    # Run demo if requested and checks passed
    if args.demo and success and not args.check_only:
        quick_search_demo()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)