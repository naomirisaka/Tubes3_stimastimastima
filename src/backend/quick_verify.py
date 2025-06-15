# Just to test the algorithms quickly without database integration

def test_kmp_only():
    print("Testing KMP...")
    
    try:
        import kmp
        
        # Simple test
        result = kmp.kmp_search("hello world", "world")
        if result == [6]:
            print("KMP working correctly")
            return True
        else:
            print(f"KMP failed: got {result}, expected [6]")
            return False
            
    except Exception as e:
        print(f"KMP error: {e}")
        return False

def test_boyer_moore_only():
    print("Testing Boyer-Moore...")
    
    try:
        import boyer_moore
        
        # Simple test
        result = boyer_moore.boyer_moore_search("hello world", "world")
        if result == [6]:
            print("Boyer-Moore working correctly")
            return True
        else:
            print(f"Boyer-Moore failed: got {result}, expected [6]")
            return False
            
    except Exception as e:
        print(f"Boyer-Moore error: {e}")
        return False

def test_levenshtein_only():
    print("Testing Levenshtein...")
    
    try:
        import levenshtein
        
        # Simple test
        result = levenshtein.levenshtein_distance("cat", "bat")
        if result == 1:
            print("Levenshtein working correctly")
            return True
        else:
            print(f"Levenshtein failed: got {result}, expected 1")
            return False
            
    except Exception as e:
        print(f"Levenshtein error: {e}")
        return False

def test_aho_corasick_only():
    print("Testing Aho-Corasick...")
    
    try:
        import aho_corasick
        
        # Simple test
        result = aho_corasick.aho_corasick_search("hello world", ["world"])
        if "world" in result and result["world"] == [6]:
            print("Aho-Corasick working correctly")
            return True
        else:
            print(f"Aho-Corasick failed: got {result}")
            return False
            
    except Exception as e:
        print(f"Aho-Corasick error: {e}")
        return False

def main():
    print("QUICK ALGORITHM VERIFICATION")
    print("=" * 35)
    
    tests = [
        test_kmp_only,
        test_boyer_moore_only,
        test_levenshtein_only,
        test_aho_corasick_only
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{len(tests)} algorithms working")
    
    if passed == len(tests):
        print("All algorithms work! Ready for database integration.")
    else:
        print("Some algorithms have issues. Check the errors above.")

if __name__ == "__main__":
    main()