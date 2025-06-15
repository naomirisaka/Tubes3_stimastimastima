from typing import List, Dict, Tuple
import re

FUZZY_SIMILARITY_THRESHOLD = 60.0

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

def optimized_similarity_score(s1: str, s2: str) -> float:
    s1_clean = s1.lower().strip()
    s2_clean = s2.lower().strip()
    
    if s1_clean == s2_clean:
        return 100.0
    
    if not s1_clean or not s2_clean:
        return 0.0
    
    base_similarity = similarity_percentage(s1_clean, s2_clean)
    
    # Start character bonus 
    start_bonus = 5.0 if s1_clean[0] == s2_clean[0] else 0.0
    
    # End character bonus
    end_bonus = 3.0 if s1_clean[-1] == s2_clean[-1] else 0.0
    
    # Length difference penalty
    len_diff = abs(len(s1_clean) - len(s2_clean))
    max_len = max(len(s1_clean), len(s2_clean))
    
    if max_len <= 4:
        length_penalty = len_diff * 5.0
    else:
        length_penalty = len_diff * 8.0
    
    # Common substring bonus
    substring_bonus = 0.0
    if len(s1_clean) >= 3 and len(s2_clean) >= 3:
        # Check for common 2-character substrings
        s1_bigrams = {s1_clean[i:i+2] for i in range(len(s1_clean)-1)}
        s2_bigrams = {s2_clean[i:i+2] for i in range(len(s2_clean)-1)}
        common_bigrams = len(s1_bigrams & s2_bigrams)
        total_bigrams = len(s1_bigrams | s2_bigrams)
        
        if total_bigrams > 0:
            substring_bonus = (common_bigrams / total_bigrams) * 10.0
    
    # Calculate final optimized score
    final_score = base_similarity + start_bonus + end_bonus + substring_bonus - length_penalty
    
    return min(100.0, max(0.0, final_score))

def extract_words_from_text(text: str) -> List[str]:
    words = re.findall(r'\b\w+\b', text.lower())
    
    tech_terms = re.findall(r'\b\w+[+#.]?\w*\b', text.lower())
    
    all_words = set(words + tech_terms)
    
    common_short_terms = {'js', 'ai', 'ml', 'ui', 'ux', 'api', 'sql', 'css', 'php', 'go', 'r'}
    filtered_words = []
    
    for word in all_words:
        word_clean = word.strip()
        if len(word_clean) >= 3 or word_clean in common_short_terms:
            filtered_words.append(word_clean)
    
    return filtered_words

def find_similar_words(keyword: str, text: str, threshold: float = None) -> List[Tuple[str, float]]:
    if threshold is None:
        threshold = FUZZY_SIMILARITY_THRESHOLD
    
    words = extract_words_from_text(text)
    similar_words = []
    
    keyword_clean = keyword.lower().strip()
    
    if len(keyword_clean) < 2:
        return []
    
    for word in words:
        word_clean = word.lower().strip()
        len_diff = abs(len(keyword_clean) - len(word_clean))
        max_len = max(len(keyword_clean), len(word_clean))
        
        max_allowed_diff = max(2, max_len * 0.5)

        if len_diff > max_allowed_diff:
            continue
        
        similarity = optimized_similarity_score(keyword_clean, word_clean)
        
        if similarity >= threshold:
            similar_words.append((word, similarity))
    
    similar_words.sort(key=lambda x: x[1], reverse=True)
    return similar_words[:15]

def fuzzy_search_keywords(text: str, keywords: List[str], threshold: float = None) -> Dict[str, List[Tuple[str, float]]]:
    if threshold is None:
        threshold = FUZZY_SIMILARITY_THRESHOLD
    
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

def fuzzy_match_in_file(filepath: str, keyword_string: str, threshold: float = None) -> Dict[str, List[Tuple[str, float]]]:
    if threshold is None:
        threshold = FUZZY_SIMILARITY_THRESHOLD
    
    text = read_file(filepath)
    keywords = parse_keywords(keyword_string)
    
    return fuzzy_search_keywords(text, keywords, threshold)

def set_fuzzy_threshold(new_threshold: float):
    global FUZZY_SIMILARITY_THRESHOLD
    if 0 <= new_threshold <= 100:
        FUZZY_SIMILARITY_THRESHOLD = new_threshold
        print(f"Fuzzy threshold set to {new_threshold}%")
    else:
        print(f"Invalid threshold: {new_threshold}. Must be between 0-100")

def get_fuzzy_threshold() -> float:
    return FUZZY_SIMILARITY_THRESHOLD