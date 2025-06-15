from typing import List, Dict

def compute_bad_char_table(pattern: str) -> Dict[str, int]:
    table = {}
    for i in range(len(pattern)):
        table[pattern[i]] = i
    return table

def boyer_moore_search(text: str, pattern: str) -> List[int]:
    if not pattern or not text:
        return []
    
    bad_char = compute_bad_char_table(pattern)
    result = []
    
    shift = 0
    while shift <= len(text) - len(pattern):
        j = len(pattern) - 1

        while j >= 0 and pattern[j] == text[shift + j]:
            j -= 1
        
        if j < 0:
            result.append(shift)
            shift += (len(pattern) - bad_char.get(text[shift + len(pattern)], -1) - 1) if shift + len(pattern) < len(text) else 1
        else:
            shift += max(1, j - bad_char.get(text[shift + j], -1))
    
    return result

def parse_keywords(input_str: str) -> List[str]:
    return [kw.strip() for kw in input_str.split(',') if kw.strip()]

def read_file(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def count_keyword_occurrences_in_file(filepath: str, keyword_string: str) -> Dict[str, int]:
    text = read_file(filepath).lower()
    keywords = parse_keywords(keyword_string.lower())
    
    result = {}
    for kw in keywords:
        matches = boyer_moore_search(text, kw)
        result[kw] = len(matches)
    return result

if __name__ == "__main__":
    path = "data/schema.sql"
    input_keywords = "React, Next.js, HTML"
    
    counts = count_keyword_occurrences_in_file(path, input_keywords)
    for keyword, count in counts.items():
        print(f"{keyword}: {count} occurrence(s)")