from data_extractor.db_utils import get_all_cv_paths, get_applicant_id_by_cv, get_summary_by_applicant
from backend.kmp import count_keyword_occurrences_in_file
# from backend.bm import count_bm_occurrences

def search_top_matches(keywords: str, algorithm: str, top_n: int):
    results = []
    for path in get_all_cv_paths():
        print("🔍 Checking CV path:", path)
        if algorithm == "KMP":
            result = count_keyword_occurrences_in_file(path, keywords)
        # elif algorithm == "BM":
            # result = count_bm_occurrences(path, keywords)
        else:
            continue

        total_match = sum(result.values())
        if total_match > 0:
            results.append({
                "cv_path": path,
                "match": total_match,
                "keywords": result
            })

    results.sort(key=lambda x: x["match"], reverse=True)
    return results[:top_n]

def get_applicant_summary_from_path(cv_path: str):
    applicant_id = get_applicant_id_by_cv(cv_path)
    if applicant_id:
        return get_summary_by_applicant(applicant_id)
    return None
