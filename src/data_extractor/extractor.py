import os
import glob
import re
from faker import Faker
import fitz 
import mysql.connector
import getpass 
import random
import base64
from cryptography.fernet import Fernet
import json
import hashlib

DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "ats_db"

DB_PASSWORD = os.getenv('MYSQL_PASSWORD', '')  

if not DB_PASSWORD:
    try:
        test_conn = mysql.connector.connect(host=DB_HOST, user=DB_USER)
        test_conn.close()
        DB_PASSWORD = "" 
    except mysql.connector.Error:
        DB_PASSWORD = getpass.getpass("Enter MySQL Password: ")

        try:
            test_conn = mysql.connector.connect(
                host=DB_HOST, 
                user=DB_USER, 
                password=DB_PASSWORD
            )
            test_conn.close()
            print("Password verified successfully")
        except mysql.connector.Error as e:
            print("Password verification failed")
            exit(1) 

# Encryption configuration
ENCRYPTION_KEY_FILE = "ats_encryption.key"
ENCRYPTION_CONFIG_FILE = "ats_config.json"

class EncryptionManager:
    def __init__(self):
        self.key = None
        self.cipher = None
        self.encryption_enabled = False
    
    def generate_key(self) -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()
    
    def save_key(self, key: bytes, password: str = None):
        """Save encryption key to file, optionally password-protected."""
        if password:
            # Derive key from password using PBKDF2
            password_hash = hashlib.pbkdf2_hmac('sha256', 
                                               password.encode('utf-8'), 
                                               b'ats_salt_2024', 
                                               100000)
            password_cipher = Fernet(base64.urlsafe_b64encode(password_hash))
            encrypted_key = password_cipher.encrypt(key)
            
            with open(ENCRYPTION_KEY_FILE, 'wb') as f:
                f.write(encrypted_key)
        else:
            with open(ENCRYPTION_KEY_FILE, 'wb') as f:
                f.write(key)
        
        print(f"Encryption key saved to {ENCRYPTION_KEY_FILE}")
    
    def load_key(self, password: str = None) -> bytes:
        """Load encryption key from file."""
        if not os.path.exists(ENCRYPTION_KEY_FILE):
            return None
        
        with open(ENCRYPTION_KEY_FILE, 'rb') as f:
            key_data = f.read()
        
        if password:
            try:
                password_hash = hashlib.pbkdf2_hmac('sha256', 
                                                   password.encode('utf-8'), 
                                                   b'ats_salt_2024', 
                                                   100000)
                password_cipher = Fernet(base64.urlsafe_b64encode(password_hash))
                key = password_cipher.decrypt(key_data)
                return key
            except Exception as e:
                print(f"Failed to decrypt key with password: {e}")
                return None
        else:
            return key_data
    
    def initialize_encryption(self, password: str = None) -> bool:
        """Initialize encryption with existing or new key."""
        # Try to load existing key
        key = self.load_key(password)
        
        if not key:
            # Generate new key
            key = self.generate_key()
            self.save_key(key, password)
            print("Generated new encryption key")
        else:
            print("Loaded existing encryption key")
        
        self.key = key
        self.cipher = Fernet(key)
        self.encryption_enabled = True
        return True
    
    def encrypt_text(self, text: str) -> str:
        """Encrypt text and return base64 encoded string."""
        if not self.encryption_enabled or not text:
            return text
        
        encrypted_data = self.cipher.encrypt(text.encode('utf-8'))
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_text(self, encrypted_text: str) -> str:
        """Decrypt base64 encoded encrypted text."""
        if not self.encryption_enabled or not encrypted_text:
            return encrypted_text
        
        try:
            encrypted_data = base64.b64decode(encrypted_text.encode('utf-8'))
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            print(f"Decryption failed: {e}")
            return encrypted_text

    def is_encrypted_data(self, text: str) -> bool:
        """Check if text appears to be encrypted (base64 encoded)."""
        if not text or len(text) < 10:
            return False
        
        try:
            # Try to decode as base64
            decoded = base64.b64decode(text.encode('utf-8'))
            # Check if it looks like Fernet encrypted data (starts with specific bytes)
            return len(decoded) > 10 and decoded.startswith(b'\x80')
        except:
            return False

def save_encryption_config(encryption_enabled: bool, password_protected: bool = False):
    """Save encryption configuration."""
    config = {
        "encryption_enabled": encryption_enabled,
        "password_protected": password_protected,
        "version": "1.0"
    }
    
    with open(ENCRYPTION_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_encryption_config() -> dict:
    """Load encryption configuration."""
    if not os.path.exists(ENCRYPTION_CONFIG_FILE):
        return {"encryption_enabled": False, "password_protected": False}
    
    try:
        with open(ENCRYPTION_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"encryption_enabled": False, "password_protected": False}

# Global encryption manager
encryption_manager = EncryptionManager()

# Modified table creation with encryption support
create_applicant_profile_table = """
CREATE TABLE IF NOT EXISTS ApplicantProfile (
    applicant_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(255) DEFAULT NULL,
    last_name VARCHAR(255) DEFAULT NULL,
    date_of_birth VARCHAR(255) DEFAULT NULL,
    address TEXT DEFAULT NULL,
    phone_number VARCHAR(255) DEFAULT NULL,
    is_encrypted BOOLEAN DEFAULT FALSE
)
"""

create_application_detail_table = """
CREATE TABLE IF NOT EXISTS ApplicationDetail (
    detail_id INT AUTO_INCREMENT PRIMARY KEY,
    applicant_id INT NOT NULL,
    application_role VARCHAR(255) DEFAULT NULL,
    cv_path TEXT,
    cv_raw_text LONGTEXT,
    summary_section TEXT,
    skills_section TEXT,
    experience_section TEXT,
    education_section TEXT,
    accomplishments_section TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (applicant_id) REFERENCES ApplicantProfile(applicant_id)
)
"""

# create database
conn_init = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD
)
cursor_init = conn_init.cursor()
cursor_init.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
cursor_init.close()
conn_init.close()

db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)
cursor = db.cursor()

cursor.execute(create_applicant_profile_table)
cursor.execute(create_application_detail_table)
db.commit()

# seeding with faker
faker = Faker('id_ID')

def generate_phone():
    return "08" + ''.join(faker.random_choices(elements='0123456789', length=10))

def generate_fake_profile():
    # use simple Indonesian name generation
    first_name = faker.first_name()
    last_name = faker.last_name() 
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": generate_phone(),
        "date_of_birth": faker.date_of_birth(minimum_age=22, maximum_age=60).isoformat(),
        "address": faker.address().replace('\n', ', ')
    }

def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        full_text = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Method 1: Try structured extraction with blocks
            blocks = page.get_text("blocks")
            page_lines = []
            
            # Sort blocks by position (top to bottom, left to right)
            blocks.sort(key=lambda block: (block[1], block[0]))  # Sort by y, then x
            
            for block in blocks:
                if len(block) >= 5:  # Text block
                    text = block[4].strip()
                    if text:
                        # Split block text into lines and clean
                        lines = text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line:
                                page_lines.append(line)
            
            # If structured extraction didn't work well, try simple extraction
            if len(page_lines) < 5:
                simple_text = page.get_text().strip()
                if simple_text:
                    page_lines = [line.strip() for line in simple_text.split('\n') if line.strip()]
            
            if page_lines:
                full_text.extend(page_lines)
        
        doc.close()
        
        # Join with newlines and clean up
        result = '\n'.join(full_text)
        return clean_extracted_text(result)
        
    except Exception as e:
        print(f"PyMuPDF extraction failed for {pdf_path}: {e}")
        return ""
    
def clean_extracted_text(text):
    if not text:
        return ""
    
    lines = text.split('\n')
    cleaned_lines = []
    
    prev_line = ""
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
        
        # Fix common PDF extraction issues
        line = re.sub(r'\s+', ' ', line)  

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
    
    final_lines = []
    for line in cleaned_lines:
        line = re.sub(r'(\d{2}/\d{4})\s+to\s+(\d{2}/\d{4})', r'\1 to \2', line)
        line = re.sub(r'(\d{2}/\d{4})\s*-\s*(\d{2}/\d{4})', r'\1 - \2', line)
        
        line = re.sub(r'Company Name\s*[,\s]*City\s*[,\s]*State', 'Company Name, City, State', line)
        
        line = re.sub(r'([a-z])([A-Z])', r'\1 \2', line)  
        line = re.sub(r'([0-9])([A-Z])', r'\1 \2', line) 
        
        final_lines.append(line)
    
    return '\n'.join(final_lines)

def extract_cv_sections(cv_text):
    sections = {'summary': '', 'skills': '', 'experience': '', 'education': '', 'accomplishments': ''}
    
    if not cv_text:
        return sections
    
    # Normalize text
    normalized_text = cv_text.replace('\r', '\n')
    text_lower = normalized_text.lower()
    
    # SUMMARY PATTERNS - improved with line boundaries
    summary_patterns = [
        r'(?:^|\n)\s*summary\s+(.*?)(?=\n\s*(?:skills|experience|education|accomplishments|certifications|interests|additional))',
        r'(?:^|\n)\s*profile\s+(.*?)(?=\n\s*(?:skills|experience|education|accomplishments|certifications|interests|additional))',
        r'(?:^|\n)\s*overview\s+(.*?)(?=\n\s*(?:skills|experience|education|accomplishments|certifications|interests|additional))',
        r'(?:^|\n)\s*about\s+(.*?)(?=\n\s*(?:skills|experience|education|accomplishments|certifications|interests|additional))',
        r'(?:^|\n)\s*professional\s+summary\s+(.*?)(?=\n\s*(?:skills|experience|education|accomplishments|certifications|interests|additional))',
    ]
    
    # Try summary regex patterns first
    for pattern in summary_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            start, end = match.start(1), match.end(1)
            sections['summary'] = normalized_text[start:end].strip()[:1000]
            break
    
    # HIGHLIGHTS - merge into summary section
    if not sections['summary']:
        highlights_patterns = [
            r'(?:^|\n)\s*highlights\s+(.*?)(?=\n\s*(?:skills|experience|education|accomplishments|certifications|interests|additional))',
            r'(?:^|\n)\s*key\s+highlights\s+(.*?)(?=\n\s*(?:skills|experience|education|accomplishments|certifications|interests|additional))',
            r'(?:^|\n)\s*core\s+competencies\s+(.*?)(?=\n\s*(?:skills|experience|education|accomplishments|certifications|interests|additional))'
        ]
        
        for pattern in highlights_patterns:
            match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
            if match:
                start, end = match.start(1), match.end(1)
                sections['summary'] = normalized_text[start:end].strip()[:1000]
                break
    
    # Handle summary without explicit header (after job title/position)
    if not sections['summary']:
        lines = normalized_text.split('\n')
        for i, line in enumerate(lines[:15]):
            line_stripped = line.strip()
            line_lower = line_stripped.lower()
            
            # Skip empty lines and contact info
            if not line_stripped or any(indicator in line_lower for indicator in ['@', 'phone', 'email', 'address']):
                continue
                
            # Skip single words or very short lines (likely names/titles)
            if len(line_stripped.split()) <= 3:
                continue
            
            # If we find a descriptive sentence, it's likely summary
            if (len(line_stripped.split()) >= 5 and 
                any(word in line_lower for word in ['specializing', 'experienced', 'professional', 'expert', 'skilled', 'responsible', 'managing'])):
                
                # Find where summary ends
                summary_lines = [line_stripped]
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_line = lines[j].strip()
                    if not next_line:
                        continue
                    
                    # Stop if we hit a section header (but not highlights - that goes to summary)
                    next_lower = next_line.lower()
                    if (len(next_line) <= 50 and 
                        any(header in next_lower for header in ['skills', 'experience', 'education', 'accomplishments'])):
                        break
                    
                    # Stop if we hit date patterns (likely experience section)
                    if re.search(r'\b\d{4}\s+to\s+\d{4}\b|\b\d{1,2}/\d{4}\s*[-–]\s*\d{1,2}/\d{4}\b', next_line):
                        break
                    
                    # Stop if we hit "Company Name" patterns
                    if 'company name' in next_lower:
                        break
                    
                    summary_lines.append(next_line)
                
                sections['summary'] = '\n'.join(summary_lines).strip()[:1000]
                break
    
    # SKILLS - handle both early and late positioning in CV
    skills_patterns = [
        # Skills section that appears mid-document (before experience/education)
        r'(?:^|\n)\s*skills\s+(.*?)(?=\n\s*(?:experience|education|accomplishments|achievements|certifications|interests|additional))',
        r'(?:^|\n)\s*technical\s+skills\s+(.*?)(?=\n\s*(?:experience|education|accomplishments|achievements|certifications|interests|additional))',
        r'(?:^|\n)\s*professional\s+skills\s+(.*?)(?=\n\s*(?:experience|education|accomplishments|achievements|certifications|interests|additional))',
        r'(?:^|\n)\s*key\s+skills\s+(.*?)(?=\n\s*(?:experience|education|accomplishments|achievements|certifications|interests|additional))',
        r'(?:^|\n)\s*summary\s+of\s+skills\s+(.*?)(?=\n\s*(?:experience|education|accomplishments|achievements|certifications|interests|additional))',       
       
        # Skills section that appears at the end of document (after experience/education)
        r'(?:^|\n)\s*skills\s+(.*?)(?=\n\s*(?:accomplishments|achievements|certifications|interests|additional|$))',
        r'(?:^|\n)\s*technical\s+skills\s+(.*?)(?=\n\s*(?:accomplishments|achievements|certifications|interests|additional|$))',
        r'(?:^|\n)\s*professional\s+skills\s+(.*?)(?=\n\s*(?:accomplishments|achievements|certifications|interests|additional|$))',
        r'(?:^|\n)\s*key\s+skills\s+(.*?)(?=\n\s*(?:accomplishments|achievements|certifications|interests|additional|$))',
        r'(?:^|\n)\s*summary\s+of\s+skills\s+(.*?)(?=\n\s*(?:accomplishments|achievements|certifications|interests|additional|$))',
        
        # Skills section at very end of document (no following sections)
        r'(?:^|\n)\s*skills\s+(.*?)$',
        r'(?:^|\n)\s*technical\s+skills\s+(.*?)$',
        r'(?:^|\n)\s*professional\s+skills\s+(.*?)$'
        r'(?:^|\n)\s*key\s+skills\s+(.*?)$',
        r'(?:^|\n)\s*summary\s+of\s+skills\s+(.*?)$'
    ]
    
    for pattern in skills_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            start, end = match.start(1), match.end(1)
            sections['skills'] = normalized_text[start:end].strip()
            break
    
    # EXPERIENCE with improved patterns
    experience_patterns = [
        r'(?:^|\n)\s*experience\s+(.*?)(?=\n\s*(?:education|accomplishments|achievements|certifications|interests|additional|skills))',
        r'(?:^|\n)\s*work\s+experience\s+(.*?)(?=\n\s*(?:education|accomplishments|achievements|certifications|interests|additional|skills))',
        r'(?:^|\n)\s*employment\s+history\s+(.*?)(?=\n\s*(?:education|accomplishments|achievements|certifications|interests|additional|skills))',
        r'(?:^|\n)\s*professional\s+experience\s+(.*?)(?=\n\s*(?:education|accomplishments|achievements|certifications|interests|additional|skills))',
        r'(?:^|\n)\s*affiliations\s+(.*?)(?=\n\s*(?:education|accomplishments|achievements|certifications|interests|additional|skills))',
        r'(?:^|\n)\s*work\s+history\s+(.*?)(?=\n\s*(?:education|accomplishments|achievements|certifications|interests|additional|skills))'
    ]
    
    for pattern in experience_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            start, end = match.start(1), match.end(1)
            exp_text = normalized_text[start:end].strip()
            exp_text = re.sub(r'company\s*name', 'Company Name', exp_text, flags=re.IGNORECASE)
            exp_text = re.sub(r'city\s*,\s*state', 'City, State', exp_text, flags=re.IGNORECASE)
            sections['experience'] = exp_text
            break
    
    # EDUCATION with improved patterns
    education_patterns = [
        r'(?:^|\n)\s*education\s+(.*?)(?=\n\s*(?:accomplishments|achievements|certifications|interests|additional|skills))',
        r'(?:^|\n)\s*academic\s+background\s+(.*?)(?=\n\s*(?:accomplishments|achievements|certifications|interests|additional|skills))',
        r'(?:^|\n)\s*qualifications\s+(.*?)(?=\n\s*(?:accomplishments|achievements|certifications|interests|additional|skills))',
        r'(?:^|\n)\s*education\s+and\s+training\s+(.*?)(?=\n\s*(?:accomplishments|achievements|certifications|interests|additional|skills))',
        r'(?:^|\n)\s*academic\s+qualifications\s+(.*?)(?=\n\s*(?:accomplishments|achievements|certifications|interests|additional|skills))',
    ]
    
    for pattern in education_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            start, end = match.start(1), match.end(1)
            edu_text = normalized_text[start:end].strip()
            sections['education'] = edu_text
            break
    
    # ACCOMPLISHMENTS with improved patterns
    accomplishments_patterns = [
        r'(?:^|\n)\s*accomplishments\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*achievements\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*key\s+achievements\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*certifications\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*certifications\s+and\s+training\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*certificates\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*professional\s+certifications\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*licenses\s+and\s+certifications\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*awards\s+and\s+certifications\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*qualifications\s+and\s+certifications\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*licenses\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*awards\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))',
        r'(?:^|\n)\s*honors\s+(.*?)(?=\n\s*(?:experience|education|interests|additional|skills))'
    ]
    
    for pattern in accomplishments_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            start, end = match.start(1), match.end(1)
            sections['accomplishments'] = normalized_text[start:end].strip()
            break
    
    return sections

def insert_applicant_profile(profile_data, encrypt_data=False):
    if encrypt_data:
        # Encrypt sensitive personal data
        first_name = encryption_manager.encrypt_text(profile_data['first_name'])
        last_name = encryption_manager.encrypt_text(profile_data['last_name'])
        date_of_birth = encryption_manager.encrypt_text(profile_data['date_of_birth'])
        address = encryption_manager.encrypt_text(profile_data['address'])
        phone_number = encryption_manager.encrypt_text(profile_data['phone_number'])
    else:
        first_name = profile_data['first_name']
        last_name = profile_data['last_name']
        date_of_birth = profile_data['date_of_birth']
        address = profile_data['address']
        phone_number = profile_data['phone_number']
    
    cursor.execute("""
        INSERT INTO ApplicantProfile (first_name, last_name, date_of_birth, address, phone_number, is_encrypted)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        first_name,
        last_name,
        date_of_birth,
        address,
        phone_number,
        encrypt_data
    ))
    return cursor.lastrowid

def insert_application_detail(applicant_id, cv_path, cv_text, sections, encrypt_data=False):
    role = extract_application_role(cv_text, cv_path)
    
    if encrypt_data:
        # Encrypt CV content and sections
        cv_raw_text = encryption_manager.encrypt_text(cv_text)
        summary_section = encryption_manager.encrypt_text(sections['summary'])
        skills_section = encryption_manager.encrypt_text(sections['skills'])
        experience_section = encryption_manager.encrypt_text(sections['experience'])
        education_section = encryption_manager.encrypt_text(sections['education'])
        accomplishments_section = encryption_manager.encrypt_text(sections['accomplishments'])
        application_role = encryption_manager.encrypt_text(role)
    else:
        cv_raw_text = cv_text
        summary_section = sections['summary']
        skills_section = sections['skills']
        experience_section = sections['experience']
        education_section = sections['education']
        accomplishments_section = sections['accomplishments']
        application_role = role
    
    cursor.execute("""
        INSERT INTO ApplicationDetail 
        (applicant_id, application_role, cv_path, cv_raw_text, summary_section, 
         skills_section, experience_section, education_section, accomplishments_section, is_encrypted)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        applicant_id,
        application_role,
        cv_path,
        cv_raw_text,
        summary_section,
        skills_section,
        experience_section,
        education_section,
        accomplishments_section,
        encrypt_data
    ))

def extract_application_role(cv_text, cv_path):
    path_parts = cv_path.replace('\\', '/').split('/')
    for part in path_parts:
        part_upper = part.upper()
        if part_upper in ['ACCOUNTANT', 'ADVOCATE', 'AGRICULTURE', 'APPAREL', 'ARTS', 
                         'AUTOMOBILE', 'AVIATION', 'BANKING', 'BPO', 'BUSINESS-DEVELOPMENT',
                         'CHEF', 'CONSTRUCTION', 'CONSULTANT', 'DESIGNER', 'DIGITAL-MEDIA',
                         'ENGINEERING', 'FINANCE', 'FITNESS', 'HEALTHCARE', 'HR',
                         'INFORMATION-TECHNOLOGY', 'PUBLIC-RELATIONS', 'SALES', 'TEACHER']:
            return part_upper.replace('-', ' ').title()
    
    lines = cv_text.split('\n')
    for i, line in enumerate(lines[:5]): 
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 3:
            continue

        if line_clean.isupper() and len(line_clean.split()) <= 3:
            continue
            
        if re.search(r'(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})|(@)|(\d{5})', line_clean):
            continue
            
        role_keywords = [
            'chef', 'cook', 'accountant', 'engineer', 'developer', 'manager', 'analyst',
            'designer', 'consultant', 'specialist', 'coordinator', 'assistant', 'director',
            'supervisor', 'lead', 'senior', 'junior', 'associate', 'executive', 'officer',
            'technician', 'administrator', 'representative', 'advisor', 'instructor',
            'teacher', 'professor', 'nurse', 'doctor', 'therapist', 'lawyer', 'advocate'
        ]
        
        line_lower = line_clean.lower()
        for keyword in role_keywords:
            if keyword in line_lower:
                return line_clean.title()[:100]
    
    cv_lower = cv_text.lower()
    role_patterns = [
        r'(?:job title|position|role|objective):\s*([^\n]+)',
        r'(?:seeking|looking for|applying for)\s+(?:position as|role as|job as)?\s*([^\n]+)',
        r'(?:current role|current position):\s*([^\n]+)',
    ]
    
    for pattern in role_patterns:
        match = re.search(pattern, cv_lower)
        if match:
            role_text = match.group(1).strip()
            if len(role_text) > 5:  
                return role_text.title()[:100]
    
    content_role_map = {
        'chef': ['chef', 'cook', 'culinary', 'kitchen', 'food prep', 'restaurant'],
        'developer': ['developer', 'programming', 'coding', 'software', 'python', 'java', 'javascript'],
        'accountant': ['accounting', 'bookkeeping', 'financial', 'tax', 'audit'],
        'engineer': ['engineering', 'technical', 'system', 'design', 'development'],
        'designer': ['design', 'creative', 'graphic', 'ui', 'ux', 'visual'],
        'teacher': ['teaching', 'education', 'instructor', 'academic', 'student'],
        'nurse': ['nursing', 'healthcare', 'medical', 'patient care', 'hospital'],
        'sales': ['sales', 'selling', 'customer', 'revenue', 'target']
    }
    
    for role, keywords in content_role_map.items():
        if any(keyword in cv_lower for keyword in keywords):
            return role.title()
    
    return 'General Application'

def setup_encryption():
    """Setup encryption based on user choice."""
    print("\n=== ENCRYPTION SETUP ===")
    print("Choose encryption option:")
    print("1. No encryption (default)")
    print("2. Encrypt with auto-generated key")
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        print("Proceeding without encryption")
        save_encryption_config(False, False)
        return False
    elif choice == "2":
        # Initialize encryption with auto-generated key
        if encryption_manager.initialize_encryption():
            save_encryption_config(True, False)
            print("Encryption setup completed successfully!")
            return True
        else:
            print("Encryption setup failed. Proceeding without encryption.")
            save_encryption_config(False, False)
            return False
    else:
        print("Invalid choice. Proceeding without encryption.")
        save_encryption_config(False, False)
        return False

def process_folder(base_folder, use_encryption=False):
    pdf_files = glob.glob(os.path.join(base_folder, "**/*.pdf"), recursive=True)
    
    if not pdf_files:
        print("No PDF file found in data and its subfiles")
        return
    
    total_files = len(pdf_files)
    print(f"Found {total_files} PDF files to process")
    
    if use_encryption:
        print("Processing with ENCRYPTION enabled")
    else:
        print("Processing WITHOUT encryption")
    
    # create base profiles for one-to-many
    base_profiles = []
    profile_percentage = random.uniform(0.40, 0.50)
    num_base_profiles = max(50, int(total_files * profile_percentage)) 
    
    print(f"Creating {num_base_profiles} base profiles")
    
    for i in range(num_base_profiles):
        profile_data = generate_fake_profile()
        applicant_id = insert_applicant_profile(profile_data, use_encryption)
        base_profiles.append({
            'id': applicant_id,
            'application_count': 0
        })
        
        if (i + 1) % 50 == 0:
            print(f"Created {i + 1} profiles...")
    
    db.commit()
    
    # verify profile count
    cursor.execute("SELECT COUNT(*) FROM ApplicantProfile")
    profile_count_after_creation = cursor.fetchone()[0]
    print(f"Verified: {profile_count_after_creation} profiles in database")
    
    if profile_count_after_creation != num_base_profiles:
        print(f"ERROR: Expected {num_base_profiles} but found {profile_count_after_creation}")
        return
    
    # process pdfs - NEVER create new profiles
    processed = 0
    failed = 0
    
    print("Starting PDF processing...")
    
    for i, path in enumerate(pdf_files):
        try:
            if i % 100 == 0:
                print(f"Processing file {i+1}/{total_files}")
            
            cv_text = extract_text_from_pdf(path)
            if not cv_text or len(cv_text) < 50:
                failed += 1
                continue
                
            sections = extract_cv_sections(cv_text)
            
            # ONLY use existing profiles
            selected_profile = min(base_profiles, key=lambda p: p['application_count'])
            applicant_id = selected_profile['id']
            selected_profile['application_count'] += 1
            
            insert_application_detail(applicant_id, path, cv_text, sections, use_encryption)
            processed += 1
            
            # check if profiles are being created somehow
            if processed % 100 == 0:
                cursor.execute("SELECT COUNT(*) FROM ApplicantProfile")
                current_profile_count = cursor.fetchone()[0]
                if current_profile_count != num_base_profiles:
                    print(f"ALERT: Profile count changed to {current_profile_count}!")
                    break
                db.commit()
            
        except Exception as e:
            print(f"Error processing {path}: {e}")
            failed += 1
            continue
    
    db.commit()
    
    # final statistics
    cursor.execute("SELECT COUNT(DISTINCT applicant_id) FROM ApplicationDetail")
    unique_profiles = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ApplicationDetail")
    total_applications = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ApplicantProfile")
    total_profiles_in_table = cursor.fetchone()[0]
    
    print(f"\nProcessing completed")
    print(f"Successfully processed: {processed}")
    print(f"Failed: {failed}")
    print(f"Profiles in ApplicantProfile table: {total_profiles_in_table}")
    print(f"Unique profiles used in applications: {unique_profiles}")
    print(f"Total applications: {total_applications}")
    print(f"Encryption used: {'YES' if use_encryption else 'NO'}")
    
    if total_profiles_in_table != num_base_profiles:
        print(f"ERROR: Something created extra profiles! Expected {num_base_profiles}")
    
    if unique_profiles != num_base_profiles:
        print(f"ERROR: Not all profiles were used! Expected {num_base_profiles}")
    
    print(f"Average applications per profile: {total_applications/unique_profiles:.2f}")

def export_data_to_sql(filename):
    try:
        cursor.execute("SELECT * FROM ApplicantProfile ORDER BY applicant_id")
        profiles = cursor.fetchall()
        
        cursor.execute("SELECT * FROM ApplicationDetail ORDER BY detail_id")
        details = cursor.fetchall()
        
        def escape_sql(val):
            if val is None:
                return "NULL"
            return "'" + str(val).replace("'", "''").replace("\\", "\\\\") + "'"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};\n")
            f.write(f"USE {DB_NAME};\n\n")
            
            f.write("-- Create ApplicantProfile table\n")
            f.write(create_applicant_profile_table.strip() + ";\n\n")
            f.write("-- Create ApplicationDetail table\n")
            f.write(create_application_detail_table.strip() + ";\n\n")
            
            f.write("-- Insert ApplicantProfile data\n")
            for i, profile in enumerate(profiles, 1):  # start from 1
                original_id, first_name, last_name, dob, address, phone, is_encrypted = profile
                dob_val = escape_sql(dob if dob else None)
                
                # use sequential IDs starting from 1
                insert_stmt = (
                    "INSERT INTO ApplicantProfile (applicant_id, first_name, last_name, date_of_birth, address, phone_number, is_encrypted) VALUES ("
                    f"{i}, {escape_sql(first_name)}, {escape_sql(last_name)}, {dob_val}, "
                    f"{escape_sql(address)}, {escape_sql(phone)}, {is_encrypted});\n"
                )
                f.write(insert_stmt)
            
            f.write("\n-- Insert ApplicationDetail data\n")
            
            # create mapping from old IDs to new IDs to maintain relationships
            id_mapping = {}
            for i, profile in enumerate(profiles, 1):
                original_id = profile[0]
                id_mapping[original_id] = i
            
            for i, detail in enumerate(details, 1):  # start from 1
                detail_id, original_applicant_id, role, cv_path, cv_raw_text, summary, skills, experience, education, accomplishments, is_encrypted = detail
                new_applicant_id = id_mapping[original_applicant_id]  # maintain one-to-many relationships
                
                insert_stmt = (
                    "INSERT INTO ApplicationDetail (detail_id, applicant_id, application_role, cv_path, cv_raw_text, "
                    "summary_section, skills_section, experience_section, education_section, accomplishments_section, is_encrypted) VALUES ("
                    f"{i}, {new_applicant_id}, {escape_sql(role)}, {escape_sql(cv_path)}, {escape_sql(cv_raw_text)}, "
                    f"{escape_sql(summary)}, {escape_sql(skills)}, {escape_sql(experience)}, "
                    f"{escape_sql(education)}, {escape_sql(accomplishments)}, {is_encrypted});\n"
                )
                f.write(insert_stmt)
        
        print(f"Data exported successfully to: {filename}")
        
    except Exception as e:
        print(f"Error while exporting data: {e}")

def test_extraction(pdf_path):
    print(f"Testing extraction on: {pdf_path}")
    cv_text = extract_text_from_pdf(pdf_path)
    sections = extract_cv_sections(cv_text)
    
    print("\n=== RESULT ===")
    for section_name, content in sections.items():
        print(f"\n{section_name.upper()}:")
        print("-" * 40)
        if content:
            print(content[:200] + "..." if len(content) > 200 else content)
        else:
            print("(Not found)")

if __name__ == "__main__":
    # Check for existing encryption configuration
    config = load_encryption_config()
    use_encryption = False
    
    if config.get("encryption_enabled"):
        print("Existing encryption configuration found.")
        
        # Try to load existing encryption
        password = None
        if config.get("password_protected"):
            password = getpass.getpass("Enter encryption password: ")
        
        if encryption_manager.initialize_encryption(password):
            use_encryption = True
            print("Encryption loaded successfully!")
        else:
            print("Failed to load encryption. Proceeding without encryption.")
            use_encryption = False
    else:
        # Setup new encryption
        use_encryption = setup_encryption()
    
    # CLEAR DATABASE FIRST
    print("Clearing existing data...")
    cursor.execute("DELETE FROM ApplicationDetail")
    cursor.execute("DELETE FROM ApplicantProfile")
    cursor.execute("ALTER TABLE ApplicantProfile AUTO_INCREMENT = 1")
    cursor.execute("ALTER TABLE ApplicationDetail AUTO_INCREMENT = 1")
    db.commit()
    print("Database cleared and AUTO_INCREMENT reset")
    
    # Uncomment to test single file extraction
    # test_extraction("../../data/CHEF/10276858.pdf")
    
    # Process all PDFs
    process_folder("../../data", use_encryption)
    
    # Export to SQL file
    export_filename = "../../data/ats_encrypted.sql" if use_encryption else "../../data/ats.sql"
    export_data_to_sql(export_filename)
    
    print(f"\n=== EXTRACTION COMPLETED ===")
    print(f"Database: {DB_NAME}")
    print(f"Encryption: {'ENABLED' if use_encryption else 'DISABLED'}")
    print(f"Export file: {export_filename}")
    
    if use_encryption:
        print(f"\nEncryption files:")
        print(f"  Key file: {ENCRYPTION_KEY_FILE}")
        print(f"  Config file: {ENCRYPTION_CONFIG_FILE}")
        print("\nIMPORTANT: Keep these files safe! They are required to decrypt your data.")
    
    cursor.close()
    db.close()