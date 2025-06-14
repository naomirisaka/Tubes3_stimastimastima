# backend/boyer_moore.py

from typing import List, Dict

def compute_bad_char_table(pattern: str) -> Dict[str, int]:
    """Compute bad character table for Boyer-Moore algorithm."""
    table = {}
    for i in range(len(pattern)):
        table[pattern[i]] = i
    return table

def compute_good_suffix_table(pattern: str) -> List[int]:
    """Compute good suffix table for Boyer-Moore algorithm."""
    pattern_len = len(pattern)
    good_suffix = [0] * pattern_len
    last_prefix_index = pattern_len
    
    for i in range(pattern_len - 1, -1, -1):
        if is_prefix(pattern, i + 1):
            last_prefix_index = i + 1
        good_suffix[i] = last_prefix_index + (pattern_len - 1 - i)
    
    for i in range(pattern_len - 1):
        suffix_len = suffix_length(pattern, i)
        if pattern[i - suffix_len] != pattern[pattern_len - 1 - suffix_len]:
            good_suffix[pattern_len - 1 - suffix_len] = pattern_len - 1 - i + suffix_len
    
    return good_suffix

def is_prefix(pattern: str, pos: int) -> bool:
    """Check if suffix starting at pos is a prefix of the pattern."""
    suffix_len = len(pattern) - pos
    return pattern.startswith(pattern[pos:pos + suffix_len])

def suffix_length(pattern: str, pos: int) -> int:
    """Return the length of the longest suffix ending at pos."""
    length = 0
    i = pos
    j = len(pattern) - 1
    
    while i >= 0 and pattern[i] == pattern[j]:
        length += 1
        i -= 1
        j -= 1
    
    return length

def simple_search(text: str, pattern: str) -> List[int]:
    """Simple string search for very short patterns."""
    result = []
    pattern_len = len(pattern)
    text_len = len(text)
    
    for i in range(text_len - pattern_len + 1):
        if text[i:i + pattern_len] == pattern:
            result.append(i)
    
    return result

def single_char_search(text: str, char: str) -> List[int]:
    """Optimized single character search."""
    return [i for i, c in enumerate(text) if c == char]

def full_boyer_moore_search(text: str, pattern: str) -> List[int]:
    """Full Boyer-Moore implementation with both heuristics."""
    if not pattern or not text:
        return []
    
    pattern_len = len(pattern)
    text_len = len(text)
    
    if pattern_len > text_len:
        return []
    
    bad_char = compute_bad_char_table(pattern)
    good_suffix = compute_good_suffix_table(pattern)
    
    result = []
    shift = 0
    
    while shift <= text_len - pattern_len:
        j = pattern_len - 1
        
        while j >= 0 and pattern[j] == text[shift + j]:
            j -= 1
        
        if j < 0:
            result.append(shift)
            shift += good_suffix[0]
        else:
            bad_char_shift = j - bad_char.get(text[shift + j], -1)
            good_suffix_shift = good_suffix[j]
            shift += max(bad_char_shift, good_suffix_shift, 1)
    
    return result

def boyer_moore_search(text: str, pattern: str) -> List[int]:
    """
    MAIN Boyer-Moore function with automatic optimization.
    This is the function that gets called by your existing code.
    
    🎯 This replaces your original boyer_moore_search function!
    """
    if not pattern or not text:
        return []
    
    pattern_len = len(pattern)
    
    # 🚀 OPTIMIZATION: Choose best algorithm based on pattern length
    if pattern_len == 1:
        # Single character - use optimized search
        return single_char_search(text, pattern)
    elif pattern_len <= 3:
        # Short patterns - simple search is faster
        return simple_search(text, pattern)
    else:
        # Longer patterns - use full Boyer-Moore
        return full_boyer_moore_search(text, pattern)

def parse_keywords(input_str: str) -> List[str]:
    """Parse comma-separated keywords."""
    return [kw.strip() for kw in input_str.split(',') if kw.strip()]

def read_file(filepath: str) -> str:
    """Read file content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return ""
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return ""

def count_keyword_occurrences_in_file(filepath: str, keyword_string: str) -> Dict[str, int]:
    """Count keyword occurrences using optimized Boyer-Moore."""
    text = read_file(filepath)
    if not text:
        return {}
    
    text_lower = text.lower()
    keywords = parse_keywords(keyword_string.lower())
    
    result = {}
    for kw in keywords:
        if kw:  # Skip empty keywords
            matches = boyer_moore_search(text_lower, kw)  # 🎯 This now uses optimization!
            result[kw] = len(matches)
    
    return result

def test_performance():
    """Test performance with your problematic 'pro' search."""
    import time
    
    print("🧪 TESTING BOYER-MOORE PERFORMANCE FIX")
    print("=" * 45)
    
    # Create test text similar to your CV content
    test_text = ("professional programming project with many programs and processes. " * 1000).lower()
    
    test_patterns = [
        "pro",           # Your problematic pattern
        "program",       # Medium pattern  
        "professional",  # Long pattern
        "xyz"           # Not found
    ]
    
    print(f"Test text length: {len(test_text):,} characters")
    print()
    
    for pattern in test_patterns:
        print(f"Searching for: '{pattern}' (length: {len(pattern)})")
        
        # Time the search
        start_time = time.time()
        matches = boyer_moore_search(test_text, pattern)  # Uses optimized version now
        search_time = (time.time() - start_time) * 1000
        
        # Determine which algorithm was used
        if len(pattern) == 1:
            algorithm_used = "Single char search"
        elif len(pattern) <= 3:
            algorithm_used = "Simple search"
        else:
            algorithm_used = "Full Boyer-Moore"
        
        print(f"  ⚡ Algorithm used: {algorithm_used}")
        print(f"  ⏱️  Time: {search_time:.3f}ms")
        print(f"  📊 Found: {len(matches)} matches")
        print()

if __name__ == "__main__":
    test_performance()

    print("ORIGINAL TEST:")
    path = "data/schema.sql"
    input_keywords = "React, Next.js, HTML"
    
    counts = count_keyword_occurrences_in_file(path, input_keywords)
    for keyword, count in counts.items():
        print(f"{keyword}: {count} occurrence(s)")