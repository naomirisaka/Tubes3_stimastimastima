# startup.py - Script untuk menjalankan ATS Application dengan setup otomatis

import os
import sys
import subprocess
import time
from pathlib import Path

def print_banner():
    """Print startup banner"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    ATS CV Matcher - Matchify                 ║
║                Advanced CV Matching System                   ║
║                                                              ║
║  🚀 Powered by: KMP, Boyer-Moore, Aho-Corasick             ║
║  📄 Features: Smart CV Search, Fuzzy Matching, Regex       ║
║  💾 Backend: MySQL Database with Caching System            ║
╚══════════════════════════════════════════════════════════════╝
    """)

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def check_and_install_requirements():
    """Check and install required packages"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'flet>=0.15.0',
        'PyMuPDF>=1.23.0',
        'mysql-connector-python>=8.0.33'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        package_name = package.split('>=')[0]
        try:
            __import__(package_name.replace('-', '_'))
            print(f"   ✅ {package_name}")
        except ImportError:
            print(f"   ❌ {package_name} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n🔧 Installing missing packages...")
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"   ✅ Installed {package}")
            except subprocess.CalledProcessError:
                print(f"   ❌ Failed to install {package}")
                return False
    
    return True

def check_directory_structure():
    """Check if required directories exist"""
    print("\n📁 Checking directory structure...")
    
    required_dirs = [
        'frontend',
        'backend', 
        'data_extractor',
        'data'
    ]
    
    required_files = [
        'main.py',
        'frontend/views.py',
        'frontend/controller.py',
        'backend/database.py',
        'backend/search_engine.py'
    ]
    
    missing_items = []
    
    # Check directories
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"   ✅ {dir_name}/")
        else:
            print(f"   ❌ {dir_name}/ - MISSING")
            missing_items.append(f"directory: {dir_name}")
    
    # Check files
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"   ✅ {file_name}")
        else:
            print(f"   ⚠️ {file_name} - MISSING (may affect functionality)")
    
    if missing_items:
        print(f"\n⚠️ Missing items: {', '.join(missing_items)}")
        print("   Some features may not work properly.")
    
    return True

def check_database_connection():
    """Check database connection"""
    print("\n🗄️ Checking database connection...")
    
    try:
        import mysql.connector
        
        # Try to connect with default settings
        connection_configs = [
            {
                'host': 'localhost',
                'user': 'root',
                'password': '',
                'database': 'ats_db'
            },
            {
                'host': 'localhost', 
                'user': 'root',
                'password': '',
                'database': ''  # Connect without database first
            }
        ]
        
        for config in connection_configs:
            try:
                conn = mysql.connector.connect(**config)
                if config['database']:
                    print(f"   ✅ Connected to database: {config['database']}")
                else:
                    print(f"   ✅ Connected to MySQL server")
                
                # Check if ats_db exists
                cursor = conn.cursor()
                cursor.execute("SHOW DATABASES LIKE 'ats_db'")
                if cursor.fetchone():
                    print(f"   ✅ Database 'ats_db' exists")
                    
                    # Check if tables exist
                    cursor.execute("USE ats_db")
                    cursor.execute("SHOW TABLES")
                    tables = [table[0] for table in cursor.fetchall()]
                    
                    required_tables = ['ApplicantProfile', 'ApplicationDetail']
                    missing_tables = [table for table in required_tables if table not in tables]
                    
                    if missing_tables:
                        print(f"   ⚠️ Missing tables: {', '.join(missing_tables)}")
                        print(f"   💡 Run database_setup.sql to create required tables")
                    else:
                        print(f"   ✅ All required tables exist")
                        
                        # Check data
                        cursor.execute("SELECT COUNT(*) FROM ApplicantProfile")
                        applicant_count = cursor.fetchone()[0]
                        cursor.execute("SELECT COUNT(*) FROM ApplicationDetail") 
                        application_count = cursor.fetchone()[0]
                        
                        print(f"   📊 Data: {applicant_count} applicants, {application_count} applications")
                
                else:
                    print(f"   ⚠️ Database 'ats_db' does not exist")
                    print(f"   💡 Run database_setup.sql to create the database")
                
                conn.close()
                return True
                
            except mysql.connector.Error as e:
                continue
        
        print(f"   ❌ Could not connect to MySQL database")
        print(f"   💡 Make sure MySQL is running and credentials are correct")
        return False
        
    except ImportError:
        print(f"   ❌ MySQL connector not installed")
        return False

def check_sample_data():
    """Check if sample CV files exist"""
    print("\n📄 Checking sample CV data...")
    
    data_dir = Path("data")
    if not data_dir.exists():
        print(f"   ❌ Data directory not found")
        print(f"   💡 Create 'data' directory and add sample CV files")
        return False
    
    # Check for subdirectories
    expected_subdirs = ['ENGINEERING', 'DATASCI', 'BUSINESS', 'DESIGN']
    found_subdirs = []
    total_pdfs = 0
    
    for subdir in expected_subdirs:
        subdir_path = data_dir / subdir
        if subdir_path.exists():
            pdf_files = list(subdir_path.glob("*.pdf"))
            found_subdirs.append(subdir)
            total_pdfs += len(pdf_files)
            print(f"   ✅ {subdir}: {len(pdf_files)} PDF files")
        else:
            print(f"   ⚠️ {subdir}: directory not found")
    
    if total_pdfs > 0:
        print(f"   📊 Total: {total_pdfs} CV files ready for processing")
        return True
    else:
        print(f"   ⚠️ No PDF files found in data directory")
        print(f"   💡 Add sample CV files to test the application")
        return False

def run_system_tests():
    """Run basic system tests"""
    print("\n🧪 Running system tests...")
    
    # Test 1: Algorithm imports
    try:
        sys.path.insert(0, 'backend')
        from kmp import kmp_search
        from boyer_moore import boyer_moore_search
        from aho_corasick import aho_corasick_search
        from levenshtein import levenshtein_distance
        
        # Quick algorithm tests
        text = "hello world testing"
        pattern = "world"
        
        kmp_result = kmp_search(text, pattern)
        bm_result = boyer_moore_search(text, pattern)
        ac_result = aho_corasick_search(text, [pattern])
        lev_result = levenshtein_distance("hello", "helo")
        
        if kmp_result and bm_result and ac_result and lev_result >= 0:
            print("   ✅ String matching algorithms working")
        else:
            print("   ❌ Algorithm test failed")
            return False
            
    except ImportError as e:
        print(f"   ❌ Algorithm import failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Algorithm test error: {e}")
        return False
    
    # Test 2: PDF extraction
    try:
        from data_extractor.extractor import extract_pdf_text
        
        # Find a sample PDF to test
        data_dir = Path("data")
        sample_pdf = None
        for pdf_file in data_dir.rglob("*.pdf"):
            sample_pdf = pdf_file
            break
        
        if sample_pdf and sample_pdf.exists():
            text = extract_pdf_text(str(sample_pdf))
            if text and len(text) > 10:
                print("   ✅ PDF extraction working")
            else:
                print("   ⚠️ PDF extraction returned empty result")
        else:
            print("   ⚠️ No sample PDF found for testing")
            
    except ImportError:
        print("   ⚠️ PDF extractor not available (PyMuPDF missing?)")
    except Exception as e:
        print(f"   ❌ PDF extraction test error: {e}")
    
    return True

def create_run_script():
    """Create a convenient run script"""
    script_content = """#!/usr/bin/env python3
# run_ats.py - Convenient script to run ATS application

import subprocess
import sys
import os

def main():
    print("🚀 Starting ATS CV Matcher...")
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        # Run the main application
        subprocess.run([sys.executable, "main.py"], check=True)
    except KeyboardInterrupt:
        print("\\n👋 ATS application stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Application failed with exit code {e.returncode}")
    except FileNotFoundError:
        print("❌ main.py not found. Please ensure you're in the correct directory.")

if __name__ == "__main__":
    main()
"""
    
    with open("run_ats.py", "w") as f:
        f.write(script_content)
    
    # Make executable on Unix systems
    if os.name != 'nt':
        os.chmod("run_ats.py", 0o755)
    
    print("   ✅ Created run_ats.py script")

def print_next_steps(all_checks_passed):
    """Print next steps for user"""
    print("\n" + "="*60)
    
    if all_checks_passed:
        print("🎉 SYSTEM READY!")
        print("\n📋 Next steps:")
        print("   1. Run the application:")
        print("      python main.py")
        print("      # OR")
        print("      python run_ats.py")
        print("\n   2. Open your browser if it doesn't open automatically")
        print("   3. Enter keywords to search CVs")
        print("   4. Select algorithm (KMP, Boyer-Moore, or Aho-Corasick)")
        print("   5. Adjust number of results and click Search")
        
        print("\n🔧 Advanced usage:")
        print("   - Add more CV files to data/ directory")
        print("   - Run database_setup.sql for fresh database")
        print("   - Check logs if you encounter issues")
        
    else:
        print("⚠️ SETUP INCOMPLETE")
        print("\n🔧 Required actions:")
        print("   1. Install missing dependencies:")
        print("      pip install -r requirements.txt")
        print("\n   2. Setup database:")
        print("      - Start MySQL server")
        print("      - Run: mysql < database_setup.sql")
        print("\n   3. Add sample data:")
        print("      - Create data/ directory")
        print("      - Add PDF files in subdirectories")
        print("\n   4. Re-run this setup script")
    
    print("\n💡 For help:")
    print("   - Check README.md")
    print("   - Review tugas specification")
    print("   - Contact development team")
    print("="*60)

def main():
    """Main startup function"""
    print_banner()
    
    print("🔍 Starting system check...")
    time.sleep(1)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_and_install_requirements), 
        ("Directory Structure", check_directory_structure),
        ("Database Connection", check_database_connection),
        ("Sample Data", check_sample_data),
        ("System Tests", run_system_tests)
    ]
    
    passed_checks = 0
    total_checks = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n{'='*20} {check_name} {'='*20}")
        try:
            if check_func():
                passed_checks += 1
        except Exception as e:
            print(f"   ❌ {check_name} failed with error: {e}")
    
    # Create convenience script
    print(f"\n{'='*20} Creating Helper Scripts {'='*20}")
    try:
        create_run_script()
    except Exception as e:
        print(f"   ⚠️ Could not create run script: {e}")
    
    # Summary
    print(f"\n📊 SYSTEM CHECK SUMMARY")
    print(f"   ✅ Passed: {passed_checks}/{total_checks} checks")
    print(f"   🎯 Success Rate: {(passed_checks/total_checks)*100:.1f}%")
    
    all_checks_passed = passed_checks == total_checks
    print_next_steps(all_checks_passed)
    
    # Offer to start application
    if all_checks_passed:
        print(f"\n🚀 Would you like to start the application now? (y/n): ", end="")
        try:
            response = input().lower().strip()
            if response in ['y', 'yes']:
                print("\n" + "="*60)
                print("🎬 STARTING ATS CV MATCHER...")
                print("="*60)
                time.sleep(2)
                
                # Import and run main application
                import main
                main.ft.app(target=main.main)
        except KeyboardInterrupt:
            print(f"\n👋 Startup cancelled by user")
        except Exception as e:
            print(f"\n❌ Failed to start application: {e}")
            print(f"💡 Try running: python main.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n👋 Setup interrupted by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print(f"💡 Please check your environment and try again")