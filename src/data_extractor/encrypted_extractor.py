import os
import glob
import re
from faker import Faker
from PyPDF2 import PdfReader
import getpass 
import random
import sys
from typing import Dict, Any
from pathlib import Path

# Import encryption system from same folder
try:
    from encryption import ATSCryptoManager, EncryptedDatabaseManager, get_crypto_manager, get_database_connection
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure encryption.py is in the same folder as this file")
    sys.exit(1)

class EncryptedATSExtractor:
    """CV Extractor with built-in encryption"""
    
    def __init__(self, master_password: str = None):
        self.crypto = ATSCryptoManager(master_password)
        self.db = EncryptedDatabaseManager(self.crypto)
        self.faker = Faker('id_ID')
        
        # Initialize encrypted database
        if not self.db.create_encrypted_tables():
            raise Exception("Failed to initialize encrypted database")
    
    def generate_phone(self):
        """Generate Indonesian phone number"""
        return "08" + ''.join(self.faker.random_choices(elements='0123456789', length=10))
    
    def generate_fake_profile(self):
        """Generate fake Indonesian profile"""
        return {
            "first_name": self.faker.first_name(),
            "last_name": self.faker.last_name(),
            "phone_number": self.generate_phone(),
            "date_of_birth": self.faker.date_of_birth(minimum_age=22, maximum_age=60).isoformat(),
            "address": self.faker.address().replace('\n', ', ')
        }
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF"""
        try:
            reader = PdfReader(pdf_path)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
            return text.strip()
        except Exception as e:
            print(f"Failed to read {pdf_path}: {e}")
            return ""
    
    def extract_cv_sections(self, cv_text):
        """Extract CV sections using regex"""
        sections = {'summary': '', 'skills': '', 'experience': '', 'education': '', 'accomplishments': ''}
        
        # Normalize text
        text = cv_text.replace('\n', ' ').replace('\r', ' ')
        text = ' '.join(text.split())  
        text_lower = text.lower()
        
        # Summary patterns
        summary_patterns = [
            r'summary\s+(.*?)(?=highlights|skills|experience|education|accomplishments|certifications|interests|additional)',
            r'profile\s+(.*?)(?=highlights|skills|experience|education|accomplishments|certifications|interests|additional)',
            r'overview\s+(.*?)(?=highlights|skills|experience|education|accomplishments|certifications|interests|additional)'
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
            if match:
                sections['summary'] = match.group(1).strip()[:1000]
                break
        
        # Skills and highlights
        skills_content = []
        
        highlights_patterns = [
            r'highlights\s+(.*?)(?=accomplishments|experience|education|certifications|interests|additional|skills)',
            r'key skills\s+(.*?)(?=accomplishments|experience|education|certifications|interests|additional)',
            r'core competencies\s+(.*?)(?=accomplishments|experience|education|certifications|interests|additional)'
        ]
        
        for pattern in highlights_patterns:
            match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
            if match:
                skills_content.append(match.group(1).strip())
                break
        
        # Skills section
        skills_patterns = [
            r'(?:^|\s)skills\s+(.*?)(?=accomplishments|achievements|certifications|interests|additional|$)',
            r'technical skills\s+(.*?)(?=accomplishments|achievements|certifications|interests|additional|$)',
            r'professional skills\s+(.*?)(?=accomplishments|achievements|certifications|interests|additional|$)'
        ]
        
        for pattern in skills_patterns:
            match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
            if match:
                skills_content.append(match.group(1).strip())
                break
        
        if skills_content:
            sections['skills'] = ' '.join(skills_content)[:1500]
        
        # Experience
        experience_patterns = [
            r'experience\s+(.*?)(?=education|accomplishments|achievements|certifications|interests|additional|skills)',
            r'work experience\s+(.*?)(?=education|accomplishments|achievements|certifications|interests|additional|skills)',
            r'employment history\s+(.*?)(?=education|accomplishments|achievements|certifications|interests|additional|skills)',
            r'professional experience\s+(.*?)(?=education|accomplishments|achievements|certifications|interests|additional|skills)'
        ]
        
        for pattern in experience_patterns:
            match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
            if match:
                exp_text = match.group(1).strip()
                exp_text = re.sub(r'company\s*name', 'Company Name', exp_text, flags=re.IGNORECASE)
                exp_text = re.sub(r'city\s*,\s*state', 'City, State', exp_text, flags=re.IGNORECASE)
                sections['experience'] = exp_text[:2000]
                break
        
        # Education
        education_patterns = [
            r'education\s+(.*?)(?=accomplishments|achievements|certifications|interests|additional|skills)',
            r'academic background\s+(.*?)(?=accomplishments|achievements|certifications|interests|additional|skills)',
            r'qualifications\s+(.*?)(?=accomplishments|achievements|certifications|interests|additional|skills)'
        ]
        
        for pattern in education_patterns:
            match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
            if match:
                edu_text = match.group(1).strip()
                sections['education'] = edu_text[:1000]
                break
        
        # Accomplishments
        accomplishments_patterns = [
            r'accomplishments\s+(.*?)(?=highlights|experience|education|interests|additional|skills)',
            r'achievements\s+(.*?)(?=highlights|experience|education|interests|additional|skills)',
            r'key achievements\s+(.*?)(?=highlights|experience|education|interests|additional|skills)',
            r'certifications\s+(.*?)(?=highlights|experience|education|interests|additional|skills)',
            r'certificates\s+(.*?)(?=highlights|experience|education|interests|additional|skills)',
            r'professional certifications\s+(.*?)(?=highlights|experience|education|interests|additional|skills)',
            r'licenses and certifications\s+(.*?)(?=highlights|experience|education|interests|additional|skills)',
            r'awards and certifications\s+(.*?)(?=highlights|experience|education|interests|additional|skills)',
            r'qualifications and certifications\s+(.*?)(?=highlights|experience|education|interests|additional|skills)',
            r'licenses\s+(.*?)(?=highlights|experience|education|interests|additional|skills)',
            r'awards\s+(.*?)(?=highlights|experience|education|interests|additional|skills)',
            r'honors\s+(.*?)(?=highlights|experience|education|interests|additional|skills)'
        ]
        
        for pattern in accomplishments_patterns:
            match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
            if match:
                sections['accomplishments'] = match.group(1).strip()[:1500]
                break
        
        return sections
    
    def extract_application_role(self, cv_text, cv_path):
        """Extract application role from CV"""
        path_parts = cv_path.replace('\\', '/').split('/')
        for part in path_parts:
            part_upper = part.upper()
            if part_upper in ['ACCOUNTANT', 'ADVOCATE', 'AGRICULTURE', 'APPAREL', 'ARTS', 
                             'AUTOMOBILE', 'AVIATION', 'BANKING', 'BPO', 'BUSINESS-DEVELOPMENT',
                             'CHEF', 'CONSTRUCTION', 'CONSULTANT', 'DESIGNER', 'DIGITAL-MEDIA',
                             'ENGINEERING', 'FINANCE', 'FITNESS', 'HEALTHCARE', 'HR',
                             'INFORMATION-TECHNOLOGY', 'PUBLIC-RELATIONS', 'SALES', 'TEACHER']:
                return part_upper.replace('-', ' ').title()
        
        # Additional role extraction logic...
        lines = cv_text.split('\n')
        for i, line in enumerate(lines[:5]):
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 3:
                continue
            
            role_keywords = [
                'chef', 'cook', 'accountant', 'engineer', 'developer', 'manager', 'analyst',
                'designer', 'consultant', 'specialist', 'coordinator', 'assistant', 'director',
                'supervisor', 'lead', 'senior', 'junior', 'associate', 'executive', 'officer'
            ]
            
            line_lower = line_clean.lower()
            for keyword in role_keywords:
                if keyword in line_lower:
                    return line_clean.title()[:100]
        
        return 'General Application'
    
    def insert_encrypted_applicant_profile(self, profile_data):
        """Insert encrypted applicant profile"""
        if not self.db.connect():
            return None
        
        cursor = self.db.connection.cursor()
        
        try:
            # Encrypt all personal data
            first_name_enc = self.crypto.encrypt_text(profile_data['first_name'])
            last_name_enc = self.crypto.encrypt_text(profile_data['last_name'])
            dob_enc = self.crypto.encrypt_text(profile_data['date_of_birth'])
            address_enc = self.crypto.encrypt_text(profile_data['address'])
            phone_enc = self.crypto.encrypt_text(profile_data['phone_number'])
            phone_hash = self.crypto.hash_phone(profile_data['phone_number'])
            
            cursor.execute("""
                INSERT INTO ApplicantProfileEncrypted 
                (first_name_enc, last_name_enc, date_of_birth_enc, address_enc, phone_number_enc, phone_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (first_name_enc, last_name_enc, dob_enc, address_enc, phone_enc, phone_hash))
            
            applicant_id = cursor.lastrowid
            self.db.connection.commit()
            return applicant_id
            
        except Exception as e:
            print(f"Error inserting profile: {e}")
            self.db.connection.rollback()
            return None
        finally:
            cursor.close()
            self.db.disconnect()
    
    def insert_encrypted_application_detail(self, applicant_id, cv_path, cv_text, sections):
        """Insert encrypted application detail"""
        if not self.db.connect():
            return False
        
        cursor = self.db.connection.cursor()
        
        try:
            role = self.extract_application_role(cv_text, cv_path)
            
            # Encrypt all CV data
            role_enc = self.crypto.encrypt_text(role)
            cv_path_enc = self.crypto.encrypt_text(cv_path)
            cv_raw_text_enc = self.crypto.encrypt_large_text(cv_text)
            summary_enc = self.crypto.encrypt_text(sections['summary'])
            skills_enc = self.crypto.encrypt_text(sections['skills'])
            experience_enc = self.crypto.encrypt_large_text(sections['experience'])
            education_enc = self.crypto.encrypt_text(sections['education'])
            accomplishments_enc = self.crypto.encrypt_text(sections['accomplishments'])
            
            cursor.execute("""
                INSERT INTO ApplicationDetailEncrypted 
                (applicant_id, application_role_enc, cv_path_enc, cv_raw_text_enc, 
                 summary_section_enc, skills_section_enc, experience_section_enc, 
                 education_section_enc, accomplishments_section_enc)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (applicant_id, role_enc, cv_path_enc, cv_raw_text_enc,
                  summary_enc, skills_enc, experience_enc, education_enc, accomplishments_enc))
            
            self.db.connection.commit()
            return True
            
        except Exception as e:
            print(f"Error inserting application detail: {e}")
            self.db.connection.rollback()
            return False
        finally:
            cursor.close()
            self.db.disconnect()
    
    def clear_encrypted_database(self):
        """Clear all data from encrypted database"""
        if not self.db.connect():
            return False
        
        cursor = self.db.connection.cursor()
        
        try:
            cursor.execute("DELETE FROM ApplicationDetailEncrypted")
            cursor.execute("DELETE FROM ApplicantProfileEncrypted")
            cursor.execute("ALTER TABLE ApplicantProfileEncrypted AUTO_INCREMENT = 1")
            cursor.execute("ALTER TABLE ApplicationDetailEncrypted AUTO_INCREMENT = 1")
            self.db.connection.commit()
            print("Encrypted database cleared successfully")
            return True
            
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False
        finally:
            cursor.close()
            self.db.disconnect()
    
    def process_folder_encrypted(self, base_folder):
        """Process PDF folder and store encrypted data"""
        pdf_files = glob.glob(os.path.join(base_folder, "**/*.pdf"), recursive=True)
        
        if not pdf_files:
            print("No PDF files found in data folder")
            return
        
        total_files = len(pdf_files)
        print(f"🔐 Found {total_files} PDF files to encrypt and process")
        
        # Clear database first
        self.clear_encrypted_database()
        
        # Create base profiles
        base_profiles = []
        profile_percentage = random.uniform(0.40, 0.50)
        num_base_profiles = max(50, int(total_files * profile_percentage))
        
        print(f"🔐 Creating {num_base_profiles} encrypted base profiles...")
        
        for i in range(num_base_profiles):
            profile_data = self.generate_fake_profile()
            applicant_id = self.insert_encrypted_applicant_profile(profile_data)
            
            if applicant_id:
                base_profiles.append({
                    'id': applicant_id,
                    'application_count': 0
                })
            
            if (i + 1) % 50 == 0:
                print(f"Encrypted {i + 1} profiles...")
        
        print(f"✅ Created {len(base_profiles)} encrypted profiles")
        
        # Process PDFs
        processed = 0
        failed = 0
        
        print("🔐 Starting encrypted PDF processing...")
        
        for i, path in enumerate(pdf_files):
            try:
                if i % 100 == 0:
                    print(f"Encrypting file {i+1}/{total_files}")
                
                cv_text = self.extract_text_from_pdf(path)
                if not cv_text or len(cv_text) < 50:
                    failed += 1
                    continue
                
                sections = self.extract_cv_sections(cv_text)
                
                # Use existing profiles (one-to-many relationship)
                selected_profile = min(base_profiles, key=lambda p: p['application_count'])
                applicant_id = selected_profile['id']
                selected_profile['application_count'] += 1
                
                if self.insert_encrypted_application_detail(applicant_id, path, cv_text, sections):
                    processed += 1
                else:
                    failed += 1
                
                if processed % 100 == 0:
                    print(f"✅ Encrypted {processed} CVs...")
                    
            except Exception as e:
                print(f"Error processing {path}: {e}")
                failed += 1
                continue
        
        print(f"\n🔐 Encrypted Processing Complete!")
        print(f"✅ Successfully encrypted: {processed} CVs")
        print(f"❌ Failed: {failed} CVs")
        print(f"👥 Profiles created: {len(base_profiles)}")
        print(f"📊 Average applications per profile: {processed/len(base_profiles):.2f}")
    
    def export_encrypted_data_stats(self, filename="encrypted_stats.txt"):
        """Export statistics about encrypted data"""
        if not self.db.connect():
            return
        
        cursor = self.db.connection.cursor()
        
        try:
            # Get basic stats
            cursor.execute("SELECT COUNT(*) FROM ApplicantProfileEncrypted")
            total_profiles = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ApplicationDetailEncrypted")
            total_applications = cursor.fetchone()[0]
            
            # Get first few encrypted records as examples
            cursor.execute("SELECT first_name_enc, phone_hash FROM ApplicantProfileEncrypted LIMIT 3")
            sample_profiles = cursor.fetchall()
            
            cursor.execute("SELECT application_role_enc, LEFT(cv_raw_text_enc, 100) FROM ApplicationDetailEncrypted LIMIT 3")
            sample_apps = cursor.fetchall()
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("🔐 ATS ENCRYPTED DATABASE STATISTICS\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Total Encrypted Profiles: {total_profiles}\n")
                f.write(f"Total Encrypted Applications: {total_applications}\n")
                f.write(f"Encryption Algorithm: AES-256 + Fernet\n")
                f.write(f"Key Derivation: PBKDF2 (100,000 iterations)\n\n")
                
                f.write("SAMPLE ENCRYPTED DATA (Unreadable without master key):\n")
                f.write("-" * 50 + "\n")
                
                f.write("Encrypted Names:\n")
                for i, (name_enc, phone_hash) in enumerate(sample_profiles, 1):
                    f.write(f"  {i}. Name: {name_enc[:50]}...\n")
                    f.write(f"     Phone Hash: {phone_hash}\n")
                
                f.write("\nEncrypted CV Content:\n")
                for i, (role_enc, cv_enc) in enumerate(sample_apps, 1):
                    f.write(f"  {i}. Role: {role_enc[:50]}...\n")
                    f.write(f"     CV: {cv_enc}...\n")
                
                f.write("\n⚠️  WARNING: This data is completely encrypted and unreadable without the master password!\n")
            
            print(f"📊 Encrypted data statistics exported to: {filename}")
            
        finally:
            cursor.close()
            self.db.disconnect()

# Updated search engine for encrypted data
class EncryptedSearchEngine:
    """Search engine that works with encrypted CV data"""
    
    def __init__(self, crypto_manager: ATSCryptoManager):
        self.crypto = crypto_manager
        self.db = EncryptedDatabaseManager(crypto_manager)
        self.cv_cache = {}
        self.cache_loaded = False
    
    def load_encrypted_cv_cache(self):
        """Load and decrypt CVs into memory for searching"""
        if self.cache_loaded:
            return
        
        if not self.db.connect():
            raise Exception("Failed to connect to encrypted database")
        
        cursor = self.db.connection.cursor()
        
        try:
            print("🔓 Decrypting CV cache for search...")
            cursor.execute("SELECT detail_id, cv_raw_text_enc FROM ApplicationDetailEncrypted")
            encrypted_cvs = cursor.fetchall()
            
            self.cv_cache = {}
            for detail_id, cv_raw_text_enc in encrypted_cvs:
                # Decrypt CV text and store in cache
                decrypted_text = self.crypto.decrypt_large_text(cv_raw_text_enc)
                if decrypted_text:
                    self.cv_cache[detail_id] = decrypted_text.lower()
            
            self.cache_loaded = True
            print(f"✅ Loaded {len(self.cv_cache)} decrypted CVs into search cache")
            
        finally:
            cursor.close()
            self.db.disconnect()
    
    def search_keywords(self, keywords_str: str, algorithm: str = "kmp", top_n: int = 10):
        """Search keywords in encrypted CVs"""
        self.load_encrypted_cv_cache()
        
        keywords = [kw.strip().lower() for kw in keywords_str.split(',') if kw.strip()]
        if not keywords:
            return []
        
        # Search in decrypted cache
        cv_matches = {}
        
        for detail_id, cv_text in self.cv_cache.items():
            keyword_counts = {}
            
            for keyword in keywords:
                if algorithm == "kmp":
                    from backend.kmp import kmp_search
                    matches = kmp_search(cv_text, keyword)
                    keyword_counts[keyword] = len(matches)
                elif algorithm == "boyer_moore":
                    from backend.boyer_moore import boyer_moore_search
                    matches = boyer_moore_search(cv_text, keyword)
                    keyword_counts[keyword] = len(matches)
                else:  # Simple count
                    keyword_counts[keyword] = cv_text.count(keyword)
            
            total_matches = sum(keyword_counts.values())
            if total_matches > 0:
                cv_matches[detail_id] = {
                    'total_matches': total_matches,
                    'keyword_matches': keyword_counts
                }
        
        # Get top matches and decrypt their details
        sorted_matches = sorted(cv_matches.items(), key=lambda x: x[1]['total_matches'], reverse=True)
        top_matches = sorted_matches[:top_n]
        
        results = []
        for detail_id, match_data in top_matches:
            app_data = self.db.get_decrypted_application(detail_id)
            if app_data:
                app_data.update(match_data)
                results.append(app_data)
        
        return results

def main():
    """Main function for encrypted ATS system"""
    print("🔐 ATS ENCRYPTED CV EXTRACTOR")
    print("=" * 40)
    
    choice = input("Choose option:\n1. Setup new encrypted database\n2. Process CVs with encryption\n3. Test encrypted search\n4. Export stats\nChoice: ")
    
    if choice == "1":
        print("\n🔐 Setting up encrypted database...")
        master_password = getpass.getpass("Create master encryption password: ")
        confirm_password = getpass.getpass("Confirm password: ")
        
        if master_password != confirm_password:
            print("❌ Passwords don't match!")
            return
        
        try:
            extractor = EncryptedATSExtractor(master_password)
            print("✅ Encrypted database setup complete!")
            print("💡 Remember to set environment variable: export ATS_MASTER_KEY='your_password'")
        except Exception as e:
            print(f"❌ Setup failed: {e}")
    
    elif choice == "2":
        print("\n🔐 Processing CVs with encryption...")
        
        try:
            extractor = EncryptedATSExtractor()
            data_folder = input("Enter data folder path (default: ../../data): ").strip()
            if not data_folder:
                data_folder = "../../data"
            
            extractor.process_folder_encrypted(data_folder)
            
        except Exception as e:
            print(f"❌ Processing failed: {e}")
    
    elif choice == "3":
        print("\n🔍 Testing encrypted search...")
        
        try:
            crypto = ATSCryptoManager()
            search_engine = EncryptedSearchEngine(crypto)
            
            keywords = input("Enter keywords (comma-separated): ")
            algorithm = input("Algorithm (kmp/boyer_moore): ").strip() or "kmp"
            
            results = search_engine.search_keywords(keywords, algorithm, 5)
            
            print(f"\n📊 Found {len(results)} matching CVs:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result['first_name']} {result['last_name']}")
                print(f"   Role: {result['role']}")
                print(f"   Total Matches: {result['total_matches']}")
                print(f"   Keywords: {result['keyword_matches']}")
                
        except Exception as e:
            print(f"❌ Search failed: {e}")
    
    elif choice == "4":
        print("\n📊 Exporting encrypted database stats...")
        
        try:
            extractor = EncryptedATSExtractor()
            extractor.export_encrypted_data_stats()
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
    
    else:
        print("❌ Invalid choice!")

if __name__ == "__main__":
    main()