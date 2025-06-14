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
    keyword_matches: dict[str, list[int]] = None

    def __post_init__(self):
        if self.keyword_matches is None:
            self.keyword_matches = {}

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

def extract_cv_sections(cv_raw_text: str) -> dict[str, str]:
    """Extract CV sections using improved pattern matching"""
    sections = {
        'summary': '',
        'skills': '',
        'experience': '',
        'education': '',
        'accomplishments': ''
    }
    
    if not cv_raw_text:
        return sections
    
    lines = cv_raw_text.split('\n')
    
    # Define section headers with variations
    section_patterns = {
        'summary': [
            r'^\s*(summary|profile|about|objective|career\s+objective|professional\s+summary)\s*:?\s*$',
            r'^\s*(summary|profile|about|objective)\s*$'
        ],
        'skills': [
            r'^\s*(skills|technical\s+skills|core\s+competencies|expertise|competencies)\s*:?\s*$',
            r'^\s*(skills|competencies)\s*$'
        ],
        'experience': [
            r'^\s*(experience|work\s+experience|employment|professional\s+experience|career\s+history)\s*:?\s*$',
            r'^\s*(experience|employment)\s*$'
        ],
        'education': [
            r'^\s*(education|academic\s+background|qualifications|educational\s+background)\s*:?\s*$',
            r'^\s*(education|qualifications)\s*$'
        ],
        'accomplishments': [
            r'^\s*(accomplishments|achievements|awards|honors|certifications)\s*:?\s*$',
            r'^\s*(accomplishments|achievements)\s*$'
        ]
    }
    
    # Find section positions
    section_positions = []
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        for section, patterns in section_patterns.items():
            for pattern in patterns:
                if re.match(pattern, line_lower):
                    section_positions.append((section, i))
                    break
    
    # Sort by position
    section_positions.sort(key=lambda x: x[1])
    
    # Extract content for each section
    for i, (section, start_line) in enumerate(section_positions):
        end_line = section_positions[i + 1][1] if i + 1 < len(section_positions) else len(lines)
        
        # Get content between section headers
        content_lines = []
        for line_idx in range(start_line + 1, end_line):
            line = lines[line_idx].strip()
            if line:  # Skip empty lines
                content_lines.append(line)
        
        sections[section] = '\n'.join(content_lines)
    
    return sections

def search_keywords_in_cv(cv_text: str, keywords: list[str]) -> dict[str, list[int]]:
    """Search for keywords using multiple algorithms"""
    if not cv_text or not keywords:
        return {}
    
    # Use Aho-Corasick for multiple pattern matching
    results = SearchAlgorithms.aho_corasick_search(cv_text, keywords)
    
    # Filter out empty results
    return {k: v for k, v in results.items() if v}

BASE_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

def extract_realtime(cv_path: str, keywords: list[str] = None) -> ExtractionResult:
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

def insert_applicant_profile(profile: dict[str, str], encrypt: bool = False) -> int:
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

def insert_application_detail(applicant_id: int, cv_path: str, result: ExtractionResult, 
                            encrypt: bool = False, application_role: str = "General") -> bool:
    """Insert application details into database"""
    try:
        db = get_db_connection()
        cursor = db.cursor()

        if encrypt and encryption.encryption_enabled:
            cv_raw = encryption.encrypt(result.cv_raw_text) if result.cv_raw_text else ""
            summary = encryption.encrypt(result.summary_section) if result.summary_section else ""
            skills = encryption.encrypt(result.skills_section) if result.skills_section else ""
            experience = encryption.encrypt(result.experience_section) if result.experience_section else ""
            education = encryption.encrypt(result.education_section) if result.education_section else ""
            accomplishments = encryption.encrypt(result.accomplishments_section) if result.accomplishments_section else ""
        else:
            cv_raw = result.cv_raw_text
            summary = result.summary_section
            skills = result.skills_section
            experience = result.experience_section
            education = result.education_section
            accomplishments = result.accomplishments_section

        cursor.execute("""
            INSERT INTO ApplicationDetail
            (applicant_id, application_role, cv_path, cv_raw_text,
            summary_section, skills_section, experience_section,
            education_section, accomplishments_section, is_encrypted, 
            extraction_status, extraction_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            applicant_id,
            application_role,
            cv_path,
            cv_raw,
            summary,
            skills,
            experience,
            education,
            accomplishments,
            encrypt,
            'completed' if result.success else 'failed',
            datetime.now()
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

# ================== INITIALIZATION =============
encryption = EncryptionManager()
# Uncomment to enable encryption:
# encryption.initialize(password="your-password")
