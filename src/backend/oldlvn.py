from typing import List, Dict, Tuple
import re

def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def similarity_percentage(s1: str, s2: str) -> float:
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 100.0
    
    distance = levenshtein_distance(s1, s2)
    return ((max_len - distance) / max_len) * 100

def extract_words_from_text(text: str) -> List[str]:
    words = re.findall(r'\b\w+\b', text.lower())
    return words

def find_similar_words(keyword: str, text: str, threshold: float = 70.0) -> List[Tuple[str, float]]:
    words = extract_words_from_text(text)
    similar_words = []
    
    for word in set(words): 
        similarity = similarity_percentage(keyword.lower(), word.lower())
        if similarity >= threshold:
            similar_words.append((word, similarity))
    
    similar_words.sort(key=lambda x: x[1], reverse=True)
    return similar_words

def fuzzy_search_keywords(text: str, keywords: List[str], threshold: float = 70.0) -> Dict[str, List[Tuple[str, float]]]:
    result = {}
    for keyword in keywords:
        similar = find_similar_words(keyword, text, threshold)
        result[keyword] = similar
    return result

def parse_keywords(input_str: str) -> List[str]:
    return [kw.strip() for kw in input_str.split(',') if kw.strip()]

def read_file(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def fuzzy_match_in_file(filepath: str, keyword_string: str, threshold: float = 70.0) -> Dict[str, List[Tuple[str, float]]]:
    text = read_file(filepath)
    keywords = parse_keywords(keyword_string)
    
    return fuzzy_search_keywords(text, keywords, threshold)

if __name__ == "__main__":
    path = "data/schema.sql"
    input_keywords = "React, Python, JavaScript"
    
    results = fuzzy_match_in_file(path, input_keywords, threshold=60.0)
    
    for keyword, matches in results.items():
        print(f"\nKeyword: '{keyword}'")
        if matches:
            for word, similarity in matches[:5]:
                print(f"  - {word}: {similarity:.1f}% similar")
        else:
            print("  No similar words found")
    
    print(f"\nDirect tests:")
    print(f"Distance between 'kitten' and 'sitting': {levenshtein_distance('kitten', 'sitting')}")
    print(f"Similarity between 'python' and 'pyhton': {similarity_percentage('python', 'pyhton'):.1f}%")