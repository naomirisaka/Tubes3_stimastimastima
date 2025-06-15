import time
from typing import List, Dict, Tuple
from enum import Enum
from dataclasses import dataclass

import kmp
import boyer_moore
import levenshtein
import aho_corasick
from database import DatabaseManager, get_database_connection
from extractor import extract_realtime, get_cv_summary_with_extraction

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
    is_encrypted: bool = False
    match_sources: List[str] = None

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
    encryption_enabled: bool = False
    
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
        self.cv_cache = {} 
        self.cache_loaded = False
        self.encryption_enabled = False

    def load_cv_cache(self, force_reload: bool = False):
        """Load CV data with real-time extraction capability"""
        if self.cache_loaded and not force_reload:
            return
        
        if not self.db_manager.connect():
            raise Exception("Failed to connect to database")
        
        print("Loading CV data from database for real-time extraction...")
        
        # Ensure encryption columns exist
        self.db_manager._ensure_encryption_columns()
        
        encryption_status = self.db_manager.get_encryption_status()
        self.encryption_enabled = encryption_status.get('encryption_manager_ready', False)
        
        # Get CV data without extracted text (will be extracted real-time)
        cv_data = self.db_manager.get_cv_data_for_search()
        
        self.cv_cache = {}
        for detail_id, cv_path, applicant_name, application_role in cv_data:
            self.cv_cache[detail_id] = {
                'cv_path': cv_path,
                'applicant_name': applicant_name,
                'application_role': application_role,
                'extracted_text': None  # Will be extracted on-demand
            }
        
        self.cache_loaded = True
        self.db_manager.disconnect()
        print(f"Loaded {len(self.cv_cache)} CVs for real-time extraction (encryption: {'enabled' if self.encryption_enabled else 'disabled'})")

    def _extract_cv_text_realtime(self, detail_id: int) -> str:
        """Extract CV text in real-time"""
        if detail_id not in self.cv_cache:
            return ""
        
        cv_info = self.cv_cache[detail_id]
        
        # Check if already extracted
        if cv_info['extracted_text'] is not None:
            return cv_info['extracted_text']
        
        # Extract in real-time
        cv_path = cv_info['cv_path']
        extraction_result = extract_realtime(cv_path)
        
        if extraction_result.success:
            cv_info['extracted_text'] = extraction_result.cv_raw_text.lower()
        else:
            cv_info['extracted_text'] = ""
            print(f"Failed to extract CV {detail_id}: {extraction_result.error_message}")
        
        return cv_info['extracted_text']

    def search_cvs(self, keywords_str: str, algorithm: SearchAlgorithm = SearchAlgorithm.KMP, 
                fuzzy_threshold: float = 70.0, top_n: int = 10) -> SearchResult:
        self.load_cv_cache()
        
        result = SearchResult()
        keywords = self._parse_keywords(keywords_str)
        result.keywords_searched = keywords
        result.algorithm_used = algorithm.value
        result.total_cvs_scanned = len(self.cv_cache)
        result.encryption_enabled = self.encryption_enabled
        
        if not keywords:
            return result

        # 1. Perform exact search with real-time extraction
        start_time = time.time()
        exact_matches = self._perform_exact_search_realtime(keywords, algorithm)
        result.exact_match_time = (time.time() - start_time) * 1000
        
        # Calculate overall exact match counts
        result.exact_matches = {kw: sum(matches.get(kw, 0) for matches in exact_matches.values()) 
                            for kw in keywords}
        
        # 2. Fuzzy search for keywords without exact matches
        keywords_without_matches = [kw for kw, count in result.exact_matches.items() if count == 0]
        fuzzy_matches = {}
        
        if keywords_without_matches:
            print(f"Performing fuzzy search for {len(keywords_without_matches)} keywords without exact matches")
            start_time = time.time()
            
            fuzzy_matches = self._perform_fuzzy_search_realtime(keywords_without_matches, fuzzy_threshold)
            
            result.fuzzy_match_time = (time.time() - start_time) * 1000
            
            # Set fuzzy matches result
            for keyword in keywords_without_matches:
                all_fuzzy_words = set()
                for cv_matches in fuzzy_matches.values():
                    if keyword in cv_matches:
                        all_fuzzy_words.update([word for word, _ in cv_matches[keyword]])
                
                if all_fuzzy_words:
                    similarity_scores = []
                    for word in all_fuzzy_words:
                        similarity = levenshtein.similarity_percentage(keyword, word)
                        similarity_scores.append((word, similarity))
                    
                    similarity_scores.sort(key=lambda x: x[1], reverse=True)
                    result.fuzzy_matches[keyword] = similarity_scores[:10]
        
        # 3. Rank CVs
        result.cv_matches = self._rank_cvs_realtime(exact_matches, fuzzy_matches, top_n)
        
        return result

    def _perform_exact_search_realtime(self, keywords: List[str], algorithm: SearchAlgorithm) -> Dict[int, Dict[str, int]]:
        """Perform exact search with real-time extraction"""
        cv_matches = {}
        
        for detail_id in self.cv_cache.keys():
            # Extract CV text in real-time
            cv_text = self._extract_cv_text_realtime(detail_id)
            
            if not cv_text:
                continue
            
            keyword_counts = {}
            
            if algorithm == SearchAlgorithm.KMP:
                for keyword in keywords:
                    matches = kmp.kmp_search(cv_text, keyword.lower())
                    keyword_counts[keyword] = len(matches)
            
            elif algorithm == SearchAlgorithm.BOYER_MOORE:
                for keyword in keywords:
                    matches = boyer_moore.boyer_moore_search(cv_text, keyword.lower())
                    keyword_counts[keyword] = len(matches)
            
            elif algorithm == SearchAlgorithm.AHO_CORASICK:
                matches = aho_corasick.aho_corasick_search(cv_text, [kw.lower() for kw in keywords])
                for keyword in keywords:
                    keyword_counts[keyword] = len(matches.get(keyword.lower(), []))
            
            # Only include if there are matches
            if sum(keyword_counts.values()) > 0:
                cv_matches[detail_id] = keyword_counts
        
        return cv_matches
    
    def _perform_fuzzy_search_realtime(self, keywords: List[str], threshold: float) -> Dict[int, Dict[str, List[Tuple[str, float]]]]:
        """Perform fuzzy search with real-time extraction"""
        cv_fuzzy_matches = {}
        
        for detail_id in self.cv_cache.keys():
            # Extract CV text in real-time
            cv_text = self._extract_cv_text_realtime(detail_id)
            
            if not cv_text:
                continue
            
            fuzzy_results = {}
            
            for keyword in keywords:
                similar_words = levenshtein.find_similar_words(keyword, cv_text, threshold)
                if similar_words:
                    fuzzy_results[keyword] = similar_words[:5]  # Top 5 similar words per CV
            
            if fuzzy_results:
                cv_fuzzy_matches[detail_id] = fuzzy_results
        
        return cv_fuzzy_matches
    
    def _parse_keywords(self, keywords_str: str) -> List[str]:
        if not keywords_str:
            return []
        return [kw.strip().lower() for kw in keywords_str.split(',') if kw.strip()]
    
    def _rank_cvs_realtime(self, exact_matches: Dict[int, Dict[str, int]], 
                         fuzzy_matches: Dict[int, Dict[str, List[Tuple[str, float]]]], 
                         top_n: int) -> List[CVMatch]:
        """Rank CVs using cached data"""
        cv_scores = {}
        
        # Process exact matches
        for detail_id, keyword_counts in exact_matches.items():
            total_exact = sum(keyword_counts.values())
            if total_exact > 0:
                cv_scores[detail_id] = {
                    'exact_score': total_exact,
                    'fuzzy_score': 0,
                    'keyword_breakdown': keyword_counts.copy(),
                    'match_sources': ['CV Content']
                }
        
        # Process fuzzy matches
        for detail_id, keyword_fuzzy in fuzzy_matches.items():
            if detail_id not in cv_scores:
                cv_scores[detail_id] = {
                    'exact_score': 0,
                    'fuzzy_score': 0,
                    'keyword_breakdown': {},
                    'match_sources': ['Fuzzy Match']
                }
            
            fuzzy_score = 0
            for keyword, similar_words in keyword_fuzzy.items():
                word_count = len(similar_words)
                weighted_score = word_count * 0.5
                fuzzy_score += weighted_score
                
                fuzzy_key = f"{keyword} (fuzzy)"
                cv_scores[detail_id]['keyword_breakdown'][fuzzy_key] = word_count
            
            cv_scores[detail_id]['fuzzy_score'] = fuzzy_score
            if 'Fuzzy Match' not in cv_scores[detail_id]['match_sources']:
                cv_scores[detail_id]['match_sources'].append('Fuzzy Match')
        
        # Build final ranking
        ranked_cvs = []
        
        for detail_id, scores in cv_scores.items():
            total_score = scores['exact_score'] + scores['fuzzy_score']
            
            if total_score > 0 and detail_id in self.cv_cache:
                cv_info = self.cv_cache[detail_id]
                
                cv_match = CVMatch(
                    detail_id=detail_id,
                    applicant_name=cv_info['applicant_name'],
                    application_role=cv_info['application_role'],
                    total_matches=int(total_score),
                    keyword_matches=scores['keyword_breakdown'],
                    similarity_score=total_score,
                    is_encrypted=False,  # Will be determined from database if needed
                    match_sources=scores['match_sources']
                )
                
                ranked_cvs.append(cv_match)
        
        # Sort by similarity score (descending)
        ranked_cvs.sort(key=lambda x: x.similarity_score, reverse=True)
        return ranked_cvs[:top_n]
    
    def get_cv_summary(self, detail_id: int) -> Dict[str, str]:
        """Get CV summary using real-time extraction"""
        return get_cv_summary_with_extraction(detail_id)
    
    def get_database_stats(self) -> Dict[str, int]:
        if not self.db_manager.connect():
            return {}
        
        try:
            stats = self.db_manager.get_database_stats()
            encryption_status = self.db_manager.get_encryption_status()
            stats['encryption_enabled'] = encryption_status['encryption_enabled']
            stats['encryption_ready'] = encryption_status['encryption_manager_ready']
            return stats
        finally:
            self.db_manager.disconnect()
    
    def test_realtime_extraction(self) -> Dict[str, any]:
        """Test real-time extraction capability"""
        if not self.db_manager.connect():
            return {"error": "Database connection failed"}
        
        try:
            self.load_cv_cache()
            
            total_cvs = len(self.cv_cache)
            successful_extractions = 0
            failed_extractions = 0
            
            # Test extraction on first 5 CVs
            test_cvs = list(self.cv_cache.keys())[:5]
            
            for detail_id in test_cvs:
                cv_text = self._extract_cv_text_realtime(detail_id)
                if cv_text and len(cv_text) > 0:
                    successful_extractions += 1
                else:
                    failed_extractions += 1
            
            return {
                "total_cvs_in_cache": total_cvs,
                "test_sample_size": len(test_cvs),
                "successful_extractions": successful_extractions,
                "failed_extractions": failed_extractions,
                "extraction_success_rate": (successful_extractions / len(test_cvs)) * 100 if test_cvs else 0,
                "realtime_extraction_ready": successful_extractions > 0
            }
            
        except Exception as e:
            return {"error": f"Test failed: {str(e)}"}
        
        finally:
            self.db_manager.disconnect()

def search_database_cvs(keywords: str, algorithm: str = "kmp", top_n: int = 10, 
                       fuzzy_threshold: float = 70.0) -> Tuple[SearchResult, List[CVMatch]]:
    """Search database CVs with real-time extraction."""
    engine = DatabaseCVSearchEngine()
    
    algo_enum = SearchAlgorithm.KMP
    if algorithm.lower() == "boyer_moore":
        algo_enum = SearchAlgorithm.BOYER_MOORE
    elif algorithm.lower() == "aho_corasick":
        algo_enum = SearchAlgorithm.AHO_CORASICK
    
    search_result = engine.search_cvs(keywords, algo_enum, fuzzy_threshold, top_n)
    
    return search_result, search_result.cv_matches

def get_cv_summary_by_id(detail_id: int) -> Dict[str, str]:
    """Get CV summary by ID using real-time extraction"""
    engine = DatabaseCVSearchEngine()
    return engine.get_cv_summary(detail_id)

def get_cv_path_by_id(detail_id: int) -> str:
    """Get CV path by ID"""
    summary = get_cv_summary_by_id(detail_id)
    return summary.get('cv_path', '')