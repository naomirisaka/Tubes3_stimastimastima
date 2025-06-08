import time
from typing import List, Dict, Tuple
from enum import Enum
from dataclasses import dataclass

import kmp
import boyer_moore
import levenshtein
import aho_corasick
from database import DatabaseManager, get_database_connection

class SearchAlgorithm(Enum):
    KMP = "kmp"
    BOYER_MOORE = "boyer_moore"
    AHO_CORASICK = "aho_corasick"

@dataclass
class CVMatch:
    detail_id: int
    applicant_name: str
    application_role: str
    total_matches: int
    keyword_matches: Dict[str, int]
    similarity_score: float = 0.0

@dataclass
class SearchResult:
    exact_matches: Dict[str, int] = None
    fuzzy_matches: Dict[str, List[Tuple[str, float]]] = None
    exact_match_time: float = 0.0
    fuzzy_match_time: float = 0.0
    total_cvs_scanned: int = 0
    keywords_searched: List[str] = None
    algorithm_used: str = ""
    cv_matches: List[CVMatch] = None
    
    def __post_init__(self):
        if self.exact_matches is None:
            self.exact_matches = {}
        if self.fuzzy_matches is None:
            self.fuzzy_matches = {}
        if self.keywords_searched is None:
            self.keywords_searched = []
        if self.cv_matches is None:
            self.cv_matches = []

class DatabaseCVSearchEngine:
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or get_database_connection()
        self.cv_cache = {}  # Cache CV data for performance
        self.cache_loaded = False
    
    def load_cv_cache(self, force_reload: bool = False):
        if self.cache_loaded and not force_reload:
            return
        
        if not self.db_manager.connect():
            raise Exception("Failed to connect to database")
        
        print("Loading CV data from database...")
        cv_data = self.db_manager.get_cv_texts_for_search()
        
        self.cv_cache = {}
        for detail_id, cv_text in cv_data:
            self.cv_cache[detail_id] = cv_text
        
        self.cache_loaded = True
        self.db_manager.disconnect()
        print(f"Loaded {len(self.cv_cache)} CVs into cache")
    
    def search_cvs(self, keywords_str: str, algorithm: SearchAlgorithm = SearchAlgorithm.KMP, 
                   fuzzy_threshold: float = 70.0, top_n: int = 10) -> SearchResult:
        self.load_cv_cache()
        
        result = SearchResult()
        keywords = self._parse_keywords(keywords_str)
        result.keywords_searched = keywords
        result.algorithm_used = algorithm.value
        result.total_cvs_scanned = len(self.cv_cache)
        
        if not keywords:
            return result
        
        # Perform exact matching
        start_time = time.time()
        cv_exact_matches = self._perform_exact_search_on_cvs(keywords, algorithm)
        result.exact_match_time = (time.time() - start_time) * 1000
        
        # Calculate total exact matches
        result.exact_matches = {kw: sum(matches.get(kw, 0) for matches in cv_exact_matches.values()) 
                               for kw in keywords}
        
        # Perform fuzzy matching for keywords with no exact matches
        keywords_without_matches = [kw for kw, count in result.exact_matches.items() if count == 0]
        
        if keywords_without_matches:
            start_time = time.time()
            cv_fuzzy_matches = self._perform_fuzzy_search_on_cvs(keywords_without_matches, fuzzy_threshold)
            result.fuzzy_match_time = (time.time() - start_time) * 1000
            
            # Calculate fuzzy match summary
            for keyword in keywords_without_matches:
                all_fuzzy_words = set()
                for cv_matches in cv_fuzzy_matches.values():
                    if keyword in cv_matches:
                        all_fuzzy_words.update([word for word, _ in cv_matches[keyword]])
                
                if all_fuzzy_words:
                    # Get similarity scores for unique words found
                    similarity_scores = []
                    for word in all_fuzzy_words:
                        similarity = levenshtein.similarity_percentage(keyword, word)
                        similarity_scores.append((word, similarity))
                    
                    # Sort by similarity and take top matches
                    similarity_scores.sort(key=lambda x: x[1], reverse=True)
                    result.fuzzy_matches[keyword] = similarity_scores[:10]
        else:
            cv_fuzzy_matches = {}
        
        # Generate CV rankings
        result.cv_matches = self._rank_cvs(cv_exact_matches, cv_fuzzy_matches, top_n)
        
        return result
    
    def _parse_keywords(self, keywords_str: str) -> List[str]:
        if not keywords_str:
            return []
        return [kw.strip().lower() for kw in keywords_str.split(',') if kw.strip()]
    
    def _perform_exact_search_on_cvs(self, keywords: List[str], algorithm: SearchAlgorithm) -> Dict[int, Dict[str, int]]:
        cv_matches = {}
        
        for detail_id, cv_text in self.cv_cache.items():
            keyword_counts = {}
            
            if algorithm == SearchAlgorithm.KMP:
                for keyword in keywords:
                    matches = kmp.kmp_search(cv_text, keyword)
                    keyword_counts[keyword] = len(matches)
            
            elif algorithm == SearchAlgorithm.BOYER_MOORE:
                for keyword in keywords:
                    matches = boyer_moore.boyer_moore_search(cv_text, keyword)
                    keyword_counts[keyword] = len(matches)
            
            elif algorithm == SearchAlgorithm.AHO_CORASICK:
                matches = aho_corasick.aho_corasick_search(cv_text, keywords)
                for keyword in keywords:
                    keyword_counts[keyword] = len(matches.get(keyword, []))
            
            cv_matches[detail_id] = keyword_counts
        
        return cv_matches
    
    def _perform_fuzzy_search_on_cvs(self, keywords: List[str], threshold: float) -> Dict[int, Dict[str, List[Tuple[str, float]]]]:
        cv_fuzzy_matches = {}
        
        for detail_id, cv_text in self.cv_cache.items():
            fuzzy_results = {}
            
            for keyword in keywords:
                similar_words = levenshtein.find_similar_words(keyword, cv_text, threshold)
                if similar_words:
                    fuzzy_results[keyword] = similar_words[:5]  # Top 5 similar words per CV
            
            if fuzzy_results:
                cv_fuzzy_matches[detail_id] = fuzzy_results
        
        return cv_fuzzy_matches
    
    def _rank_cvs(self, exact_matches: Dict[int, Dict[str, int]], 
                  fuzzy_matches: Dict[int, Dict[str, List[Tuple[str, float]]]], 
                  top_n: int) -> List[CVMatch]:
        cv_scores = {}
        
        # Score exact matches
        for detail_id, keyword_counts in exact_matches.items():
            total_exact = sum(keyword_counts.values())
            if total_exact > 0:
                cv_scores[detail_id] = {
                    'exact_score': total_exact,
                    'fuzzy_score': 0,
                    'keyword_breakdown': keyword_counts.copy()
                }
        
        # Add fuzzy match scores (weighted lower)
        for detail_id, keyword_fuzzy in fuzzy_matches.items():
            if detail_id not in cv_scores:
                cv_scores[detail_id] = {
                    'exact_score': 0,
                    'fuzzy_score': 0,
                    'keyword_breakdown': {}
                }
            
            fuzzy_score = 0
            for keyword, similar_words in keyword_fuzzy.items():
                # Count fuzzy matches but weight them less
                word_count = len(similar_words)
                weighted_score = word_count * 0.5  # Weight fuzzy matches at 50% of exact
                fuzzy_score += weighted_score
                
                # Add to keyword breakdown
                fuzzy_key = f"{keyword} (fuzzy)"
                cv_scores[detail_id]['keyword_breakdown'][fuzzy_key] = word_count
            
            cv_scores[detail_id]['fuzzy_score'] = fuzzy_score
        
        # Calculate final scores and get CV details from database
        ranked_cvs = []
        
        if not self.db_manager.connect():
            return ranked_cvs
        
        try:
            for detail_id, scores in cv_scores.items():
                total_score = scores['exact_score'] + scores['fuzzy_score']
                
                if total_score > 0:
                    # Get applicant and application details
                    app = self.db_manager.get_application_by_id(detail_id)
                    if app:
                        profile = self.db_manager.get_applicant_profile(app.applicant_id)
                        applicant_name = f"{profile.first_name} {profile.last_name}" if profile else "Unknown"
                        
                        cv_match = CVMatch(
                            detail_id=detail_id,
                            applicant_name=applicant_name,
                            application_role=app.application_role,
                            total_matches=int(total_score),
                            keyword_matches=scores['keyword_breakdown'],
                            similarity_score=total_score
                        )
                        ranked_cvs.append(cv_match)
            
            # Sort by total score and return top N
            ranked_cvs.sort(key=lambda x: x.similarity_score, reverse=True)
            return ranked_cvs[:top_n]
        
        finally:
            self.db_manager.disconnect()
    
    def get_cv_summary(self, detail_id: int) -> Dict[str, str]:
        if not self.db_manager.connect():
            return {}
        
        try:
            summary_data = self.db_manager.get_application_summary_data(detail_id)
            return summary_data
        finally:
            self.db_manager.disconnect()
    
    def get_database_stats(self) -> Dict[str, int]:
        if not self.db_manager.connect():
            return {}
        
        try:
            return self.db_manager.get_database_stats()
        finally:
            self.db_manager.disconnect()

# Convenience functions for easy usage
def search_database_cvs(keywords: str, algorithm: str = "kmp", top_n: int = 10, 
                       fuzzy_threshold: float = 70.0) -> Tuple[SearchResult, List[CVMatch]]:
    engine = DatabaseCVSearchEngine()
    
    algo_enum = SearchAlgorithm.KMP
    if algorithm.lower() == "boyer_moore":
        algo_enum = SearchAlgorithm.BOYER_MOORE
    elif algorithm.lower() == "aho_corasick":
        algo_enum = SearchAlgorithm.AHO_CORASICK
    
    search_result = engine.search_cvs(keywords, algo_enum, fuzzy_threshold, top_n)
    
    return search_result, search_result.cv_matches

def get_cv_summary_by_id(detail_id: int) -> Dict[str, str]:
    engine = DatabaseCVSearchEngine()
    return engine.get_cv_summary(detail_id)

def get_cv_path_by_id(detail_id: int) -> str:
    summary = get_cv_summary_by_id(detail_id)
    return summary.get('cv_path', '')

if __name__ == "__main__":
    print("Testing Database CV Search Engine")
    print("=" * 50)
    
    try:
        # Test database connection
        engine = DatabaseCVSearchEngine()
        stats = engine.get_database_stats()
        
        print(f"Database Statistics:")
        print(f"  Total Applicants: {stats.get('total_applicants', 0)}")
        print(f"  Total Applications: {stats.get('total_applications', 0)}")
        print()
        
        # Test search scenarios
        test_searches = [
            "Python, JavaScript, React",
            "Machine Learning, Data Science",
            "Java, Spring Boot",
            "Chef, Cooking, Kitchen"
        ]
        
        for keywords in test_searches:
            print(f"Testing search: '{keywords}'")
            
            result, cv_matches = search_database_cvs(
                keywords, 
                algorithm="kmp", 
                top_n=3,
                fuzzy_threshold=75.0
            )
            
            print(f"  Exact match time: {result.exact_match_time:.2f}ms")
            print(f"  Fuzzy match time: {result.fuzzy_match_time:.2f}ms")
            print(f"  CVs scanned: {result.total_cvs_scanned}")
            
            total_exact = sum(result.exact_matches.values())
            print(f"  Total exact matches: {total_exact}")
            
            if result.fuzzy_matches:
                fuzzy_keywords = len([k for k, v in result.fuzzy_matches.items() if v])
                print(f"  Keywords with fuzzy matches: {fuzzy_keywords}")
            
            if cv_matches:
                print(f"  Top CV: {cv_matches[0].applicant_name} - {cv_matches[0].application_role} (Score: {cv_matches[0].total_matches})")
            else:
                print("  No matching CVs found")
            
            print()
        
        print("Database search engine test completed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()