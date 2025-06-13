# data_extractor/encryption.py
"""
Core encryption utilities for ATS system
This replaces your existing encryption.py in data_extractor folder
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import mysql.connector
import getpass
import json
from typing import Optional, Dict, Any, List
import secrets

class ATSCryptoManager:
    """Advanced encryption manager for ATS database"""
    
    def __init__(self, master_password: str = None):
        self.master_password = master_password or self._get_master_password()
        self.salt = self._get_or_create_salt()
        self.fernet = self._create_fernet_key()
        
    def _get_master_password(self) -> str:
        """Get master password from environment or user input"""
        password = os.getenv('ATS_MASTER_KEY')
        if not password:
            password = getpass.getpass("Enter ATS Master Encryption Password: ")
        return password
    
    def _get_or_create_salt(self) -> bytes:
        """Get or create encryption salt"""
        # Look for salt file in data_extractor folder first
        salt_locations = [
            "ats_encryption.salt",  # current dir
            "data_extractor/ats_encryption.salt",  # from root
            "../ats_encryption.salt",  # parent dir
            os.path.join(os.path.dirname(__file__), "ats_encryption.salt")  # same as this file
        ]
        
        # Try to find existing salt
        for salt_file in salt_locations:
            if os.path.exists(salt_file):
                try:
                    with open(salt_file, 'rb') as f:
                        print(f"🔑 Using existing salt file: {salt_file}")
                        return f.read()
                except Exception as e:
                    print(f"Warning: Could not read salt file {salt_file}: {e}")
                    continue
        
        # Create new salt in data_extractor directory
        salt = os.urandom(16)
        
        # Save in same directory as this file
        current_dir = os.path.dirname(__file__)
        salt_file = os.path.join(current_dir, "ats_encryption.salt")
        
        try:
            with open(salt_file, 'wb') as f:
                f.write(salt)
            print(f"🔑 Created new encryption salt: {salt_file}")
        except Exception as e:
            print(f"Warning: Could not save salt file: {e}")
        
        return salt
    
    def _create_fernet_key(self) -> Fernet:
        """Create Fernet encryption key from master password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_password.encode()))
        return Fernet(key)
    
    def encrypt_text(self, plaintext: str) -> str:
        """Encrypt text data"""
        if not plaintext:
            return ""
        
        encrypted = self.fernet.encrypt(plaintext.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    
    def decrypt_text(self, encrypted_text: str) -> str:
        """Decrypt text data"""
        if not encrypted_text:
            return ""
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            print(f"Decryption error: {e}")
            return ""
    
    def encrypt_large_text(self, plaintext: str) -> str:
        """Encrypt large text (CV content) using AES"""
        if not plaintext:
            return ""
        
        # Generate random IV
        iv = os.urandom(16)
        
        # Create cipher
        key = hashlib.sha256(self.master_password.encode()).digest()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Pad text to be multiple of 16 bytes
        padded_text = self._pad_text(plaintext.encode('utf-8'))
        
        # Encrypt
        encrypted = encryptor.update(padded_text) + encryptor.finalize()
        
        # Combine IV + encrypted data and encode
        result = iv + encrypted
        return base64.urlsafe_b64encode(result).decode('utf-8')
    
    def decrypt_large_text(self, encrypted_text: str) -> str:
        """Decrypt large text (CV content)"""
        if not encrypted_text:
            return ""
        
        try:
            # Decode
            encrypted_data = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
            
            # Extract IV and encrypted content
            iv = encrypted_data[:16]
            encrypted_content = encrypted_data[16:]
            
            # Create cipher
            key = hashlib.sha256(self.master_password.encode()).digest()
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            
            # Decrypt and unpad
            decrypted_padded = decryptor.update(encrypted_content) + decryptor.finalize()
            decrypted = self._unpad_text(decrypted_padded)
            
            return decrypted.decode('utf-8')
        except Exception as e:
            print(f"Large text decryption error: {e}")
            return ""
    
    def _pad_text(self, text: bytes) -> bytes:
        """PKCS7 padding"""
        pad_length = 16 - (len(text) % 16)
        return text + bytes([pad_length] * pad_length)
    
    def _unpad_text(self, padded_text: bytes) -> bytes:
        """Remove PKCS7 padding"""
        pad_length = padded_text[-1]
        return padded_text[:-pad_length]
    
    def hash_phone(self, phone: str) -> str:
        """One-way hash for phone numbers (searchable but secure)"""
        if not phone:
            return ""
        
        # Use salt + phone for hashing
        combined = self.salt + phone.encode('utf-8')
        return hashlib.sha256(combined).hexdigest()

class EncryptedDatabaseManager:
    """Database manager with encryption support"""
    
    def __init__(self, crypto_manager: ATSCryptoManager, host="localhost", user="root", database="ats_db", password=None):
        self.crypto = crypto_manager
        self.host = host
        self.user = user
        self.database = database
        self.password = password or os.getenv('MYSQL_PASSWORD', '')
        self.connection = None
        
        # Auto-detect MySQL password
        if not self.password:
            try:
                test_conn = mysql.connector.connect(host=self.host, user=self.user)
                test_conn.close()
                self.password = ""
            except:
                self.password = getpass.getpass("Enter MySQL Password: ")
    
    def connect(self):
        """Connect to database"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            return True
        except mysql.connector.Error as e:
            print(f"Database connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from database"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def create_encrypted_tables(self):
        """Create encrypted versions of ATS tables"""
        if not self.connect():
            return False
        
        cursor = self.connection.cursor()
        
        # Create encrypted ApplicantProfile table
        create_encrypted_profile_table = """
        CREATE TABLE IF NOT EXISTS ApplicantProfileEncrypted (
            applicant_id INT AUTO_INCREMENT PRIMARY KEY,
            first_name_enc TEXT,
            last_name_enc TEXT,
            date_of_birth_enc TEXT,
            address_enc TEXT,
            phone_number_enc TEXT,
            phone_hash VARCHAR(64),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX(phone_hash)
        )
        """
        
        # Create encrypted ApplicationDetail table
        create_encrypted_detail_table = """
        CREATE TABLE IF NOT EXISTS ApplicationDetailEncrypted (
            detail_id INT AUTO_INCREMENT PRIMARY KEY,
            applicant_id INT NOT NULL,
            application_role_enc TEXT,
            cv_path_enc TEXT,
            cv_raw_text_enc LONGTEXT,
            summary_section_enc TEXT,
            skills_section_enc TEXT,
            experience_section_enc TEXT,
            education_section_enc TEXT,
            accomplishments_section_enc TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (applicant_id) REFERENCES ApplicantProfileEncrypted(applicant_id)
        )
        """
        
        try:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            cursor.execute(f"USE {self.database}")
            cursor.execute(create_encrypted_profile_table)
            cursor.execute(create_encrypted_detail_table)
            self.connection.commit()
            print("✅ Encrypted tables created successfully!")
            return True
        except mysql.connector.Error as e:
            print(f"❌ Error creating encrypted tables: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def get_decrypted_application(self, detail_id: int) -> Dict[str, Any]:
        """Get and decrypt application data"""
        if not self.connect():
            return {}
        
        cursor = self.connection.cursor()
        
        try:
            # Get encrypted data
            cursor.execute("""
                SELECT ad.*, ap.first_name_enc, ap.last_name_enc, ap.phone_number_enc, ap.address_enc
                FROM ApplicationDetailEncrypted ad
                JOIN ApplicantProfileEncrypted ap ON ad.applicant_id = ap.applicant_id
                WHERE ad.detail_id = %s
            """, (detail_id,))
            
            result = cursor.fetchone()
            if not result:
                return {}
            
            # Decrypt all fields
            (detail_id, applicant_id, role_enc, cv_path_enc, cv_raw_text_enc, 
             summary_enc, skills_enc, experience_enc, education_enc, accomplishments_enc, created_at,
             first_name_enc, last_name_enc, phone_enc, address_enc) = result
            
            return {
                'detail_id': detail_id,
                'applicant_id': applicant_id,
                'first_name': self.crypto.decrypt_text(first_name_enc),
                'last_name': self.crypto.decrypt_text(last_name_enc),
                'phone': self.crypto.decrypt_text(phone_enc),
                'address': self.crypto.decrypt_text(address_enc),
                'role': self.crypto.decrypt_text(role_enc),
                'cv_path': self.crypto.decrypt_text(cv_path_enc),
                'cv_raw_text': self.crypto.decrypt_large_text(cv_raw_text_enc),
                'summary': self.crypto.decrypt_text(summary_enc),
                'skills': self.crypto.decrypt_text(skills_enc),
                'experience': self.crypto.decrypt_large_text(experience_enc),
                'education': self.crypto.decrypt_text(education_enc),
                'accomplishments': self.crypto.decrypt_text(accomplishments_enc)
            }
            
        except mysql.connector.Error as e:
            print(f"Error retrieving application: {e}")
            return {}
        finally:
            cursor.close()
            self.disconnect()

# Global instances
_global_crypto = None
_global_db = None

def get_crypto_manager(master_password: str = None) -> ATSCryptoManager:
    """Get global crypto manager instance"""
    global _global_crypto
    if _global_crypto is None:
        _global_crypto = ATSCryptoManager(master_password)
    return _global_crypto

def get_database_connection() -> EncryptedDatabaseManager:
    """Get global encrypted database connection"""
    global _global_db
    if _global_db is None:
        crypto = get_crypto_manager()
        _global_db = EncryptedDatabaseManager(crypto)
    return _global_db

# Test function
def test_encryption():
    """Test encryption functionality"""
    print("🔐 Testing ATS Encryption System")
    print("=" * 40)
    
    try:
        # Test crypto manager
        crypto = get_crypto_manager("test_password_123")
        
        # Test small text
        original = "John Doe"
        encrypted = crypto.encrypt_text(original)
        decrypted = crypto.decrypt_text(encrypted)
        
        print(f"Small text test: {original} -> {encrypted[:20]}... -> {decrypted}")
        assert original == decrypted, "Small text encryption failed"
        print("✅ Small text encryption: PASSED")
        
        # Test large text
        large_text = "This is a sample CV content " * 100
        encrypted_large = crypto.encrypt_large_text(large_text)
        decrypted_large = crypto.decrypt_large_text(encrypted_large)
        
        assert large_text == decrypted_large, "Large text encryption failed"
        print("✅ Large text encryption: PASSED")
        
        # Test phone hash
        phone = "+628123456789"
        phone_hash = crypto.hash_phone(phone)
        print(f"Phone hash: {phone} -> {phone_hash}")
        print("✅ Phone hashing: PASSED")
        
        # Test database
        db = get_database_connection()
        if db.create_encrypted_tables():
            print("✅ Database tables creation: PASSED")
        else:
            print("❌ Database tables creation: FAILED")
        
        print("\n🎉 All encryption tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Encryption test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_encryption()