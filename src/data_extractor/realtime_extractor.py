# realtime_extractor.py
"""
Real-time PDF extraction module untuk ATS system
Menggunakan PyMuPDF (fitz) untuk ekstraksi real-time
"""

import os
import time
import re
import fitz  # PyMuPDF
from typing import Dict, Optional, Tuple
from datetime import datetime
import threading
import queue
from dataclasses import dataclass


@dataclass
class ExtractionResult:
    """Result dari ekstraksi PDF"""
    success: bool
    cv_raw_text: str = ""
    summary_section: str = ""
    skills_section: str = ""
    experience_section: str = ""
    education_section: str = ""
    accomplishments_section: str = ""
    error_message: str = ""
    extraction_time_ms: float = 0.0


class RealtimePDFExtractor:
    """Real-time PDF extractor dengan caching dan optimization"""
    
    def __init__(self):
        self.extraction_cache = {}  # Cache untuk hasil ekstraksi
        self.processing_queue = queue.Queue()
        self.is_processing = False
        
    def extract_pdf_text(self, pdf_path: str) -> str:
        """Ekstrak teks mentah dari PDF menggunakan PyMuPDF"""
        if not pdf_path or not os.path.exists(pdf_path):
            return ""
        
        try:
            # Buka PDF dengan PyMuPDF
            doc = fitz.open(pdf_path)
            full_text = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Ekstrak text dengan layout preservation
                blocks = page.get_text("blocks")
                page_lines = []
                
                # Sort blocks by position (top to bottom, left to right)
                blocks.sort(key=lambda block: (block[1], block[0]))
                
                for block in blocks:
                    if len(block) >= 5:  # Text block
                        text = block[4].strip()
                        if text:
                            lines = text.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line:
                                    page_lines.append(line)
                
                # Fallback jika blocks tidak bekerja dengan baik
                if len(page_lines) < 5:
                    simple_text = page.get_text().strip()
                    if simple_text:
                        page_lines = [line.strip() for line in simple_text.split('\n') if line.strip()]
                
                if page_lines:
                    full_text.extend(page_lines)
            
            doc.close()
            
            result = '\n'.join(full_text)
            return self.clean_extracted_text(result)
            
        except Exception as e:
            print(f"Error extracting PDF {pdf_path}: {e}")
            return ""
    
    def clean_extracted_text(self, text: str) -> str:
        """Bersihkan dan normalisasi text hasil ekstraksi"""
        if not text:
            return ""
        
        lines = text.split('\n')
        cleaned_lines = []
        
        prev_line = ""
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Normalisasi spasi
            line = re.sub(r'\s+', ' ', line)
            
            # Gabungkan baris yang terputus
            if (prev_line and 
                len(prev_line) > 0 and 
                not prev_line.endswith(('.', '!', '?', ':', ';')) and
                not line[0].isupper() and 
                len(line.split()) < 4 and
                not any(char.isdigit() for char in line[:3])):
                if cleaned_lines:
                    cleaned_lines[-1] = cleaned_lines[-1] + " " + line
            else:
                cleaned_lines.append(line)
            
            prev_line = line
        
        # Post-processing untuk menggabungkan tanggal dan info yang terpisah
        final_lines = []
        for line in cleaned_lines:
            # Fix tanggal yang terpisah
            line = re.sub(r'(\d{2}/\d{4})\s+to\s+(\d{2}/\d{4})', r'\1 to \2', line)
            line = re.sub(r'(\d{2}/\d{4})\s*-\s*(\d{2}/\d{4})', r'\1 - \2', line)
            
            # Fix company name dan location
            line = re.sub(r'Company Name\s*[,\s]*City\s*[,\s]*State', 'Company Name, City, State', line)
            
            # Fix camelCase yang terpisah
            line = re.sub(r'([a-z])([A-Z])', r'\1 \2', line)
            line = re.sub(r'([0-9])([A-Z])', r'\1 \2', line)
            
            final_lines.append(line)
        
        return '\n'.join(final_lines)
    
    def extract_cv_sections(self, cv_raw_text: str) -> Dict[str, str]:
        """Ekstrak section-section dari CV menggunakan regex patterns"""
        sections = {
            'summary': '',
            'skills': '',
            'experience': '',
            'education': '',
            'accomplishments': ''
        }
        
        if not cv_raw_text:
            return sections
        
        normalized_text = cv_raw_text.replace('\r', '\n')
        lines = normalized_text.split('\n')
        text_lower = normalized_text.lower()
        
        # Daftar section yang diabaikan
        ignored_sections = [
            'others', 'other', 'personal information', 'personal info',
            'additional information', 'additional info', 'miscellaneous',
            'references', 'hobbies', 'interests', 'personal details',
            'contact information', 'contact info', 'contact',
            'objective', 'career objective', 'personal statement', 'highlights'
        ]
        
        section_positions = []
        
        # Deteksi posisi section headers
        for i, line in enumerate(lines):
            line_clean = line.strip().lower()
            if not line_clean or len(line_clean) > 100:
                continue
            
            if any(ignored in line_clean for ignored in ignored_sections):
                continue
            
            # Pattern matching untuk section headers
            if re.match(r'^(summary|profile|overview|about|professional summary|career focus|executive profile)$', line_clean):
                section_positions.append(('summary', i))
            elif re.match(r'^(skills|summary of skills|technical skills|professional skills|key skills|core competencies)$', line_clean):
                section_positions.append(('skills', i))
            elif re.match(r'^(experience|work experience|employment history|professional experience|work history)$', line_clean):
                section_positions.append(('experience', i))
            elif re.match(r'^(education|academic background|qualifications|educational background|education and training)$', line_clean):
                section_positions.append(('education', i))
            elif re.match(r'^(accomplishments|achievements|certifications|certificates|awards|honors|licenses|core accomplishments|certifications and training)$', line_clean):
                section_positions.append(('accomplishments', i))
        
        # Sort berdasarkan posisi
        section_positions.sort(key=lambda x: x[1])
        
        # Ekstrak konten untuk setiap section
        for i, (section_name, start_pos) in enumerate(section_positions):
            # Tentukan posisi akhir
            if i + 1 < len(section_positions):
                end_pos = section_positions[i + 1][1]
            else:
                end_pos = len(lines)
            
            content_lines = []
            for j in range(start_pos + 1, end_pos):
                if j < len(lines):
                    line = lines[j].strip()
                    if line:
                        content_lines.append(line)
            
            content = '\n'.join(content_lines).strip()
            sections[section_name] = content
        
        # Fallback: gunakan regex jika section header tidak terdeteksi
        if not any(sections.values()):
            sections = self.extract_sections_with_regex(normalized_text, text_lower)
        
        return self.clean_sections(sections)
    
    def extract_sections_with_regex(self, normalized_text: str, text_lower: str) -> Dict[str, str]:
        """Ekstrak sections menggunakan regex patterns sebagai fallback"""
        sections = {'summary': '', 'skills': '', 'experience': '', 'education': '', 'accomplishments': ''}
        
        patterns = {
            'summary': [
                r'(?:^|\n)\s*(?:summary|profile|overview|about|professional summary|career focus)\s*:?\s*\n(.*?)(?=\n\s*(?:skills|experience|education|accomplishments|work history|employment)\s*:?\s*\n|\Z)',
            ],
            'skills': [
                r'(?:^|\n)\s*(?:skills|technical skills|professional skills|key skills|core competencies|summary of skills)\s*:?\s*\n(.*?)(?=\n\s*(?:experience|education|accomplishments|work history|employment|summary|profile)\s*:?\s*\n|\Z)',
            ],
            'experience': [
                r'(?:^|\n)\s*(?:experience|work experience|employment history|professional experience|work history)\s*:?\s*\n(.*?)(?=\n\s*(?:education|accomplishments|skills|certifications)\s*:?\s*\n|\Z)',
            ],
            'education': [
                r'(?:^|\n)\s*(?:education|academic background|qualifications|educational background)\s*:?\s*\n(.*?)(?=\n\s*(?:accomplishments|skills|experience|certifications)\s*:?\s*\n|\Z)',
            ],
            'accomplishments': [
                r'(?:^|\n)\s*(?:accomplishments|achievements|certifications|certificates|core accomplishments|awards|honors|licenses|certifications and training)\s*:?\s*\n(.*?)(?=\n\s*(?:skills|experience|education|summary)\s*:?\s*\n|\Z)',
            ]
        }
        
        for section_name, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
                if match:
                    start, end = match.start(1), match.end(1)
                    content = normalized_text[start:end].strip()
                    if content and len(content) > 10:
                        sections[section_name] = content
                        break
        
        return sections
    
    def clean_sections(self, sections: Dict[str, str]) -> Dict[str, str]:
        """Bersihkan dan normalisasi sections"""
        for section_name, content in sections.items():
            if not content:
                continue
            
            # Bersihkan duplikasi dari section lain
            for other_section, other_content in sections.items():
                if other_section == section_name or not other_content:
                    continue
            
            # Normalisasi newlines
            content = re.sub(r'\n\s*\n', '\n', content)
            content = content.strip()
            sections[section_name] = content
        
        return sections
    
    def extract_realtime(self, cv_path: str) -> ExtractionResult:
        """Ekstraksi real-time dari PDF path"""
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"{cv_path}_{os.path.getmtime(cv_path) if os.path.exists(cv_path) else 0}"
            if cache_key in self.extraction_cache:
                cached_result = self.extraction_cache[cache_key]
                cached_result.extraction_time_ms = (time.time() - start_time) * 1000
                return cached_result
            
            # Validate PDF path
            if not cv_path or not os.path.exists(cv_path):
                return ExtractionResult(
                    success=False,
                    error_message=f"PDF file not found: {cv_path}",
                    extraction_time_ms=(time.time() - start_time) * 1000
                )
            
            # Ekstrak text mentah
            cv_raw_text = self.extract_pdf_text(cv_path)
            
            if not cv_raw_text:
                return ExtractionResult(
                    success=False,
                    error_message="Failed to extract text from PDF",
                    extraction_time_ms=(time.time() - start_time) * 1000
                )
            
            # Ekstrak sections
            sections = self.extract_cv_sections(cv_raw_text)
            
            # Buat result
            result = ExtractionResult(
                success=True,
                cv_raw_text=cv_raw_text,
                summary_section=sections['summary'],
                skills_section=sections['skills'],
                experience_section=sections['experience'],
                education_section=sections['education'],
                accomplishments_section=sections['accomplishments'],
                extraction_time_ms=(time.time() - start_time) * 1000
            )
            
            # Cache hasil untuk performa
            self.extraction_cache[cache_key] = result
            
            # Limit cache size
            if len(self.extraction_cache) > 100:
                # Remove oldest entries
                oldest_key = min(self.extraction_cache.keys())
                del self.extraction_cache[oldest_key]
            
            return result
            
        except Exception as e:
            return ExtractionResult(
                success=False,
                error_message=f"Extraction error: {str(e)}",
                extraction_time_ms=(time.time() - start_time) * 1000
            )
    
    def get_pdf_info(self, cv_path: str) -> Dict[str, any]:
        """Get basic PDF information"""
        if not os.path.exists(cv_path):
            return {"exists": False, "error": "File not found"}
        
        try:
            stat = os.stat(cv_path)
            doc = fitz.open(cv_path)
            
            info = {
                "exists": True,
                "filename": os.path.basename(cv_path),
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "page_count": len(doc),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", "")
            }
            
            doc.close()
            return info
            
        except Exception as e:
            return {"exists": True, "error": str(e)}
    
    def clear_cache(self):
        """Clear extraction cache"""
        self.extraction_cache.clear()


# Global instance
realtime_extractor = RealtimePDFExtractor()

def extract_cv_realtime(cv_path: str) -> ExtractionResult:
    """Convenience function untuk ekstraksi real-time"""
    return realtime_extractor.extract_realtime(cv_path)

def get_pdf_info(cv_path: str) -> Dict[str, any]:
    """Convenience function untuk info PDF"""
    return realtime_extractor.get_pdf_info(cv_path)


# Test function
if __name__ == "__main__":
    # Test extraction
    test_path = "data/INFORMATION-TECHNOLOGY/15118506.pdf"
    
    print("Testing real-time PDF extraction...")
    result = extract_cv_realtime(test_path)
    
    if result.success:
        print(f"✅ Extraction successful in {result.extraction_time_ms:.2f}ms")
        print(f"Text length: {len(result.cv_raw_text)} characters")
        print(f"Summary: {result.summary_section[:100]}...")
        print(f"Skills: {result.skills_section[:100]}...")
    else:
        print(f"❌ Extraction failed: {result.error_message}")
    
    # Test PDF info
    info = get_pdf_info(test_path)
    print(f"PDF Info: {info}")