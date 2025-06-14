from data_extractor.extractor import extract_realtime
path = "../data/ENGINEERING/10030015.pdf"
result = extract_realtime(path)
print(result.success)
print(result.cv_raw_text[:500])
