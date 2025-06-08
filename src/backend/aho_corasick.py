from typing import List, Dict, Set, Tuple
from collections import deque, defaultdict

class TrieNode:
    def __init__(self):
        self.children = {}
        self.failure = None
        self.output = []
        self.is_end = False

class AhoCorasick:
    def __init__(self):
        self.root = TrieNode()
        self.patterns = []
    
    def add_pattern(self, pattern: str):
        if pattern not in self.patterns:
            self.patterns.append(pattern)
            self._build_trie(pattern)
    
    def add_patterns(self, patterns: List[str]):
        for pattern in patterns:
            self.add_pattern(pattern)
    
    def _build_trie(self, pattern: str):
        node = self.root
        for char in pattern:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        node.output.append(pattern)
    
    def build_failure_function(self):
        queue = deque()
        
        for child in self.root.children.values():
            child.failure = self.root
            queue.append(child)
        
        while queue:
            current = queue.popleft()
            
            for char, child in current.children.items():
                queue.append(child)
                
                failure = current.failure
                while failure and char not in failure.children:
                    failure = failure.failure
                
                if failure:
                    child.failure = failure.children[char]
                else:
                    child.failure = self.root

                child.output.extend(child.failure.output)
    
    def search(self, text: str) -> Dict[str, List[int]]:
        if not self.patterns:
            return {}

        self.build_failure_function()
        
        result = defaultdict(list)
        node = self.root
        
        for i, char in enumerate(text):
            while node and char not in node.children:
                node = node.failure
            
            if node and char in node.children:
                node = node.children[char]
                
                for pattern in node.output:
                    start_pos = i - len(pattern) + 1
                    result[pattern].append(start_pos)
            else:
                node = self.root
        
        return dict(result)
    
    def get_patterns(self) -> List[str]:
        return self.patterns.copy()

def aho_corasick_search(text: str, patterns: List[str]) -> Dict[str, List[int]]:
    if not patterns:
        return {}
    
    ac = AhoCorasick()
    ac.add_patterns(patterns)
    return ac.search(text)

def parse_keywords(input_str: str) -> List[str]:
    return [kw.strip() for kw in input_str.split(',') if kw.strip()]

def read_file(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def count_keyword_occurrences_in_file(filepath: str, keyword_string: str) -> Dict[str, int]:
    text = read_file(filepath).lower()
    keywords = parse_keywords(keyword_string.lower())
    
    matches = aho_corasick_search(text, keywords)
    
    result = {}
    for keyword in keywords:
        result[keyword] = len(matches.get(keyword, []))
    
    return result

def find_all_matches_in_file(filepath: str, keyword_string: str) -> Dict[str, List[int]]:
    text = read_file(filepath).lower()
    keywords = parse_keywords(keyword_string.lower())
    
    return aho_corasick_search(text, keywords)

if __name__ == "__main__":
    path = "data/schema.sql"
    input_keywords = "React, Next.js, HTML, CSS, JavaScript"
    
    print("=== Aho-Corasick Algorithm Test ===")
    
    counts = count_keyword_occurrences_in_file(path, input_keywords)
    print("\nKeyword counts:")
    for keyword, count in counts.items():
        print(f"  {keyword}: {count} occurrence(s)")
    
    positions = find_all_matches_in_file(path, input_keywords)
    print("\nKeyword positions:")
    for keyword, pos_list in positions.items():
        if pos_list:
            print(f"  {keyword}: found at positions {pos_list[:5]}{'...' if len(pos_list) > 5 else ''}")
        else:
            print(f"  {keyword}: not found")
    
    print("\n=== Direct Test ===")
    test_text = "she sells seashells by the seashore"
    test_patterns = ["she", "shells", "sea"]
    
    direct_results = aho_corasick_search(test_text, test_patterns)
    print(f"Text: '{test_text}'")
    print(f"Patterns: {test_patterns}")
    print("Results:")
    for pattern, positions in direct_results.items():
        print(f"  '{pattern}': {positions}")