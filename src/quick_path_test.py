#!/usr/bin/env python3
"""
Quick test untuk path resolution tanpa cache manager
"""

import os

def test_path_resolution():
    """Test path resolution logic"""
    print("🧪 QUICK PATH RESOLUTION TEST")
    print("=" * 40)
    
    # Sample database paths
    test_paths = [
        "data/INFORMATION-TECHNOLOGY/15118506.pdf",
        "data/FINANCE/12858898.pdf", 
        "data/CHEF/11121498.pdf",
        "data/ENGINEERING/10030015.pdf"
    ]
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"📁 Current directory: {current_dir}")
    
    for db_path in test_paths:
        print(f"\n🔍 Testing: {db_path}")
        
        # Strategy 1: Remove 'data/' prefix and use ../data/
        if db_path.startswith('data/'):
            relative_path = db_path[5:]  # Remove 'data/'
            
            # Try different base paths
            candidates = [
                os.path.join(current_dir, '..', 'data', relative_path),
                os.path.join(current_dir, 'data', relative_path),
                os.path.join('..', 'data', relative_path),
                os.path.join('data', relative_path)
            ]
            
            for candidate in candidates:
                exists = os.path.exists(candidate)
                status = "✅" if exists else "❌"
                print(f"  {status} {candidate}")
                
                if exists:
                    print(f"  🎯 FOUND: {os.path.abspath(candidate)}")
                    break
            else:
                print(f"  ❌ NOT FOUND in any location")

def test_simple_file_access():
    """Test simple file access"""
    print(f"\n📂 SIMPLE FILE ACCESS TEST")
    print("=" * 30)
    
    # Test if we can access files directly
    test_paths = [
        "../data/INFORMATION-TECHNOLOGY/15118506.pdf",
        "../data/ENGINEERING/10030015.pdf"
    ]
    
    for path in test_paths:
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        print(f"{status} {path}")
        
        if exists:
            try:
                size = os.path.getsize(path)
                print(f"    📊 Size: {size:,} bytes")
            except Exception as e:
                print(f"    ❌ Error getting size: {e}")

def find_actual_files():
    """Find actual file locations"""
    print(f"\n🔎 FINDING ACTUAL FILES")
    print("=" * 25)
    
    # Search for files in data directory
    data_dirs = ["../data", "data", "../../data"]
    
    target_files = ["15118506.pdf", "10030015.pdf"]
    
    for data_dir in data_dirs:
        if os.path.exists(data_dir):
            print(f"📁 Searching in: {data_dir}")
            
            for target in target_files:
                for root, dirs, files in os.walk(data_dir):
                    if target in files:
                        full_path = os.path.join(root, target)
                        print(f"  ✅ Found: {target} → {full_path}")
                        break

if __name__ == "__main__":
    test_path_resolution()
    test_simple_file_access()
    find_actual_files()
    
    print(f"\n📝 SUMMARY:")
    print(f"If files are found ✅, the path resolution strategy is correct.")
    print(f"Use the working path pattern in cv_cache_manager.py")