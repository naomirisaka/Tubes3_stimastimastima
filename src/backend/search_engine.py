import time
from typing import List, Dict, Tuple
from enum import Enum
from dataclasses import dataclass

import kmp
import boyer_moore
import levenshtein
import aho_corasick
from database import DatabaseManager, get_database_connection
from data_extractor.extractor import extract_realtime, get_cv_summary_with_extraction

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
        print(f"🔄 Extracting CV {detail_id}: {cv_path}")
        
        extraction_result = extract_realtime(cv_path)
        
        if extraction_result and extraction_result.success:
            cv_info['extracted_text'] = extraction_result.cv_raw_text.lower()
            print(f"✅ Successfully extracted {len(cv_info['extracted_text'])} characters")
        else:
            cv_info['extracted_text'] = ""
            error_msg = extraction_result.error_message if extraction_result else "No extraction result"
            print(f"❌ Failed to extract CV {detail_id}: {error_msg}")
        
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
        
        print(f"🔍 Starting search for keywords: {keywords}")
        print(f"📊 Algorithm: {algorithm.value}, Threshold: {fuzzy_threshold}%, Top N: {top_n}")
        
        if not keywords:
            print("❌ No keywords provided!")
            return result

        # 1. Perform exact search with real-time extraction
        print(f"🎯 Step 1: Exact matching using {algorithm.value}")
        start_time = time.time()
        exact_matches = self._perform_exact_search_realtime(keywords, algorithm)
        result.exact_match_time = (time.time() - start_time) * 1000
        
        # Calculate overall exact match counts
        result.exact_matches = {kw: sum(matches.get(kw, 0) for matches in exact_matches.values()) 
                            for kw in keywords}
        
        print(f"✅ Exact search completed in {result.exact_match_time:.1f}ms")
        print(f"📊 Exact matches found: {result.exact_matches}")
        
        # 2. Fuzzy search for keywords without exact matches - FIXED LOGIC
        keywords_without_matches = [kw for kw, count in result.exact_matches.items() if count == 0]
        fuzzy_matches = {}
        
        if keywords_without_matches:
            print(f"🔍 Step 2: Fuzzy search for {len(keywords_without_matches)} keywords without exact matches")
            print(f"Keywords needing fuzzy search: {keywords_without_matches}")
            start_time = time.time()
            
            fuzzy_matches = self._perform_fuzzy_search_realtime(keywords_without_matches, fuzzy_threshold)
            
            result.fuzzy_match_time = (time.time() - start_time) * 1000
            print(f"✅ Fuzzy search completed in {result.fuzzy_match_time:.1f}ms")
            
            # FIXED: Better aggregation of fuzzy matches for reporting
            for keyword in keywords_without_matches:
                all_similar_words = {}  # word -> best_similarity
                
                for detail_id, cv_matches in fuzzy_matches.items():
                    if keyword in cv_matches:
                        for word, similarity in cv_matches[keyword]:
                            if word not in all_similar_words or similarity > all_similar_words[word]:
                                all_similar_words[word] = similarity
                
                if all_similar_words:
                    # Convert to list of tuples and sort by similarity
                    similarity_list = [(word, sim) for word, sim in all_similar_words.items()]
                    similarity_list.sort(key=lambda x: x[1], reverse=True)
                    result.fuzzy_matches[keyword] = similarity_list[:10]  # Top 10
                    print(f"🔍 Fuzzy matches for '{keyword}': {len(similarity_list)} similar words found")
                else:
                    result.fuzzy_matches[keyword] = []
                    print(f"❌ No fuzzy matches found for '{keyword}'")
        else:
            print("✅ All keywords found exact matches, skipping fuzzy search")
        
        # 3. Rank CVs - IMPROVED SCORING
        print(f"🏆 Step 3: Ranking CVs")
        result.cv_matches = self._rank_cvs_realtime(exact_matches, fuzzy_matches, keywords, top_n)
        
        print(f"✅ Search completed! Found {len(result.cv_matches)} matching CVs")
        return result

    def _perform_exact_search_realtime(self, keywords: List[str], algorithm: SearchAlgorithm) -> Dict[int, Dict[str, int]]:
        """Perform exact search with real-time extraction"""
        cv_matches = {}
        processed_cvs = 0
        
        print(f"🔄 Processing {len(self.cv_cache)} CVs for exact matching...")
        
        for detail_id in self.cv_cache.keys():
            # Extract CV text in real-time
            cv_text = self._extract_cv_text_realtime(detail_id)
            processed_cvs += 1
            
            if not cv_text:
                print(f"⚠️ CV {detail_id}: No text extracted, skipping")
                continue
            
            keyword_counts = {}
            total_matches = 0
            
            if algorithm == SearchAlgorithm.KMP:
                for keyword in keywords:
                    matches = kmp.kmp_search(cv_text, keyword.lower())
                    count = len(matches)
                    keyword_counts[keyword] = count
                    total_matches += count
            
            elif algorithm == SearchAlgorithm.BOYER_MOORE:
                for keyword in keywords:
                    matches = boyer_moore.boyer_moore_search(cv_text, keyword.lower())
                    count = len(matches)
                    keyword_counts[keyword] = count
                    total_matches += count
            
            elif algorithm == SearchAlgorithm.AHO_CORASICK:
                matches = aho_corasick.aho_corasick_search(cv_text, [kw.lower() for kw in keywords])
                for keyword in keywords:
                    count = len(matches.get(keyword.lower(), []))
                    keyword_counts[keyword] = count
                    total_matches += count
            
            # Only include if there are matches
            if total_matches > 0:
                cv_matches[detail_id] = keyword_counts
                print(f"✅ CV {detail_id}: {total_matches} total matches found")
            
            # Progress update
            if processed_cvs % 10 == 0:
                print(f"📊 Processed {processed_cvs}/{len(self.cv_cache)} CVs...")
        
        print(f"🎯 Exact search completed: {len(cv_matches)} CVs with matches out of {processed_cvs} processed")
        return cv_matches
    
    def _perform_fuzzy_search_realtime(self, keywords: List[str], threshold: float) -> Dict[int, Dict[str, List[Tuple[str, float]]]]:
        """Perform fuzzy search with real-time extraction - IMPROVED"""
        cv_fuzzy_matches = {}
        processed_cvs = 0
        total_fuzzy_matches = 0
        
        print(f"🔄 Processing {len(self.cv_cache)} CVs for fuzzy matching (threshold: {threshold}%)...")
        
        for detail_id in self.cv_cache.keys():
            # Extract CV text in real-time (should be cached from exact search)
            cv_text = self._extract_cv_text_realtime(detail_id)
            processed_cvs += 1
            
            if not cv_text:
                continue
            
            fuzzy_results = {}
            cv_total_fuzzy = 0
            
            for keyword in keywords:
                print(f"🔍 Searching for fuzzy matches of '{keyword}' in CV {detail_id}")
                
                # Use improved fuzzy matching
                similar_words = levenshtein.find_similar_words(keyword, cv_text, threshold)
                
                if similar_words:
                    fuzzy_results[keyword] = similar_words[:5]  # Top 5 similar words per CV
                    cv_total_fuzzy += len(similar_words)
                    total_fuzzy_matches += len(similar_words)
                    print(f"✅ Found {len(similar_words)} similar words for '{keyword}' in CV {detail_id}")
                    
                    # Debug: show top similar words
                    for word, similarity in similar_words[:3]:
                        print(f"   - '{word}' (similarity: {similarity:.1f}%)")
            
            if fuzzy_results:
                cv_fuzzy_matches[detail_id] = fuzzy_results
                print(f"✅ CV {detail_id}: {cv_total_fuzzy} total fuzzy matches")
            
            # Progress update
            if processed_cvs % 10 == 0:
                print(f"📊 Fuzzy processed {processed_cvs}/{len(self.cv_cache)} CVs...")
        
        print(f"🔍 Fuzzy search completed: {len(cv_fuzzy_matches)} CVs with fuzzy matches")
        print(f"📊 Total fuzzy matches found: {total_fuzzy_matches}")
        return cv_fuzzy_matches
    
    def _parse_keywords(self, keywords_str: str) -> List[str]:
        if not keywords_str:
            return []
        keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
        # Don't convert to lowercase here - preserve original case for display
        return keywords
    
    def _rank_cvs_realtime(self, exact_matches: Dict[int, Dict[str, int]], 
                         fuzzy_matches: Dict[int, Dict[str, List[Tuple[str, float]]]], 
                         original_keywords: List[str],
                         top_n: int) -> List[CVMatch]:
        """Rank CVs using cached data - IMPROVED SCORING"""
        cv_scores = {}
        
        print(f"🏆 Ranking CVs: {len(exact_matches)} with exact matches, {len(fuzzy_matches)} with fuzzy matches")
        
        # Process exact matches
        for detail_id, keyword_counts in exact_matches.items():
            total_exact = sum(keyword_counts.values())
            if total_exact > 0:
                cv_scores[detail_id] = {
                    'exact_score': total_exact,
                    'fuzzy_score': 0,
                    'keyword_breakdown': keyword_counts.copy(),
                    'match_sources': ['Exact Match']
                }
                print(f"📊 CV {detail_id}: {total_exact} exact matches")
        
        # Process fuzzy matches - IMPROVED SCORING
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
                # IMPROVED: Weight fuzzy matches by similarity score
                word_score = 0
                for word, similarity in similar_words:
                    # Weight by similarity percentage (0.6-1.0 range for 60-100% similarity)
                    weight = similarity / 100.0
                    word_score += weight
                
                fuzzy_score += word_score
                
                # Store as both original keyword and fuzzy indicator
                cv_scores[detail_id]['keyword_breakdown'][keyword] = len(similar_words)
                fuzzy_key = f"{keyword} (fuzzy)"
                cv_scores[detail_id]['keyword_breakdown'][fuzzy_key] = round(word_score, 2)
            
            cv_scores[detail_id]['fuzzy_score'] = fuzzy_score
            if 'Fuzzy Match' not in cv_scores[detail_id]['match_sources']:
                cv_scores[detail_id]['match_sources'].append('Fuzzy Match')
            
            print(f"📊 CV {detail_id}: {fuzzy_score:.2f} fuzzy score")
        
        # Build final ranking
        ranked_cvs = []
        
        for detail_id, scores in cv_scores.items():
            # IMPROVED: Better total score calculation
            total_score = scores['exact_score'] + (scores['fuzzy_score'] * 0.7)  # Fuzzy matches worth 70% of exact
            
            if total_score > 0 and detail_id in self.cv_cache:
                cv_info = self.cv_cache[detail_id]
                
                # Calculate similarity score as percentage
                max_possible_score = len(original_keywords) * 2  # Assume 2 matches per keyword max
                similarity_percentage = min(100.0, (total_score / max_possible_score) * 100)
                
                cv_match = CVMatch(
                    detail_id=detail_id,
                    applicant_name=cv_info['applicant_name'],
                    application_role=cv_info['application_role'],
                    total_matches=int(scores['exact_score'] + scores['fuzzy_score']),  # Show combined count
                    keyword_matches=scores['keyword_breakdown'],
                    similarity_score=similarity_percentage,
                    is_encrypted=False,  # Will be determined from database if needed
                    match_sources=scores['match_sources']
                )
                
                ranked_cvs.append(cv_match)
                print(f"🏆 Ranked CV {detail_id}: {cv_match.applicant_name} - Score: {total_score:.2f}")
        
        # Sort by total score (descending) then by similarity score
        ranked_cvs.sort(key=lambda x: (x.total_matches, x.similarity_score), reverse=True)
        
        final_results = ranked_cvs[:top_n]
        print(f"✅ Final ranking: Top {len(final_results)} CVs selected")
        
        return final_results
    
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

    def debug_search(self, keywords_str: str, algorithm: SearchAlgorithm = SearchAlgorithm.KMP, 
                    fuzzy_threshold: float = 60.0) -> Dict:
        """Debug version of search with detailed logging"""
        print("🐛 DEBUG MODE: Detailed Search Analysis")
        print("=" * 50)
        
        self.load_cv_cache()
        keywords = self._parse_keywords(keywords_str)
        
        print(f"🔍 Debug search for: {keywords}")
        print(f"📊 Total CVs in cache: {len(self.cv_cache)}")
        
        # Test extraction on first CV
        if self.cv_cache:
            first_cv_id = list(self.cv_cache.keys())[0]
            print(f"\n📄 Testing extraction on CV {first_cv_id}")
            
            cv_text = self._extract_cv_text_realtime(first_cv_id)
            print(f"   Extracted text length: {len(cv_text)} characters")
            print(f"   Text preview: {cv_text[:200]}...")
            
            # Test fuzzy matching on sample
            if cv_text and keywords:
                print(f"\n🔍 Testing fuzzy matching on sample CV:")
                for keyword in keywords:
                    similar_words = levenshtein.find_similar_words(keyword, cv_text, fuzzy_threshold)
                    print(f"   '{keyword}': {len(similar_words)} similar words found")
                    for word, similarity in similar_words[:3]:
                        print(f"     - '{word}' ({similarity:.1f}%)")
        
        # Run full search
        print(f"\n🚀 Running full search...")
        result = self.search_cvs(keywords_str, algorithm, fuzzy_threshold, 5)
        
        print(f"\n📊 Debug Results:")
        print(f"   Keywords searched: {result.keywords_searched}")
        print(f"   Algorithm used: {result.algorithm_used}")
        print(f"   Exact match time: {result.exact_match_time:.1f}ms")
        print(f"   Fuzzy match time: {result.fuzzy_match_time:.1f}ms")
        print(f"   CVs scanned: {result.total_cvs_scanned}")
        print(f"   Exact matches: {result.exact_matches}")
        print(f"   Fuzzy matches: {len(result.fuzzy_matches)} keywords had fuzzy results")
        print(f"   CV results: {len(result.cv_matches)} CVs returned")
        
        return {
            "result": result,
            "debug_info": {
                "cache_size": len(self.cv_cache),
                "extraction_test": cv_text[:100] if 'cv_text' in locals() else "No test performed"
            }
        }

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

# Add these debugging methods to your search_engine.py or integrated_ats_backend.py

def debug_fuzzy_search_flow(self, keywords: str, algorithm: str = "kmp", top_n: int = 10):
    """Debug the fuzzy search flow to see where results are lost"""
    print("🐛 DEBUG: Starting fuzzy search flow analysis")
    print("=" * 60)
    
    # Parse keywords
    keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
    print(f"📝 Parsed keywords: {keyword_list}")
    
    # Check cache
    print(f"📊 CVs in cache: {len(self.cache_manager.memory_cache)}")
    
    # Step 1: Exact matching
    exact_matches = {keyword: 0 for keyword in keyword_list}
    cv_exact_results = {}
    
    for detail_id, cache_entry in self.cache_manager.memory_cache.items():
        cv_text = getattr(cache_entry, 'raw_text', '')
        if not cv_text:
            continue
            
        cv_text_lower = cv_text.lower()
        for keyword in keyword_list:
            keyword_lower = keyword.lower()
            
            # Simple exact search
            if algorithm == "kmp":
                from kmp import kmp_search
                matches = kmp_search(cv_text_lower, keyword_lower)
            elif algorithm == "boyer_moore":
                from boyer_moore import boyer_moore_search
                matches = boyer_moore_search(cv_text_lower, keyword_lower)
            else:
                # Simple find
                matches = []
                start = 0
                while True:
                    pos = cv_text_lower.find(keyword_lower, start)
                    if pos == -1:
                        break
                    matches.append(pos)
                    start = pos + 1
            
            if matches:
                exact_matches[keyword] += len(matches)
                if detail_id not in cv_exact_results:
                    cv_exact_results[detail_id] = {}
                cv_exact_results[detail_id][keyword] = len(matches)
    
    print(f"🎯 Exact matches found: {exact_matches}")
    print(f"📄 CVs with exact matches: {len(cv_exact_results)}")
    
    # Step 2: Identify keywords needing fuzzy search
    missing_keywords = [kw for kw in keyword_list if exact_matches.get(kw, 0) == 0]
    print(f"🔍 Keywords needing fuzzy search: {missing_keywords}")
    
    if not missing_keywords:
        print("✅ All keywords found exactly - no fuzzy search needed")
        return cv_exact_results
    
    # Step 3: Fuzzy search
    print(f"🔄 Starting fuzzy search for {len(missing_keywords)} keywords...")
    
    fuzzy_matches = {}
    cv_fuzzy_results = {}
    
    for detail_id, cache_entry in self.cache_manager.memory_cache.items():
        cv_text = getattr(cache_entry, 'raw_text', '')
        if not cv_text:
            print(f"⚠️ CV {detail_id} has no raw_text")
            continue
        
        print(f"🔍 Checking CV {detail_id} ({cache_entry.applicant_name})")
        print(f"   Text length: {len(cv_text)} characters")
        
        for keyword in missing_keywords:
            print(f"   🔍 Fuzzy searching for '{keyword}'...")
            
            # Calculate adaptive threshold
            threshold = 60.0  # Base threshold
            keyword_len = len(keyword.strip())
            if keyword_len <= 3:
                adaptive_threshold = min(threshold + 20, 85.0)
            elif keyword_len <= 5:
                adaptive_threshold = threshold + 10
            elif keyword_len <= 8:
                adaptive_threshold = threshold
            else:
                adaptive_threshold = max(threshold - 10, 50.0)
            
            print(f"     Using threshold: {adaptive_threshold}%")
            
            # Perform fuzzy search
            from levenshtein import find_similar_words
            similar_words = find_similar_words(keyword, cv_text, adaptive_threshold)
            
            if similar_words:
                print(f"     ✅ Found {len(similar_words)} similar words:")
                for word, similarity in similar_words[:3]:
                    print(f"       - '{word}' ({similarity:.1f}%)")
                
                # Store fuzzy results
                if keyword not in fuzzy_matches:
                    fuzzy_matches[keyword] = []
                fuzzy_matches[keyword].extend(similar_words[:3])
                
                # Store CV-level results
                if detail_id not in cv_fuzzy_results:
                    cv_fuzzy_results[detail_id] = {}
                cv_fuzzy_results[detail_id][keyword] = len(similar_words)
            else:
                print(f"     ❌ No fuzzy matches found")
    
    print(f"\n📊 FUZZY SEARCH SUMMARY:")
    print(f"   Keywords with fuzzy matches: {len(fuzzy_matches)}")
    print(f"   CVs with fuzzy matches: {len(cv_fuzzy_results)}")
    
    for keyword, matches in fuzzy_matches.items():
        unique_matches = list(set([word for word, _ in matches]))
        print(f"   '{keyword}': {len(unique_matches)} unique matches")
    
    # Step 4: Combine results
    print(f"\n🔗 COMBINING RESULTS:")
    all_cv_results = {}
    
    # Add exact match CVs
    for detail_id, keyword_matches in cv_exact_results.items():
        all_cv_results[detail_id] = {
            'detail_id': detail_id,
            'applicant_name': self.cache_manager.memory_cache[detail_id].applicant_name,
            'application_role': self.cache_manager.memory_cache[detail_id].application_role,
            'total_matches': sum(keyword_matches.values()),
            'keyword_matches': keyword_matches,
            'match_type': 'exact'
        }
    
    # Add fuzzy match CVs
    for detail_id, keyword_matches in cv_fuzzy_results.items():
        if detail_id in all_cv_results:
            # Merge with existing
            all_cv_results[detail_id]['total_matches'] += sum(keyword_matches.values())
            all_cv_results[detail_id]['keyword_matches'].update(keyword_matches)
            all_cv_results[detail_id]['match_type'] = 'mixed'
        else:
            # New fuzzy-only result
            all_cv_results[detail_id] = {
                'detail_id': detail_id,
                'applicant_name': self.cache_manager.memory_cache[detail_id].applicant_name,
                'application_role': self.cache_manager.memory_cache[detail_id].application_role,
                'total_matches': sum(keyword_matches.values()),
                'keyword_matches': keyword_matches,
                'match_type': 'fuzzy'
            }
    
    print(f"   Total CVs with results: {len(all_cv_results)}")
    
    # Sort by total matches
    sorted_results = sorted(all_cv_results.values(), key=lambda x: x['total_matches'], reverse=True)
    
    print(f"\n🏆 TOP RESULTS:")
    for i, result in enumerate(sorted_results[:5], 1):
        print(f"   {i}. {result['applicant_name']} - {result['total_matches']} matches ({result['match_type']})")
        print(f"      Keywords: {result['keyword_matches']}")
    
    return sorted_results[:top_n]


# Quick fix for your search_engine.py - add this method
def _rank_cvs_with_fuzzy_fix(self, exact_matches: Dict[int, Dict[str, int]], 
                            fuzzy_matches: Dict[int, Dict[str, List[Tuple[str, float]]]], 
                            original_keywords: List[str],
                            top_n: int) -> List:
    """Fixed ranking that includes fuzzy-only results"""
    cv_scores = {}
    
    print(f"🏆 Ranking CVs: {len(exact_matches)} with exact, {len(fuzzy_matches)} with fuzzy")
    
    # Process exact matches
    for detail_id, keyword_counts in exact_matches.items():
        total_exact = sum(keyword_counts.values())
        if total_exact > 0:
            cv_scores[detail_id] = {
                'exact_score': total_exact,
                'fuzzy_score': 0,
                'keyword_breakdown': keyword_counts.copy(),
                'match_sources': ['Exact Match']
            }
    
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
            if similar_words:  # Make sure we have actual matches
                # Count number of fuzzy matches for this keyword
                fuzzy_count = len(similar_words)
                fuzzy_score += fuzzy_count
                
                # Add to keyword breakdown
                cv_scores[detail_id]['keyword_breakdown'][keyword] = fuzzy_count
        
        cv_scores[detail_id]['fuzzy_score'] = fuzzy_score
        if 'Fuzzy Match' not in cv_scores[detail_id]['match_sources']:
            cv_scores[detail_id]['match_sources'].append('Fuzzy Match')
    
    # Build final ranking - ENSURE FUZZY-ONLY RESULTS ARE INCLUDED
    ranked_cvs = []
    
    for detail_id, scores in cv_scores.items():
        total_score = scores['exact_score'] + scores['fuzzy_score']
        
        # CRITICAL: Include results even if only fuzzy matches
        if total_score > 0 and detail_id in self.cache_manager.memory_cache:
            cache_entry = self.cache_manager.memory_cache[detail_id]
            
            ranked_cvs.append({
                'detail_id': detail_id,
                'applicant_name': cache_entry.applicant_name,
                'application_role': cache_entry.application_role,
                'total_matches': int(total_score),
                'keyword_matches': scores['keyword_breakdown'],
                'similarity_score': min(100.0, (total_score / len(original_keywords)) * 25),
                'match_sources': scores['match_sources']
            })
    
    # Sort by total score
    ranked_cvs.sort(key=lambda x: x['total_matches'], reverse=True)
    
    print(f"✅ Final ranking: {len(ranked_cvs)} CVs with matches")
    for i, cv in enumerate(ranked_cvs[:3], 1):
        print(f"   {i}. {cv['applicant_name']}: {cv['total_matches']} matches")
    
    return ranked_cvs[:top_n]

if __name__ == "__main__":
    debug_search_issue()