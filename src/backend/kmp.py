from typing import List, Dict

def compute_lps(pattern: str) -> List[int]:
    lps = [0] * len(pattern)
    length = 0
    i = 1

    while i < len(pattern):
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            i += 1
        else:
            if length != 0:
                length = lps[length - 1]
            else:
                lps[i] = 0
                i += 1

    return lps

def kmp_search(text: str, pattern: str) -> List[int]:
    if not pattern or not text:
        return []

    lps = compute_lps(pattern)
    result = []

    i = j = 0
    while i < len(text):
        if pattern[j] == text[i]:
            i += 1
            j += 1

        if j == len(pattern):
            result.append(i - j)
            j = lps[j - 1]
        elif i < len(text) and pattern[j] != text[i]:
            if j != 0:
                j = lps[j - 1]
            else:
                i += 1

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
        matches = kmp_search(text, kw)
        result[kw] = len(matches)
    return result

if __name__ == "__main__":
    path = "data/schema.sql"
    input_keywords = "React, Next.js, HTML"

    counts = count_keyword_occurrences_in_file(path, input_keywords)
    for keyword, count in counts.items():
        print(f"{keyword}: {count} occurrence(s)")
