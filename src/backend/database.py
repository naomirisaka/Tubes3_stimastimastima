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
    
    def encrypt_text(self, text: str) -> str:
        if not self.encryption_enabled or not text:
            return text
        
        try:
            encrypted_data = self.cipher.encrypt(text.encode('utf-8'))
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            print(f"Encryption failed: {e}")
            return text
    
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
    _instance = None
    _initialized = False
    _password = None 
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, host="localhost", user="root", database="ats_db", password=None):
        if self._initialized:
            return
            
        print("Initializing DatabaseManager (singleton)")
        
        self.host = host
        self.user = user
        self.database = database
        self.connection = None
        self.encryption_manager = EncryptionManager()
        
        if password:
            DatabaseManager._password = password
        elif not DatabaseManager._password:
            DatabaseManager._password = self._get_mysql_password()
        
        self._initialize_encryption()
        
        self._initialized = True
    
    def _get_mysql_password(self):
        env_password = os.getenv('MYSQL_PASSWORD', '')
        if env_password:
            print("Using MySQL password from environment variable")
            return env_password
        
        print("Testing MySQL connection...")
        try:
            test_conn = mysql.connector.connect(
                host=self.host, 
                user=self.user,
                password=""
            )
            test_conn.close()
            print("MySQL connection successful with no password")
            return ""
        except mysql.connector.Error:
            print("MySQL requires a password")
            password = getpass.getpass("Enter MySQL Password: ")
            
            try:
                test_conn = mysql.connector.connect(
                    host=self.host, 
                    user=self.user, 
                    password=password
                )
                test_conn.close()
                print("Password verified successfully")
                return password
            except mysql.connector.Error as e:
                print(f"Password verification failed: {e}")
                return None
    
    def _initialize_encryption(self):
        config = self.encryption_manager.load_encryption_config()
        
        if config.get("encryption_enabled"):
            encryption_password = None
            if config.get("password_protected"):
                print("\n=== ENCRYPTION SETUP ===")
                print("Database contains encrypted data.")
                encryption_password = getpass.getpass("Enter encryption password (for encrypted data): ")
            
            if not self.encryption_manager.initialize_encryption(encryption_password):
                print("Warning: Failed to initialize encryption. Encrypted data may not be readable.")
        else:
            self.encryption_manager.encryption_enabled = False
    
    def connect(self):
        try:
            if self.connection and self.connection.is_connected():
                return True
            
            if DatabaseManager._password is None:
                print("No valid MySQL password available")
                return False
                
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=DatabaseManager._password,
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
            date_of_birth=str(date_of_birth) if date_of_birth else "",
            address=address or "",
            phone_number=phone_number or "",
            is_encrypted=is_encrypted
        )
    
    def _decrypt_application_data(self, row: tuple) -> ApplicationDetail:
        if len(row) == 5:
            detail_id, applicant_id, application_role, cv_path, is_encrypted = row
        else:
            detail_id, applicant_id, application_role, cv_path = row
            is_encrypted = False
        
        if is_encrypted and self.encryption_manager.encryption_enabled:
            application_role = self.encryption_manager.decrypt_text(application_role) if application_role else ""
        
        return ApplicationDetail(
            detail_id=detail_id,
            applicant_id=applicant_id,
            application_role=application_role or "General Application",
            cv_path=cv_path or "",
            is_encrypted=is_encrypted
        )
    
    def get_all_applications(self) -> List[ApplicationDetail]:
        self._ensure_encryption_columns()
        
        query = """
        SELECT detail_id, applicant_id, application_role, cv_path, 
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
        SELECT detail_id, applicant_id, application_role, cv_path,
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
    
    def get_cv_data_for_search(self) -> List[Tuple[int, str, str, str]]:
        """Get CV data with realtime extraction for search purposes"""
        self._ensure_encryption_columns()
        
        query = """
        SELECT ad.detail_id, ad.cv_path, 
               CONCAT(ap.first_name, ' ', ap.last_name) as applicant_name,
               ad.application_role
        FROM ApplicationDetail ad
        JOIN ApplicantProfile ap ON ad.applicant_id = ap.applicant_id
        WHERE ad.cv_path IS NOT NULL
        """
        results = self.execute_query(query)
        
        cv_data = []
        for row in results:
            detail_id, cv_path, applicant_name, application_role = row
            if cv_path and cv_path.strip():
                cv_data.append((detail_id, cv_path, applicant_name, application_role))
        
        return cv_data
    
    def get_application_basic_data(self, detail_id: int) -> Dict[str, str]:
        """Get basic application data for summary without extraction"""
        app = self.get_application_by_id(detail_id)
        profile = self.get_applicant_profile(app.applicant_id) if app else None
        
        if not app or not profile:
            return {}
        
        return {
            'name': f"{profile.first_name} {profile.last_name}",
            'phone': profile.phone_number,
            'address': profile.address,
            'role': app.application_role,
            'cv_path': app.cv_path
        }
    
    def insert_applicant_profile(self, profile_data: dict, encrypt: bool = False) -> int:
        """Insert new applicant profile"""
        self._ensure_encryption_columns()
        
        if not self.connect():
            return -1
        
        try:
            cursor = self.connection.cursor()
            
            # Encrypt data if needed
            if encrypt and self.encryption_manager.encryption_enabled:
                first_name = self.encryption_manager.encrypt_text(profile_data.get('first_name', ''))
                last_name = self.encryption_manager.encrypt_text(profile_data.get('last_name', ''))
                date_of_birth = self.encryption_manager.encrypt_text(str(profile_data.get('date_of_birth', '')))
                address = self.encryption_manager.encrypt_text(profile_data.get('address', ''))
                phone_number = self.encryption_manager.encrypt_text(profile_data.get('phone_number', ''))
            else:
                first_name = profile_data.get('first_name', '')
                last_name = profile_data.get('last_name', '')
                date_of_birth = profile_data.get('date_of_birth', '')
                address = profile_data.get('address', '')
                phone_number = profile_data.get('phone_number', '')
            
            cursor.execute("""
                INSERT INTO ApplicantProfile (first_name, last_name, date_of_birth, address, phone_number, is_encrypted)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (first_name, last_name, date_of_birth, address, phone_number, encrypt))
            
            applicant_id = cursor.lastrowid
            self.connection.commit()
            cursor.close()
            return applicant_id
            
        except Exception as e:
            print(f"Error inserting applicant profile: {e}")
            return -1
    
    def insert_application_detail(self, applicant_id: int, application_role: str, cv_path: str, encrypt: bool = False) -> bool:
        """Insert new application detail"""
        self._ensure_encryption_columns()
        
        if not self.connect():
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Encrypt data if needed
            if encrypt and self.encryption_manager.encryption_enabled:
                application_role = self.encryption_manager.encrypt_text(application_role)
            
            cursor.execute("""
                INSERT INTO ApplicationDetail (applicant_id, application_role, cv_path, is_encrypted)
                VALUES (%s, %s, %s, %s)
            """, (applicant_id, application_role, cv_path, encrypt))
            
            self.connection.commit()
            cursor.close()
            return True
            
        except Exception as e:
            print(f"Error inserting application detail: {e}")
            return False
    
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

# Global instance
db_manager = DatabaseManager()

def get_database_connection():
    return db_manager