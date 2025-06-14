import os
import glob
import re
from faker import Faker
import fitz 
import mysql.connector
import getpass 
import random
import base64
import json
import os
import sys
import time

DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "ats_db"

DB_PASSWORD = ""

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
        DB_PASSWORD = ""  
        print("MySQL connection successful with no password")
        return DB_PASSWORD
    except mysql.connector.Error:
        pass
    
    print("MySQL requires a password")
    DB_PASSWORD = getpass.getpass("Enter MySQL Password: ")
    
    try:
        test_conn = mysql.connector.connect(
            host=DB_HOST, 
            user=DB_USER, 
            password=DB_PASSWORD
        )
        test_conn.close()
        print("Password verified successfully")
        return DB_PASSWORD
    except mysql.connector.Error as e:
        print(f"Password verification failed: {e}")
        DB_PASSWORD = "" 
        return None

ENCRYPTION_KEY_FILE = "ats_encryption.key"
ENCRYPTION_CONFIG_FILE = "ats_config.json"

class SecureEncryption:
    """Fixed custom encryption using only built-in Python functions"""
    
    def __init__(self, key: bytes):
        self.key = key
        # Create multiple derived keys from the main key
        self.key1 = self._derive_key(key, 1)
        self.key2 = self._derive_key(key, 2)
        self.key3 = self._derive_key(key, 3)
    
    def _derive_key(self, key: bytes, salt: int) -> bytes:
        """Derive a key using simple mathematical operations"""
        derived = bytearray()
        for i, byte in enumerate(key):
            # Use modular arithmetic and bit operations for key derivation
            new_byte = ((byte ^ salt) + i) % 256
            new_byte = ((new_byte << 1) | (new_byte >> 7)) & 0xFF  # Rotate bits
            derived.append(new_byte)
        return bytes(derived)
    
    def _expand_key(self, target_length: int, base_key: bytes) -> bytes:
        """Expand key to match data length"""
        if target_length <= len(base_key):
            return base_key[:target_length]
        
        expanded = bytearray()
        key_pos = 0
        
        for i in range(target_length):
            # Use multiple keys and position for expansion
            byte1 = base_key[key_pos % len(base_key)]
            byte2 = self.key1[key_pos % len(self.key1)]
            byte3 = self.key2[key_pos % len(self.key2)]
            
            # Combine bytes using XOR and arithmetic
            combined = (byte1 ^ byte2 ^ byte3 ^ (i % 256)) % 256
            expanded.append(combined)
            key_pos += 1
        
        return bytes(expanded)
    
    def _substitute_bytes(self, data: bytes, encrypt: bool = True) -> bytes:
        """Apply substitution cipher - FIXED VERSION"""
        result = bytearray()
        
        for i, byte in enumerate(data):
            # Use position and key for substitution
            key_byte = self.key3[i % len(self.key3)]
            
            if encrypt:
                # Forward substitution
                new_byte = (byte + key_byte + i) % 256
                new_byte = ((new_byte << 3) | (new_byte >> 5)) & 0xFF  # Rotate
            else:
                # Reverse substitution - FIXED: Apply operations in reverse order
                byte = ((byte >> 3) | (byte << 5)) & 0xFF  # Reverse rotate first
                new_byte = (byte - key_byte - i) % 256
            
            result.append(new_byte)
        
        return bytes(result)
    
    def _permute_bytes(self, data: bytes, encrypt: bool = True) -> bytes:
        """Apply byte permutation based on key - SIMPLIFIED VERSION"""
        if len(data) < 4:
            return data
        
        # Create permutation pattern from key
        key_sum = sum(self.key) % 256
        block_size = 8  # Fixed block size for consistency
        
        result = bytearray()
        
        for block_start in range(0, len(data), block_size):
            block = data[block_start:block_start + block_size]
            
            if len(block) < 4:  # Don't permute small blocks
                result.extend(block)
                continue
            
            # Create simple permutation based on key
            perm_key = (key_sum + block_start) % len(block)
            
            if encrypt:
                # Simple rotation permutation
                permuted = block[perm_key:] + block[:perm_key]
            else:
                # Reverse rotation
                reverse_key = len(block) - perm_key
                permuted = block[reverse_key:] + block[:reverse_key]
            
            result.extend(permuted)
        
        return bytes(result)
    
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data using multiple layers"""
        if not data:
            return data
        
        # Layer 1: XOR with expanded key
        expanded_key = self._expand_key(len(data), self.key)
        layer1 = bytes(a ^ b for a, b in zip(data, expanded_key))
        
        # Layer 2: Substitution
        layer2 = self._substitute_bytes(layer1, encrypt=True)
        
        # Layer 3: Permutation
        layer3 = self._permute_bytes(layer2, encrypt=True)
        
        # Layer 4: Final XOR with different key
        final_key = self._expand_key(len(layer3), self.key2)
        result = bytes(a ^ b for a, b in zip(layer3, final_key))
        
        return result
    
    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data by reversing encryption layers"""
        if not data:
            return data
        
        # Reverse Layer 4: XOR with different key
        final_key = self._expand_key(len(data), self.key2)
        layer3 = bytes(a ^ b for a, b in zip(data, final_key))
        
        # Reverse Layer 3: Permutation
        layer2 = self._permute_bytes(layer3, encrypt=False)
        
        # Reverse Layer 2: Substitution
        layer1 = self._substitute_bytes(layer2, encrypt=False)
        
        # Reverse Layer 1: XOR with expanded key
        expanded_key = self._expand_key(len(layer1), self.key)
        result = bytes(a ^ b for a, b in zip(layer1, expanded_key))
        
        return result
    
class EncryptionManager:
    def __init__(self):
        self.key = None
        self.cipher = None
        self.encryption_enabled = False
    
    def generate_key(self) -> bytes:
        """Generate a secure 32-byte key using multiple entropy sources"""
        # Use system entropy and time-based randomness
        entropy1 = os.urandom(16)
        
        # Time-based entropy
        current_time = int(time.time() * 1000000)  # microseconds
        time_bytes = current_time.to_bytes(8, 'big')
        
        # Random number entropy
        random.seed()  # Use system time as seed
        random_nums = [random.randint(0, 255) for _ in range(8)]
        random_bytes = bytes(random_nums)
        
        # Combine entropy sources
        combined = entropy1 + time_bytes + random_bytes
        
        # Simple key derivation - mix the bytes
        final_key = bytearray(32)
        for i in range(32):
            # Combine multiple bytes with different operations
            byte1 = combined[i % len(combined)]
            byte2 = combined[(i * 3) % len(combined)]
            byte3 = combined[(i * 7) % len(combined)]
            
            final_key[i] = (byte1 ^ byte2 ^ byte3 ^ i) % 256
        
        return bytes(final_key)
    
    def _password_to_key(self, password: str) -> bytes:
        """Convert password to 32-byte key"""
        if not password:
            return b'\x00' * 32
        
        # Simple password-based key derivation
        password_bytes = password.encode('utf-8')
        salt = b'ats_simple_salt_2024'  # Fixed salt for consistency
        
        # Extend password to at least 32 bytes
        extended_password = (password_bytes + salt) * ((32 // len(password_bytes + salt)) + 1)
        extended_password = extended_password[:32]
        
        # Apply transformations
        key = bytearray(32)
        for i in range(32):
            # Multiple rounds of transformation
            byte_val = extended_password[i]
            for round_num in range(1000):  # 1000 rounds for strength
                byte_val = ((byte_val ^ (round_num % 256)) + i) % 256
                byte_val = ((byte_val << 1) | (byte_val >> 7)) & 0xFF  # Bit rotation
            key[i] = byte_val
        
        return bytes(key)
    
    def save_key(self, key: bytes, password: str = None):
        if password:
            # Encrypt key with password
            password_key = self._password_to_key(password)
            password_cipher = SecureEncryption(password_key)
            encrypted_key = password_cipher.encrypt(key)
            
            # Add simple checksum (sum of original key bytes)
            checksum = sum(key) % 65536  # 2-byte checksum
            checksum_bytes = checksum.to_bytes(2, 'big')
            
            final_data = encrypted_key + checksum_bytes
            
            with open(ENCRYPTION_KEY_FILE, 'wb') as f:
                f.write(final_data)
        else:
            with open(ENCRYPTION_KEY_FILE, 'wb') as f:
                f.write(key)
        
        print(f"Encryption key saved to {ENCRYPTION_KEY_FILE}")
    
    def load_key(self, password: str = None) -> bytes:
        if not os.path.exists(ENCRYPTION_KEY_FILE):
            return None
        
        with open(ENCRYPTION_KEY_FILE, 'rb') as f:
            key_data = f.read()
        
        if password:
            try:
                if len(key_data) < 34:  # 32 bytes key + 2 bytes checksum minimum
                    print("Invalid key file format")
                    return None
                
                encrypted_key = key_data[:-2]
                stored_checksum = int.from_bytes(key_data[-2:], 'big')
                
                # Decrypt the key
                password_key = self._password_to_key(password)
                password_cipher = SecureEncryption(password_key)
                decrypted_key = password_cipher.decrypt(encrypted_key)
                
                # Verify checksum
                calculated_checksum = sum(decrypted_key) % 65536
                if calculated_checksum != stored_checksum:
                    print("Key integrity check failed - wrong password or corrupted file")
                    return None
                
                return decrypted_key
                
            except Exception as e:
                print(f"Failed to decrypt key with password: {e}")
                return None
        else:
            return key_data
    
    def initialize_encryption(self, password: str = None) -> bool:
        key = self.load_key(password)
        
        if not key:
            key = self.generate_key()
            self.save_key(key, password)
            print("Generated new encryption key")
        else:
            print("Loaded existing encryption key")
        
        self.key = key
        self.cipher = SecureEncryption(key)
        self.encryption_enabled = True
        return True
    
    def encrypt_text(self, text: str) -> str:
        if not self.encryption_enabled or not text:
            return text
        
        # Add magic header to identify encrypted data
        text_bytes = text.encode('utf-8')
        full_data = text_bytes
        
        encrypted_data = self.cipher.encrypt(full_data)
        return base64.b64encode(encrypted_data).decode('utf-8')
        
    def decrypt_text(self, encrypted_text: str) -> str:
        """Improved decrypt_text with better error handling"""
        if not self.encryption_enabled or not encrypted_text:
            return encrypted_text
        
        try:
            # Try to decode as base64
            try:
                encrypted_data = base64.b64decode(encrypted_text.encode('utf-8'))
            except Exception as e:
                print(f"Base64 decode failed: {e}")
                return encrypted_text
            
            # Decrypt the data
            try:
                decrypted_data = self.cipher.decrypt(encrypted_data)
            except Exception as e:
                print(f"Cipher decryption failed: {e}")
                return encrypted_text
                    
            # Remove magic header and decode
            text_bytes = decrypted_data
            try:
                return text_bytes.decode('utf-8')
            except UnicodeDecodeError as e:
                print(f"UTF-8 decode failed: {e}")
                # Try with error handling
                try:
                    return text_bytes.decode('utf-8', errors='replace')
                except:
                    print("All decoding attempts failed")
                    return encrypted_text
                    
        except Exception as e:
            print(f"General decryption failed: {e}")
            return encrypted_text


    def is_encrypted_data(self, text: str) -> bool:
        if not text or len(text) < 16:
            return False
        
        try:
            # Try to decode as base64
            decoded = base64.b64decode(text.encode('utf-8'))
            return len(decoded) > 16  # Minimum size for encrypted data
        except:
            return False

def save_encryption_config(encryption_enabled: bool, password_protected: bool = False):
    config = {
        "encryption_enabled": encryption_enabled,
        "password_protected": password_protected,
        "version": "1.0"
    }
    
    with open(ENCRYPTION_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_encryption_config() -> dict:
    if not os.path.exists(ENCRYPTION_CONFIG_FILE):
        return {"encryption_enabled": False, "password_protected": False}
    
    try:
        with open(ENCRYPTION_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"encryption_enabled": False, "password_protected": False}

encryption_manager = EncryptionManager()

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

def get_database_connection():
    password = get_mysql_password()
    if password is None:
        raise Exception("Failed to get valid MySQL password")
    
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=password,
        database=DB_NAME
    )

def initialize_database():
    db = get_database_connection()
    cursor = db.cursor()
    
    cursor.execute(create_applicant_profile_table)
    cursor.execute(create_application_detail_table)
    db.commit()
    
    cursor.close()
    db.close()

faker = Faker('id_ID')

def generate_phone():
    return "08" + ''.join(faker.random_choices(elements='0123456789', length=10))

def generate_fake_profile():
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

            blocks = page.get_text("blocks")
            page_lines = []
            
            blocks.sort(key=lambda block: (block[1], block[0])) 
            
            for block in blocks:
                if len(block) >= 5: 
                    text = block[4].strip()
                    if text:
                        lines = text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line:
                                page_lines.append(line)
            
            if len(page_lines) < 5:
                simple_text = page.get_text().strip()
                if simple_text:
                    page_lines = [line.strip() for line in simple_text.split('\n') if line.strip()]
            
            if page_lines:
                full_text.extend(page_lines)
        
        doc.close()
        
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

def clean_sections(sections):
    for section_name, content in sections.items():
        if not content:
            continue
            
        for other_section, other_content in sections.items():
            if other_section == section_name or not other_content:
                continue
    
    for section_name in sections:
        content = sections[section_name]
        if content:
            content = re.sub(r'\n\s*\n', '\n', content)
            content = content.strip()
            sections[section_name] = content
    
    return sections

def find_section_boundaries(lines):
    boundaries = []
    
    for i, line in enumerate(lines):
        line_clean = line.strip().lower()
        if not line_clean or len(line_clean) > 100:
            continue
        
        if (len(line.strip()) < 50 and 
            re.match(r'^[a-z\s]+$', line_clean) and  
            any(section in line_clean for section in ['summary', 'skills', 'experience', 'education', 'accomplishments'])):
            boundaries.append((i, line_clean))
    
    return boundaries

def insert_applicant_profile(profile_data, encrypt_data=False):
    db = get_database_connection()
    cursor = db.cursor()
    
    if encrypt_data:
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
    
    result = cursor.lastrowid
    db.commit()
    cursor.close()
    db.close()
    return result

def insert_application_detail(applicant_id, cv_path, cv_text, sections, encrypt_data=False):
    db = get_database_connection()
    cursor = db.cursor()
    
    role = extract_application_role(cv_text, cv_path)
    
    if encrypt_data:
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
    
    db.commit()
    cursor.close()
    db.close()

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
    
    initialize_database()
    
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
    
    print(f"Verified: {len(base_profiles)} profiles created")
    
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
            
            selected_profile = min(base_profiles, key=lambda p: p['application_count'])
            applicant_id = selected_profile['id']
            selected_profile['application_count'] += 1
            
            insert_application_detail(applicant_id, path, cv_text, sections, use_encryption)
            processed += 1
            
        except Exception as e:
            print(f"Error processing {path}: {e}")
            failed += 1
            continue
    
    print(f"\nProcessing completed")
    print(f"Successfully processed: {processed}")
    print(f"Failed: {failed}")
    print(f"Encryption used: {'YES' if use_encryption else 'NO'}")

def export_data_to_sql(filename):
    db = get_database_connection()
    cursor = db.cursor()
    
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
                
                insert_stmt = (
                    "INSERT INTO ApplicantProfile (applicant_id, first_name, last_name, date_of_birth, address, phone_number, is_encrypted) VALUES ("
                    f"{i}, {escape_sql(first_name)}, {escape_sql(last_name)}, {dob_val}, "
                    f"{escape_sql(address)}, {escape_sql(phone)}, {is_encrypted});\n"
                )
                f.write(insert_stmt)
            
            f.write("\n-- Insert ApplicationDetail data\n")
            
            id_mapping = {}
            for i, profile in enumerate(profiles, 1):
                original_id = profile[0]
                id_mapping[original_id] = i
            
            for i, detail in enumerate(details, 1):  # start from 1
                detail_id, original_applicant_id, role, cv_path, cv_raw_text, summary, skills, experience, education, accomplishments, is_encrypted = detail
                new_applicant_id = id_mapping[original_applicant_id]
                
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
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    config = load_encryption_config()
    use_encryption = False
    
    if config.get("encryption_enabled"):
        print("Existing encryption configuration found.")
        
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
        use_encryption = setup_encryption()
    
    password = get_mysql_password()
    if password is None:
        print("Failed to get MySQL password. Exiting.")
        exit(1)
    
    print("Clearing existing data...")
    db = get_database_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM ApplicationDetail")
    cursor.execute("DELETE FROM ApplicantProfile")
    cursor.execute("ALTER TABLE ApplicantProfile AUTO_INCREMENT = 1")
    cursor.execute("ALTER TABLE ApplicationDetail AUTO_INCREMENT = 1")
    db.commit()
    cursor.close()
    db.close()
    print("Database cleared and AUTO_INCREMENT reset")
    
    process_folder("../../data", use_encryption)
    
    export_filename = "../../data/ats_encrypted.sql" if use_encryption else "../../data/ats.sql"
    export_data_to_sql(export_filename)
    
    print(f"\n=== EXTRACTION COMPLETED ===")
    print(f"Database: {DB_NAME}")
    print(f"Encryption: {'enabled' if use_encryption else 'disabled'}")
    print(f"Export file: {export_filename}")
    
    if use_encryption:
        print(f"\nEncryption files:")
        print(f"  Key file: {ENCRYPTION_KEY_FILE}")
        print(f"  Config file: {ENCRYPTION_CONFIG_FILE}")
        print("\nIMPORTANT: Keep these files safe! They are required to decrypt your data.")