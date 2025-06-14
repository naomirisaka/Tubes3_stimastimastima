import mysql.connector
import os
import getpass
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json
import base64
import hashlib

@dataclass
class ApplicantProfile:
    applicant_id: int
    first_name: str
    last_name: str
    date_of_birth: str
    address: str
    phone_number: str
    is_encrypted: bool = False

@dataclass
class ApplicationDetail:
    detail_id: int
    applicant_id: int
    application_role: str
    cv_path: str
    cv_raw_text: str
    summary_section: str
    skills_section: str
    experience_section: str
    education_section: str
    accomplishments_section: str
    is_encrypted: bool = False

class EncryptionManager:
    def __init__(self):
        self.key = None
        self.cipher = None
        self.encryption_enabled = False
        self.key_file = "ats_encryption.key"
        self.config_file = "ats_config.json"
        self.search_paths = self._get_search_paths()
    
    def _get_search_paths(self) -> list:
        current_dir = os.getcwd()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        search_paths = [
            current_dir,                                   
            script_dir,                                    
            os.path.join(current_dir, "data_extractor"), 
            os.path.join(script_dir, "..", "data_extractor"), 
            os.path.dirname(current_dir),               
            os.path.join(os.path.dirname(current_dir), "data_extractor"),

            os.path.join(os.path.dirname(script_dir)),
            os.path.join(os.path.dirname(os.path.dirname(script_dir))),
        ]
        
        unique_paths = []
        for path in search_paths:
            abs_path = os.path.abspath(path)
            if abs_path not in unique_paths and os.path.exists(abs_path):
                unique_paths.append(abs_path)
        
        return unique_paths
    
    def _find_file(self, filename: str) -> str:
        for path in self.search_paths:
            file_path = os.path.join(path, filename)
            if os.path.exists(file_path):
                return file_path
        return None
    
    def load_encryption_config(self) -> dict:
        config_path = self._find_file(self.config_file)
        
        if not config_path:
            return {"encryption_enabled": False, "password_protected": False}
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            # print(f"Loaded encryption config from: {config_path}")
            return config
        except Exception as e:
            print(f"Failed to load encryption config: {e}")
            return {"encryption_enabled": False, "password_protected": False}
    
    def load_key(self, password: str = None) -> bytes:
        key_path = self._find_file(self.key_file)
        
        if not key_path:
            print(f"Searched for {self.key_file} in paths:")
            for path in self.search_paths:
                print(f"   - {path}")
            return None
        
        try:
            with open(key_path, 'rb') as f:
                key_data = f.read()
            # print(f"Loaded encryption key from: {key_path}")
            
            if password:
                try:
                    from cryptography.fernet import Fernet
                    
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
                
        except Exception as e:
            print(f"Failed to load key file: {e}")
            return None
    
    def initialize_encryption(self, password: str = None) -> bool:
        config = self.load_encryption_config()
        
        if not config.get("encryption_enabled"):
            self.encryption_enabled = False
            print("Encryption disabled in config")
            return True
        
        key = self.load_key(password)
        
        if not key:
            print("Failed to load encryption key")
            return False
        
        try:
            from cryptography.fernet import Fernet
            self.key = key
            self.cipher = Fernet(key)
            self.encryption_enabled = True
            print("Encryption initialized successfully")
            return True
        except Exception as e:
            print(f"Failed to initialize encryption: {e}")
            return False
    
    def decrypt_text(self, encrypted_text: str) -> str:
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
        if not text or len(text) < 10:
            return False
        
        try:
            decoded = base64.b64decode(text.encode('utf-8'))
            return len(decoded) > 10 and decoded.startswith(b'\x80')
        except:
            return False
    
    def get_file_locations(self) -> dict:
        return {
            "key_file": self._find_file(self.key_file),
            "config_file": self._find_file(self.config_file),
            "search_paths": self.search_paths
        }

class DatabaseManager:    
    def __init__(self, host="localhost", user="root", database="ats_db", password=None):
        self.host = host
        self.user = user
        self.database = database
        self.password = password or os.getenv('MYSQL_PASSWORD', '')
        self.connection = None
        self.encryption_manager = EncryptionManager()
        
        if not self.password:
            try:
                test_conn = mysql.connector.connect(host=self.host, user=self.user)
                test_conn.close()
                self.password = ""
            except:
                self.password = getpass.getpass("Enter MySQL Password: ")
        
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        config = self.encryption_manager.load_encryption_config()
        
        if config.get("encryption_enabled"):
            password = None
            if config.get("password_protected"):
                password = getpass.getpass("Enter encryption password for database access: ")
            
            if not self.encryption_manager.initialize_encryption(password):
                print("Warning: Failed to initialize encryption. Encrypted data may not be readable.")
        else:
            self.encryption_manager.encryption_enabled = False
    
    def connect(self):
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
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                return []
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            cursor.close()
            return results
        except mysql.connector.Error as e:
            print(f"Query execution error: {e}")
            return []
    
    def _ensure_encryption_columns(self):
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                return False
        
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("SHOW COLUMNS FROM ApplicantProfile LIKE 'is_encrypted'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE ApplicantProfile ADD COLUMN is_encrypted BOOLEAN DEFAULT FALSE")
                cursor.execute("UPDATE ApplicantProfile SET is_encrypted = FALSE WHERE is_encrypted IS NULL")
                print("Added is_encrypted column to ApplicantProfile")
            
            cursor.execute("SHOW COLUMNS FROM ApplicationDetail LIKE 'is_encrypted'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE ApplicationDetail ADD COLUMN is_encrypted BOOLEAN DEFAULT FALSE")
                cursor.execute("UPDATE ApplicationDetail SET is_encrypted = FALSE WHERE is_encrypted IS NULL")
                print("Added is_encrypted column to ApplicationDetail")
            
            self.connection.commit()
            cursor.close()
            return True
            
        except mysql.connector.Error as e:
            print(f"Error ensuring encryption columns: {e}")
            return False
    
    def _decrypt_profile_data(self, row: tuple) -> ApplicantProfile:
        if len(row) == 7:
            applicant_id, first_name, last_name, date_of_birth, address, phone_number, is_encrypted = row
        else:
            applicant_id, first_name, last_name, date_of_birth, address, phone_number = row
            is_encrypted = False
        
        if is_encrypted and self.encryption_manager.encryption_enabled:
            first_name = self.encryption_manager.decrypt_text(first_name) if first_name else ""
            last_name = self.encryption_manager.decrypt_text(last_name) if last_name else ""
            date_of_birth = self.encryption_manager.decrypt_text(date_of_birth) if date_of_birth else ""
            address = self.encryption_manager.decrypt_text(address) if address else ""
            phone_number = self.encryption_manager.decrypt_text(phone_number) if phone_number else ""
        
        return ApplicantProfile(
            applicant_id=applicant_id,
            first_name=first_name or "",
            last_name=last_name or "",
            date_of_birth=date_of_birth or "",
            address=address or "",
            phone_number=phone_number or "",
            is_encrypted=is_encrypted
        )
    
    def _decrypt_application_data(self, row: tuple) -> ApplicationDetail:
        if len(row) == 11:
            detail_id, applicant_id, application_role, cv_path, cv_raw_text, summary_section, skills_section, experience_section, education_section, accomplishments_section, is_encrypted = row
        else:
            detail_id, applicant_id, application_role, cv_path, cv_raw_text, summary_section, skills_section, experience_section, education_section, accomplishments_section = row
            is_encrypted = False
        
        if is_encrypted and self.encryption_manager.encryption_enabled:
            application_role = self.encryption_manager.decrypt_text(application_role) if application_role else ""
            cv_raw_text = self.encryption_manager.decrypt_text(cv_raw_text) if cv_raw_text else ""
            summary_section = self.encryption_manager.decrypt_text(summary_section) if summary_section else ""
            skills_section = self.encryption_manager.decrypt_text(skills_section) if skills_section else ""
            experience_section = self.encryption_manager.decrypt_text(experience_section) if experience_section else ""
            education_section = self.encryption_manager.decrypt_text(education_section) if education_section else ""
            accomplishments_section = self.encryption_manager.decrypt_text(accomplishments_section) if accomplishments_section else ""
        
        return ApplicationDetail(
            detail_id=detail_id,
            applicant_id=applicant_id,
            application_role=application_role or "General Application",
            cv_path=cv_path or "",
            cv_raw_text=cv_raw_text or "",
            summary_section=summary_section or "",
            skills_section=skills_section or "",
            experience_section=experience_section or "",
            education_section=education_section or "",
            accomplishments_section=accomplishments_section or "",
            is_encrypted=is_encrypted
        )
    
    def get_all_applications(self) -> List[ApplicationDetail]:
        self._ensure_encryption_columns()
        
        query = """
        SELECT detail_id, applicant_id, application_role, cv_path, cv_raw_text,
               summary_section, skills_section, experience_section, 
               education_section, accomplishments_section, 
               COALESCE(is_encrypted, FALSE) as is_encrypted
        FROM ApplicationDetail
        """
        
        results = self.execute_query(query)
        applications = []
        
        for row in results:
            app = self._decrypt_application_data(row)
            applications.append(app)
        
        return applications
    
    def get_application_by_id(self, detail_id: int) -> Optional[ApplicationDetail]:
        self._ensure_encryption_columns()
        
        query = """
        SELECT detail_id, applicant_id, application_role, cv_path, cv_raw_text,
               summary_section, skills_section, experience_section, 
               education_section, accomplishments_section,
               COALESCE(is_encrypted, FALSE) as is_encrypted
        FROM ApplicationDetail WHERE detail_id = %s
        """
        
        results = self.execute_query(query, (detail_id,))
        if not results:
            return None
        
        return self._decrypt_application_data(results[0])
    
    def get_applicant_profile(self, applicant_id: int) -> Optional[ApplicantProfile]:
        self._ensure_encryption_columns()
        
        query = """
        SELECT applicant_id, first_name, last_name, date_of_birth, address, phone_number,
               COALESCE(is_encrypted, FALSE) as is_encrypted
        FROM ApplicantProfile WHERE applicant_id = %s
        """
        
        results = self.execute_query(query, (applicant_id,))
        if not results:
            return None
        
        return self._decrypt_profile_data(results[0])
    
    def get_applications_by_role(self, role: str) -> List[ApplicationDetail]:
        applications = self.get_all_applications()
        matching_applications = []
        
        for app in applications:
            if role.lower() in app.application_role.lower():
                matching_applications.append(app)
        
        return matching_applications
    
    def search_applications_by_text(self, search_term: str) -> List[ApplicationDetail]:
        all_applications = self.get_all_applications()
        matching_applications = []
        
        search_term_lower = search_term.lower()
        
        for app in all_applications:
            searchable_text = " ".join([
                app.cv_raw_text,
                app.summary_section,
                app.skills_section,
                app.experience_section,
                app.education_section,
                app.accomplishments_section
            ]).lower()
            
            if search_term_lower in searchable_text:
                matching_applications.append(app)
        
        return matching_applications
    
    def get_database_stats(self) -> Dict[str, int]:
        stats = {}
        
        result = self.execute_query("SELECT COUNT(*) FROM ApplicantProfile")
        stats['total_applicants'] = result[0][0] if result else 0
        
        result = self.execute_query("SELECT COUNT(*) FROM ApplicationDetail")
        stats['total_applications'] = result[0][0] if result else 0
        
        self._ensure_encryption_columns()
        
        result = self.execute_query("SELECT COUNT(*) FROM ApplicationDetail WHERE COALESCE(is_encrypted, FALSE) = TRUE")
        stats['encrypted_applications'] = result[0][0] if result else 0
        
        result = self.execute_query("SELECT COUNT(*) FROM ApplicantProfile WHERE COALESCE(is_encrypted, FALSE) = TRUE")
        stats['encrypted_profiles'] = result[0][0] if result else 0
        
        all_applications = self.get_all_applications()
        role_counts = {}
        for app in all_applications:
            role = app.application_role
            role_counts[role] = role_counts.get(role, 0) + 1
        
        stats['applications_by_role'] = role_counts
        
        return stats
    
    def get_cv_texts_for_search(self) -> List[Tuple[int, str]]:
        """Get CV texts for search (automatically decrypts if needed)."""
        # Ensure encryption columns exist
        self._ensure_encryption_columns()
        
        query = """
        SELECT detail_id, cv_raw_text, COALESCE(is_encrypted, FALSE) as is_encrypted 
        FROM ApplicationDetail 
        WHERE cv_raw_text IS NOT NULL
        """
        results = self.execute_query(query)
        
        cv_data = []
        for row in results:
            detail_id, cv_text, is_encrypted = row
            
            if cv_text and len(cv_text.strip()) > 0:
                # Decrypt if necessary
                if is_encrypted and self.encryption_manager.encryption_enabled:
                    cv_text = self.encryption_manager.decrypt_text(cv_text)
                
                cv_data.append((detail_id, cv_text.lower()))
        
        return cv_data
    
    def get_application_summary_data(self, detail_id: int) -> Dict[str, str]:
        app = self.get_application_by_id(detail_id)
        profile = self.get_applicant_profile(app.applicant_id) if app else None
        
        if not app or not profile:
            return {}
        
        return {
            'name': f"{profile.first_name} {profile.last_name}",
            'phone': profile.phone_number,
            'address': profile.address,
            'role': app.application_role,
            'summary': app.summary_section,
            'skills': app.skills_section,
            'experience': app.experience_section,
            'education': app.education_section,
            'accomplishments': app.accomplishments_section,
            'cv_path': app.cv_path
        }
    
    def is_encryption_enabled(self) -> bool:
        return self.encryption_manager.encryption_enabled
    
    def get_encryption_status(self) -> Dict[str, any]:
        config = self.encryption_manager.load_encryption_config()
        
        return {
            "encryption_enabled": config.get("encryption_enabled", False),
            "password_protected": config.get("password_protected", False),
            "key_file_exists": bool(self.encryption_manager._find_file(self.encryption_manager.key_file)),
            "config_file_exists": bool(self.encryption_manager._find_file(self.encryption_manager.config_file)),
            "encryption_manager_ready": self.encryption_manager.encryption_enabled
        }

db_manager = DatabaseManager()

def get_database_connection():
    return db_manager