from backend.kmp import kmp_search

text = "this is a test text with test word and testing purpose"
pattern = "test"

positions = kmp_search(text, pattern)
print("Found at:", positions)
# Output: Found at: [10, 25, 40]
