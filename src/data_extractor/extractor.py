import os
import re
import fitz  # PyMuPDF
import base64
import json
import hashlib
import getpass
import mysql.connector
from cryptography.fernet import Fernet
from faker import Faker
from datetime import datetime
from dataclasses import dataclass
import time

DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "ats_db"
DB_PASSWORD = ""

ENCRYPTION_KEY_FILE = "ats_encryption.key"
ENCRYPTION_CONFIG_FILE = "ats_config.json"

# ================== EXTRACTION RESULT ===================
@dataclass
class ExtractionResult:
    success: bool
    cv_raw_text: str = ""
    summary_section: str = ""
    skills_section: str = ""
    experience_section: str = ""
    education_section: str = ""
    accomplishments_section: str = ""
    error_message: str = ""
    extraction_time_ms: float = 0.0
    keyword_matches: dict = None

    def __post_init__(self):
        if self.keyword_matches is None:
            self.keyword_matches = {}

# ================== ENCRYPTION MANAGER ===================
class EncryptionManager:
    def __init__(self):
        self.key = None
        self.cipher = None
        self.encryption_enabled = False

    def generate_key(self) -> bytes:
        return Fernet.generate_key()

    def save_key(self, key: bytes, password: str = None):
        if password:
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), b'ats_salt_2024', 100000)
            password_cipher = Fernet(base64.urlsafe_b64encode(password_hash))
            encrypted_key = password_cipher.encrypt(key)
            with open(ENCRYPTION_KEY_FILE, 'wb') as f:
                f.write(encrypted_key)
        else:
            with open(ENCRYPTION_KEY_FILE, 'wb') as f:
                f.write(key)

    def load_key(self, password: str = None) -> bytes:
        if not os.path.exists(ENCRYPTION_KEY_FILE):
            return None
        with open(ENCRYPTION_KEY_FILE, 'rb') as f:
            key_data = f.read()
        if password:
            try:
                password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), b'ats_salt_2024', 100000)
                password_cipher = Fernet(base64.urlsafe_b64encode(password_hash))
                key = password_cipher.decrypt(key_data)
                return key
            except:
                return None
        else:
            return key_data

    def initialize(self, password: str = None):
        key = self.load_key(password)
        if not key:
            key = self.generate_key()
            self.save_key(key, password)
        self.key = key
        self.cipher = Fernet(key)
        self.encryption_enabled = True

    def encrypt(self, text: str) -> str:
        if not self.encryption_enabled or not text:
            return text
        encrypted_data = self.cipher.encrypt(text.encode('utf-8'))
        return base64.b64encode(encrypted_data).decode('utf-8')

    def decrypt(self, encrypted_text: str) -> str:
        if not self.encryption_enabled or not encrypted_text:
            return encrypted_text
        try:
            encrypted_data = base64.b64decode(encrypted_text.encode('utf-8'))
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return decrypted_data.decode('utf-8')
        except:
            return encrypted_text

# =============== DATABASE ===============
def get_mysql_password():
    global DB_PASSWORD
    if DB_PASSWORD:
        return DB_PASSWORD
    DB_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    if DB_PASSWORD:
        return DB_PASSWORD
    try:
        test_conn = mysql.connector.connect(host=DB_HOST, user=DB_USER)
        test_conn.close()
        return ""
    except Exception:
        pass
    DB_PASSWORD = getpass.getpass("Enter MySQL Password: ")
    return DB_PASSWORD

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=get_mysql_password(),
        database=DB_NAME
    )

# =============== CV EXTRACTION ===============
def extract_pdf_text(pdf_path: str) -> str:
    """Extract text from PDF with better structure preservation"""
    try:
        doc = fitz.open(pdf_path)
        full_text = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Use dict format for better text extraction
            text_dict = page.get_text("dict")
            
            page_text = []
            for block in text_dict["blocks"]:
                if "lines" in block:  # Text block
                    block_text = []
                    for line in block["lines"]:
                        line_text = []
                        for span in line["spans"]:
                            if span["text"].strip():
                                line_text.append(span["text"])
                        if line_text:
                            block_text.append(" ".join(line_text))
                    if block_text:
                        page_text.extend(block_text)
            
            if page_text:
                full_text.extend(page_text)
        
        doc.close()
        return '\n'.join(full_text)
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""

def extract_cv_sections(cv_text):
    """Extract CV sections using regex patterns"""
    sections = {'summary': '', 'skills': '', 'experience': '', 'education': '', 'accomplishments': ''}
    
    if not cv_text:
        return sections
    
    normalized_text = cv_text.replace('\r', '\n')
    lines = normalized_text.split('\n')
    text_lower = normalized_text.lower()

    ignored_sections = [
        'others', 'other', 'personal information', 'personal info', 'additional information', 
        'additional info', 'miscellaneous', 'references', 'hobbies', 'interests', 
        'personal details', 'contact information', 'contact info', 'contact',
        'objective', 'career objective', 'personal statement', 'highlights'
    ]
    
    section_positions = []
    
    for i, line in enumerate(lines):
        line_clean = line.strip().lower()
        if not line_clean or len(line_clean) > 100:  # Skip very long lines
            continue

        if any(ignored in line_clean for ignored in ignored_sections):
            continue
            
        if re.match(r'^(summary|profile|overview|about|professional summary|career focus|executive profile)$', line_clean):
            section_positions.append(('summary', i))  
        elif re.match(r'^(skills|summary of skills|technical skills|professional skills|key skills|core competencies)$', line_clean):
            section_positions.append(('skills', i))
        elif re.match(r'^(experience|work experience|employment history|professional experience|work history)$', line_clean):
            section_positions.append(('experience', i))
        elif re.match(r'^(education|academic background|qualifications|educational background|education and training)$', line_clean):
            section_positions.append(('education', i))
        elif re.match(r'^(accomplishments|achievements|certifications|certificates|awards|honors|licenses|core acccomplishments|certifications and training)$', line_clean):
            section_positions.append(('accomplishments', i))

    section_positions.sort(key=lambda x: x[1])
    
    for i, (section_name, start_pos) in enumerate(section_positions):
        # Determine end position
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
        if section_name == 'summary':
            sections['summary'] = content 
        else:
            sections[section_name] = content
    
    if not any(sections.values()):
        sections = extract_sections_with_regex(normalized_text, text_lower)
    
    return sections

def extract_sections_with_regex(normalized_text, text_lower):
    """Fallback method using regex patterns"""
    sections = {'summary': '', 'skills': '', 'experience': '', 'education': '', 'accomplishments': ''}
    
    # Define regex patterns for each section
    patterns = {
        'summary': r'(?i)(summary|profile|overview|about)[:\-\s]*\n(.*?)(?=\n\s*(skills|experience|education|accomplishments|$))',
        'skills': r'(?i)(skills|technical skills|core competencies)[:\-\s]*\n(.*?)(?=\n\s*(experience|education|accomplishments|summary|$))',
        'experience': r'(?i)(experience|work experience|employment)[:\-\s]*\n(.*?)(?=\n\s*(education|skills|accomplishments|summary|$))',
        'education': r'(?i)(education|academic background)[:\-\s]*\n(.*?)(?=\n\s*(experience|skills|accomplishments|summary|$))',
        'accomplishments': r'(?i)(accomplishments|achievements|certifications)[:\-\s]*\n(.*?)(?=\n\s*(experience|skills|education|summary|$))'
    }
    
    for section_name, pattern in patterns.items():
        match = re.search(pattern, normalized_text, re.DOTALL | re.MULTILINE)
        if match:
            sections[section_name] = match.group(2).strip()
    
    return sections

def search_keywords_in_cv(cv_text: str, keywords: list) -> dict:
    """Search for keywords using multiple algorithms"""
    if not cv_text or not keywords:
        return {}
    
    # Simple keyword search for now
    results = {}
    cv_lower = cv_text.lower()
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        positions = []
        start = 0
        while True:
            pos = cv_lower.find(keyword_lower, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        results[keyword] = positions
    
    return results

BASE_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

def extract_realtime(cv_path: str, keywords: list = None) -> ExtractionResult:
    """Real-time CV extraction with keyword search"""
    full_path = os.path.join(BASE_DATA_PATH, cv_path) if not os.path.isabs(cv_path) else cv_path
    start_time = time.time()
    
    # Validate file existence
    if not os.path.exists(full_path):
        return ExtractionResult(
            success=False, 
            error_message=f"File not found: {full_path}",
            extraction_time_ms=(time.time() - start_time) * 1000
        )
    
    # Validate file extension
    if not full_path.lower().endswith('.pdf'):
        return ExtractionResult(
            success=False, 
            error_message="Only PDF files are supported",
            extraction_time_ms=(time.time() - start_time) * 1000
        )
    
    try:
        # Extract text from PDF
        raw_text = extract_pdf_text(full_path)
        if not raw_text.strip():
            return ExtractionResult(
                success=False, 
                error_message="No text content found in PDF",
                extraction_time_ms=(time.time() - start_time) * 1000
            )
        
        # Extract sections
        sections = extract_cv_sections(raw_text)
        
        # Search for keywords if provided
        keyword_matches = {}
        if keywords:
            keyword_matches = search_keywords_in_cv(raw_text, keywords)
        
        extraction_time = (time.time() - start_time) * 1000
        
        return ExtractionResult(
            success=True,
            cv_raw_text=raw_text,
            summary_section=sections['summary'],
            skills_section=sections['skills'],
            experience_section=sections['experience'],
            education_section=sections['education'],
            accomplishments_section=sections['accomplishments'],
            keyword_matches=keyword_matches,
            extraction_time_ms=extraction_time
        )
        
    except Exception as e:
        return ExtractionResult(
            success=False,
            error_message=f"Extraction failed: {str(e)}",
            extraction_time_ms=(time.time() - start_time) * 1000
        )

def insert_applicant_profile(profile: dict, encrypt: bool = False) -> int:
    """Insert applicant profile into database"""
    try:
        db = get_db_connection()
        cursor = db.cursor()

        if encrypt and encryption.encryption_enabled:
            encrypted_profile = {k: encryption.encrypt(v) if v else v for k, v in profile.items()}
        else:
            encrypted_profile = profile

        cursor.execute("""
            INSERT INTO ApplicantProfile (first_name, last_name, date_of_birth, address, phone_number, is_encrypted)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            encrypted_profile.get('first_name', ''),
            encrypted_profile.get('last_name', ''),
            encrypted_profile.get('date_of_birth', ''),
            encrypted_profile.get('address', ''),
            encrypted_profile.get('phone_number', ''),
            encrypt
        ))
        
        applicant_id = cursor.lastrowid
        db.commit()
        return applicant_id
        
    except Exception as e:
        print(f"Database error in insert_applicant_profile: {e}")
        return -1
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

def insert_application_detail(applicant_id: int, cv_path: str, application_role: str = "General", encrypt: bool = False) -> bool:
    """Insert application details into database (simplified for new schema)"""
    try:
        db = get_db_connection()
        cursor = db.cursor()

        if encrypt and encryption.encryption_enabled:
            application_role = encryption.encrypt(application_role) if application_role else ""
        
        cursor.execute("""
            INSERT INTO ApplicationDetail
            (applicant_id, application_role, cv_path, is_encrypted)
            VALUES (%s, %s, %s, %s)
        """, (
            applicant_id,
            application_role,
            cv_path,
            encrypt
        ))
        
        db.commit()
        return True
        
    except Exception as e:
        print(f"Database error in insert_application_detail: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

def get_cv_summary_with_extraction(detail_id: int) -> dict:
    """Get CV summary with real-time extraction"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Get application and profile data
        query = """
        SELECT ad.detail_id, ad.cv_path, ad.application_role,
               ap.first_name, ap.last_name, ap.phone_number, ap.address
        FROM ApplicationDetail ad
        JOIN ApplicantProfile ap ON ad.applicant_id = ap.applicant_id
        WHERE ad.detail_id = %s
        """
        
        cursor.execute(query, (detail_id,))
        result = cursor.fetchone()
        
        if not result:
            return {}
        
        detail_id, cv_path, role, first_name, last_name, phone, address = result
        
        # Extract CV content in real-time
        extraction_result = extract_realtime(cv_path)
        
        summary_data = {
            'detail_id': detail_id,
            'name': f"{first_name} {last_name}",
            'phone': phone or 'Not available',
            'address': address or 'Not available', 
            'role': role or 'Not specified',
            'cv_path': cv_path
        }
        
        if extraction_result.success:
            summary_data.update({
                'summary': extraction_result.summary_section or 'No summary available',
                'skills': extraction_result.skills_section or 'No skills listed',
                'experience': extraction_result.experience_section or 'No experience listed',
                'education': extraction_result.education_section or 'No education listed',
                'accomplishments': extraction_result.accomplishments_section or 'No accomplishments listed'
            })
        else:
            # Fallback data if extraction fails
            summary_data.update({
                'summary': f'Extraction failed: {extraction_result.error_message}',
                'skills': 'Unable to extract skills',
                'experience': 'Unable to extract experience',
                'education': 'Unable to extract education',
                'accomplishments': 'Unable to extract accomplishments'
            })
        
        return summary_data
        
    except Exception as e:
        print(f"Error getting CV summary: {e}")
        return {}
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

def search_cvs_with_extraction(keywords: str, algorithm: str = "kmp", top_n: int = 10) -> list:
    """Search CVs with real-time extraction"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Get all CV data
        query = """
        SELECT ad.detail_id, ad.cv_path, 
               CONCAT(ap.first_name, ' ', ap.last_name) as applicant_name,
               ad.application_role
        FROM ApplicationDetail ad
        JOIN ApplicantProfile ap ON ad.applicant_id = ap.applicant_id
        WHERE ad.cv_path IS NOT NULL
        """
        
        cursor.execute(query)
        cv_data = cursor.fetchall()
        
        keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        results = []
        
        for detail_id, cv_path, applicant_name, role in cv_data:
            # Extract CV content in real-time
            extraction_result = extract_realtime(cv_path, keyword_list)
            
            if extraction_result.success:
                # Count keyword matches
                total_matches = 0
                keyword_counts = {}
                
                for keyword in keyword_list:
                    count = len(extraction_result.keyword_matches.get(keyword, []))
                    keyword_counts[keyword] = count
                    total_matches += count
                
                if total_matches > 0:
                    results.append({
                        'detail_id': detail_id,
                        'applicant_name': applicant_name,
                        'application_role': role,
                        'total_matches': total_matches,
                        'keyword_matches': keyword_counts,
                        'cv_path': cv_path
                    })
        
        # Sort by total matches (descending)
        results.sort(key=lambda x: x['total_matches'], reverse=True)
        
        return results[:top_n]
        
    except Exception as e:
        print(f"Error searching CVs: {e}")
        return []
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

# ================== INITIALIZATION =============
encryption = EncryptionManager()
# Uncomment to enable encryption:
# encryption.initialize(password="your-password")

# Example usage functions
def demo_realtime_extraction():
    """Demo real-time extraction"""
    print("DEMO: Real-time CV Extraction")
    print("=" * 40)
    
    # Test extraction
    test_cv_path = "data/ENGINEERING/13149176.pdf"  # Adjust path as needed
    keywords = ["Python", "JavaScript", "engineer"]
    
    print(f"Extracting: {test_cv_path}")
    result = extract_realtime(test_cv_path, keywords)
    
    if result.success:
        print(f"✅ Extraction successful in {result.extraction_time_ms:.1f}ms")
        print(f"📄 Text length: {len(result.cv_raw_text)} characters")
        print(f"📝 Summary: {result.summary_section[:100]}...")
        print(f"🔍 Keyword matches: {result.keyword_matches}")
    else:
        print(f"❌ Extraction failed: {result.error_message}")

def demo_database_integration():
    """Demo database integration with real-time extraction"""
    print("\nDEMO: Database Integration")
    print("=" * 40)
    
    # Test search
    results = search_cvs_with_extraction("Python, engineer", "kmp", 5)
    print(f"Found {len(results)} matching CVs")
    
    for result in results:
        print(f"- {result['applicant_name']}: {result['total_matches']} matches")
    
    # Test summary
    if results:
        detail_id = results[0]['detail_id']
        summary = get_cv_summary_with_extraction(detail_id)
        print(f"\nSummary for {summary.get('name', 'Unknown')}:")
        print(f"  Role: {summary.get('role')}")
        print(f"  Skills: {summary.get('skills', '')[:100]}...")

if __name__ == "__main__":
    print("ATS REAL-TIME EXTRACTION DEMO")
    print("=" * 50)
    
    try:
        demo_realtime_extraction()
        demo_database_integration()
        print("\n✅ All demos completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()