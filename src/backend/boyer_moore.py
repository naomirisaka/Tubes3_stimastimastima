from typing import List, Dict

def compute_bad_char_table(pattern: str) -> Dict[str, int]:
    table = {}
    for i in range(len(pattern)):
        table[pattern[i]] = i
    return table

def compute_good_suffix_table(pattern: str) -> List[int]:
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
    suffix_len = len(pattern) - pos
    return pattern.startswith(pattern[pos:pos + suffix_len])

def suffix_length(pattern: str, pos: int) -> int:
    length = 0
    i = pos
    j = len(pattern) - 1
    
    while i >= 0 and pattern[i] == pattern[j]:
        length += 1
        i -= 1
        j -= 1
    
    return length

def simple_search(text: str, pattern: str) -> List[int]:
    result = []
    pattern_len = len(pattern)
    text_len = len(text)
    
    for i in range(text_len - pattern_len + 1):
        if text[i:i + pattern_len] == pattern:
            result.append(i)
    
    return result

def single_char_search(text: str, char: str) -> List[int]:
    return [i for i, c in enumerate(text) if c == char]

def full_boyer_moore_search(text: str, pattern: str) -> List[int]:
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
    if not pattern or not text:
        return []
    
    pattern_len = len(pattern)
    
    if pattern_len == 1:
        return single_char_search(text, pattern)
    elif pattern_len <= 3:
        return simple_search(text, pattern)
    else:
        return full_boyer_moore_search(text, pattern)

def parse_keywords(input_str: str) -> List[str]:
    return [kw.strip() for kw in input_str.split(',') if kw.strip()]

def read_file(filepath: str) -> str:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return ""
    except Exception as e:
        print(f"Error reading file: {e}")
        return ""

def count_keyword_occurrences_in_file(filepath: str, keyword_string: str) -> Dict[str, int]:
    text = read_file(filepath)
    if not text:
        return {}
    
    text_lower = text.lower()
    keywords = parse_keywords(keyword_string.lower())
    
    result = {}
    for kw in keywords:
        if kw:  
            matches = boyer_moore_search(text_lower, kw) 
            result[kw] = len(matches)
    
    return result

if __name__ == "__main__":
    path = "data/schema.sql"
    input_keywords = "React, Next.js, HTML"
    
    counts = count_keyword_occurrences_in_file(path, input_keywords)
    for keyword, count in counts.items():
        print(f"{keyword}: {count} occurrence(s)")