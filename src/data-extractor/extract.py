import os
import glob
import re
import json
from faker import Faker
from PyPDF2 import PdfReader
import mysql.connector
from datetime import datetime

# ========================
# Konfigurasi Database (ubah sesuai MySQL kamu)
# ========================
DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "ats_db"

# Try common passwords or use environment variable
import os
DB_PASSWORD = os.getenv('MYSQL_PASSWORD', '')  # Set env var or leave empty for no password

if not DB_PASSWORD:
    # Try connecting without password first
    try:
        test_conn = mysql.connector.connect(host=DB_HOST, user=DB_USER)
        test_conn.close()
        print("✓ Using MySQL without password")
    except:
        DB_PASSWORD = input("Masukkan password MySQL user root: ")

# ========================
# SQL untuk buat tabel applicants dengan struktur baru
# ========================
create_applicant_profile_table = """
CREATE TABLE IF NOT EXISTS ApplicantProfile (
    applicant_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) DEFAULT NULL,
    last_name VARCHAR(50) DEFAULT NULL,
    date_of_birth DATE DEFAULT NULL,
    address VARCHAR(255) DEFAULT NULL,
    phone_number VARCHAR(20) DEFAULT NULL
)
"""

create_application_detail_table = """
CREATE TABLE IF NOT EXISTS ApplicationDetail (
    detail_id INT AUTO_INCREMENT PRIMARY KEY,
    applicant_id INT NOT NULL,
    application_role VARCHAR(100) DEFAULT NULL,
    cv_path TEXT,
    cv_raw_text LONGTEXT,
    summary_section TEXT,
    skills_section TEXT,
    experience_section TEXT,
    education_section TEXT,
    accomplishments_section TEXT,
    FOREIGN KEY (applicant_id) REFERENCES ApplicantProfile(applicant_id)
)
"""

# ========================
# Buat database jika belum ada
# ========================
conn_init = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD
)
cursor_init = conn_init.cursor()
cursor_init.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
cursor_init.close()
conn_init.close()

# ========================
# Koneksi ke database ats_db
# ========================
db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)
cursor = db.cursor()

# Buat tabel jika belum ada
cursor.execute(create_applicant_profile_table)
cursor.execute(create_application_detail_table)
db.commit()

# ========================
# Utility Faker dan fungsi bantu
# ========================
faker = Faker('id_ID')

def generate_phone():
    # 08 + 10 digit angka random
    return "08" + ''.join(faker.random_choices(elements='0123456789', length=10))

def generate_fake_profile():
    full_name = faker.name()
    name_parts = full_name.split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": generate_phone(),
        "date_of_birth": faker.date_of_birth(minimum_age=22, maximum_age=60).isoformat(),
        "address": faker.address().replace('\n', ', ')
    }

def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
        return text.strip()
    except Exception as e:
        print(f"[!] Gagal membaca {pdf_path}: {e}")
        return ""

# ========================
# Fungsi regex untuk ekstraksi bagian CV
# ========================
def extract_cv_sections(cv_text):
    """
    Ekstrak berbagai bagian dari CV menggunakan regex
    """
    sections = {
        'summary': '',
        'skills': '',
        'experience': '',
        'education': '',
        'accomplishments': ''
    }
    
    # Normalize text - convert to lowercase for pattern matching
    text_lower = cv_text.lower()
    
    # Pattern untuk Summary/About
    summary_patterns = [
        r'summary\s*\n(.*?)(?=\n(?:skills|experience|education|highlights|accomplishments|\w+\s*\n))',
        r'about\s*\n(.*?)(?=\n(?:skills|experience|education|highlights|accomplishments|\w+\s*\n))',
        r'overview\s*\n(.*?)(?=\n(?:skills|experience|education|highlights|accomplishments|\w+\s*\n))'
    ]
    
    for pattern in summary_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            sections['summary'] = match.group(1).strip()
            break
    
    # Pattern untuk Skills/Highlights
    skills_patterns = [
        r'skills\s*\n(.*?)(?=\n(?:summary|experience|education|accomplishments|highlights|\w+\s*\n))',
        r'highlights\s*\n(.*?)(?=\n(?:summary|experience|education|accomplishments|skills|\w+\s*\n))',
        r'technical skills\s*\n(.*?)(?=\n(?:summary|experience|education|accomplishments|\w+\s*\n))'
    ]
    
    for pattern in skills_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            sections['skills'] = match.group(1).strip()
            break
    
    # Pattern untuk Experience
    experience_patterns = [
        r'experience\s*\n(.*?)(?=\n(?:education|skills|accomplishments|summary|\w+\s*\n))',
        r'work experience\s*\n(.*?)(?=\n(?:education|skills|accomplishments|summary|\w+\s*\n))',
        r'employment\s*\n(.*?)(?=\n(?:education|skills|accomplishments|summary|\w+\s*\n))'
    ]
    
    for pattern in experience_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            sections['experience'] = match.group(1).strip()
            break
    
    # Pattern untuk Education
    education_patterns = [
        r'education\s*\n(.*?)(?=\n(?:experience|skills|accomplishments|summary|\w+\s*\n|$))',
        r'academic background\s*\n(.*?)(?=\n(?:experience|skills|accomplishments|summary|\w+\s*\n|$))',
        r'qualifications\s*\n(.*?)(?=\n(?:experience|skills|accomplishments|summary|\w+\s*\n|$))'
    ]
    
    for pattern in education_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            sections['education'] = match.group(1).strip()
            break
    
    # Pattern untuk Accomplishments/Achievements
    accomplishments_patterns = [
        r'accomplishments\s*\n(.*?)(?=\n(?:experience|education|skills|summary|\w+\s*\n|$))',
        r'achievements\s*\n(.*?)(?=\n(?:experience|education|skills|summary|\w+\s*\n|$))',
        r'certifications\s*\n(.*?)(?=\n(?:experience|education|skills|summary|\w+\s*\n|$))'
    ]
    
    for pattern in accomplishments_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            sections['accomplishments'] = match.group(1).strip()
            break
    
    # Jika tidak ada pattern yang cocok, coba ambil dari original text dengan case sensitive
    if not any(sections.values()):
        # Fallback: coba extract berdasarkan line breaks dan keywords
        lines = cv_text.split('\n')
        current_section = None
        temp_content = []
        
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
                
            # Check if this line is a section header
            line_lower = line_clean.lower()
            if any(keyword in line_lower for keyword in ['summary', 'about', 'overview']):
                if current_section and temp_content:
                    sections[current_section] = '\n'.join(temp_content)
                current_section = 'summary'
                temp_content = []
            elif any(keyword in line_lower for keyword in ['skills', 'highlights', 'technical']):
                if current_section and temp_content:
                    sections[current_section] = '\n'.join(temp_content)
                current_section = 'skills'
                temp_content = []
            elif 'experience' in line_lower:
                if current_section and temp_content:
                    sections[current_section] = '\n'.join(temp_content)
                current_section = 'experience'
                temp_content = []
            elif 'education' in line_lower:
                if current_section and temp_content:
                    sections[current_section] = '\n'.join(temp_content)
                current_section = 'education'
                temp_content = []
            elif any(keyword in line_lower for keyword in ['accomplishments', 'achievements', 'certifications']):
                if current_section and temp_content:
                    sections[current_section] = '\n'.join(temp_content)
                current_section = 'accomplishments'
                temp_content = []
            else:
                # This is content, add to current section
                if current_section:
                    temp_content.append(line_clean)
        
        # Don't forget the last section
        if current_section and temp_content:
            sections[current_section] = '\n'.join(temp_content)
    
    # Clean up sections - remove empty ones and limit length
    for key in sections:
        if sections[key]:
            sections[key] = sections[key][:2000]  # Limit to 2000 chars per section
        else:
            sections[key] = None
    
    return sections

def insert_applicant_profile(profile_data):
    """Insert applicant profile and return the ID"""
    cursor.execute("""
        INSERT INTO ApplicantProfile (first_name, last_name, date_of_birth, address, phone_number)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        profile_data['first_name'],
        profile_data['last_name'],
        profile_data['date_of_birth'],
        profile_data['address'],
        profile_data['phone_number']
    ))
    return cursor.lastrowid

def insert_application_detail(applicant_id, cv_path, cv_text, sections):
    """Insert application detail with extracted sections"""
    # Extract potential role from CV text or path
    role = extract_application_role(cv_text, cv_path)
    
    cursor.execute("""
        INSERT INTO ApplicationDetail 
        (applicant_id, application_role, cv_path, cv_raw_text, summary_section, 
         skills_section, experience_section, education_section, accomplishments_section)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        applicant_id,
        role,
        cv_path,
        cv_text,
        sections['summary'],
        sections['skills'],
        sections['experience'],
        sections['education'],
        sections['accomplishments']
    ))

def extract_application_role(cv_text, cv_path):
    """Extract potential role from CV content, folder name, or first line"""
    
    # 1. Try to get role from folder structure (most reliable for your data)
    path_parts = cv_path.replace('\\', '/').split('/')
    for part in path_parts:
        part_upper = part.upper()
        if part_upper in ['ACCOUNTANT', 'ADVOCATE', 'AGRICULTURE', 'APPAREL', 'ARTS', 
                         'AUTOMOBILE', 'AVIATION', 'BANKING', 'BPO', 'BUSINESS-DEVELOPMENT',
                         'CHEF', 'CONSTRUCTION', 'CONSULTANT', 'DESIGNER', 'DIGITAL-MEDIA',
                         'ENGINEERING', 'FINANCE', 'FITNESS', 'HEALTHCARE', 'HR',
                         'INFORMATION-TECHNOLOGY', 'PUBLIC-RELATIONS', 'SALES', 'TEACHER']:
            return part_upper.replace('-', ' ').title()
    
    # 2. Try to find role in first few lines of CV (common practice)
    lines = cv_text.split('\n')
    for i, line in enumerate(lines[:5]):  # Check first 5 lines
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 3:
            continue
            
        # Skip if line looks like a name (all caps, short)
        if line_clean.isupper() and len(line_clean.split()) <= 3:
            continue
            
        # Skip contact info patterns
        if re.search(r'(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})|(@)|(\d{5})', line_clean):
            continue
            
        # Look for role-like patterns in the line
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
                # Found a role keyword, extract the full line as potential role
                return line_clean.title()[:100]  # Limit to 100 chars
    
    # 3. Try to find role patterns in CV text
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
            if len(role_text) > 5:  # Avoid too short matches
                return role_text.title()[:100]
    
    # 4. Fallback based on content keywords
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

# ========================
# Proses folder recursive cari PDF dengan batch processing
# ========================
def process_folder(base_folder):
    pdf_files = glob.glob(os.path.join(base_folder, "**/*.pdf"), recursive=True)
    
    if not pdf_files:
        print("Tidak ada file PDF ditemukan di folder 'data' dan subfoldernya.")
        return
    
    total_files = len(pdf_files)
    print(f"Ditemukan {total_files} file PDF untuk diproses...")
    
    # Batch processing untuk speed
    batch_size = 10
    processed = 0
    failed = 0
    
    for i in range(0, total_files, batch_size):
        batch = pdf_files[i:i+batch_size]
        batch_data = []
        
        print(f"\n🔄 Processing batch {i//batch_size + 1}/{(total_files + batch_size - 1)//batch_size}")
        
        for path in batch:
            try:
                print(f"  📄 {os.path.basename(path)}", end=" ... ")
                
                # Extract text from PDF (with timeout/error handling)
                cv_text = extract_text_from_pdf(path)
                if not cv_text or len(cv_text) < 50:  # Skip very short/empty CVs
                    print("❌ Empty/too short")
                    failed += 1
                    continue
                
                # Extract sections using regex (faster)
                sections = extract_cv_sections_fast(cv_text)
                
                # Generate fake profile data
                profile_data = generate_fake_profile()
                
                # Prepare batch data
                batch_data.append((profile_data, path, cv_text, sections))
                print("✅")
                processed += 1
                
            except Exception as e:
                print(f"❌ {str(e)[:50]}")
                failed += 1
                continue
        
        # Batch insert to database
        if batch_data:
            insert_batch_data(batch_data)
            print(f"  💾 Saved {len(batch_data)} records to DB")
        
        # Progress update
        print(f"  📊 Progress: {processed + failed}/{total_files} ({((processed + failed)/total_files)*100:.1f}%)")
    
    print(f"\n✅ Processing completed!")
    print(f"  ✅ Successfully processed: {processed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📈 Success rate: {(processed/(processed+failed))*100:.1f}%")

def extract_cv_sections_fast(cv_text):
    """Faster regex extraction with simpler patterns"""
    sections = {'summary': '', 'skills': '', 'experience': '', 'education': '', 'accomplishments': ''}
    
    # Simplified patterns for speed
    text_lines = cv_text.split('\n')
    current_section = None
    content = []
    
    for line in text_lines:
        line = line.strip()
        if not line:
            continue
            
        line_lower = line.lower()
        
        # Quick section detection
        if any(word in line_lower for word in ['summary', 'about', 'overview', 'profile']):
            if current_section and content:
                sections[current_section] = '\n'.join(content)[:1500]  # Limit size
            current_section = 'summary'
            content = []
        elif any(word in line_lower for word in ['skill', 'highlight', 'technical', 'competenc']):
            if current_section and content:
                sections[current_section] = '\n'.join(content)[:1500]
            current_section = 'skills'
            content = []
        elif 'experience' in line_lower or 'employment' in line_lower:
            if current_section and content:
                sections[current_section] = '\n'.join(content)[:1500]
            current_section = 'experience'
            content = []
        elif 'education' in line_lower or 'academic' in line_lower:
            if current_section and content:
                sections[current_section] = '\n'.join(content)[:1500]
            current_section = 'education'
            content = []
        elif any(word in line_lower for word in ['accomplish', 'achieve', 'certif', 'award']):
            if current_section and content:
                sections[current_section] = '\n'.join(content)[:1500]
            current_section = 'accomplishments'
            content = []
        else:
            if current_section:
                content.append(line)
    
    # Don't forget last section
    if current_section and content:
        sections[current_section] = '\n'.join(content)[:1500]
    
    return sections

def insert_batch_data(batch_data):
    """Insert multiple records at once for speed"""
    try:
        for profile_data, cv_path, cv_text, sections in batch_data:
            # Insert profile
            applicant_id = insert_applicant_profile(profile_data)
            
            # Insert application detail
            insert_application_detail(applicant_id, cv_path, cv_text, sections)
        
        db.commit()  # Commit all at once
        
    except Exception as e:
        print(f"❌ Batch insert error: {e}")
        db.rollback()

# ========================
# Export data lengkap ke file SQL
# ========================
def export_data_to_sql(filename):
    """Export all data to SQL file"""
    try:
        # Get applicant profiles
        cursor.execute("SELECT * FROM ApplicantProfile")
        profiles = cursor.fetchall()
        
        # Get application details
        cursor.execute("SELECT * FROM ApplicationDetail")
        details = cursor.fetchall()
        
        def escape_sql(val):
            if val is None:
                return "NULL"
            return "'" + str(val).replace("'", "''").replace("\\", "\\\\") + "'"
        
        with open(filename, "w", encoding="utf-8") as f:
            # Create database & use
            f.write(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};\n")
            f.write(f"USE {DB_NAME};\n\n")
            
            # Create tables
            f.write("-- Create ApplicantProfile table\n")
            f.write(create_applicant_profile_table.strip() + ";\n\n")
            f.write("-- Create ApplicationDetail table\n")
            f.write(create_application_detail_table.strip() + ";\n\n")
            
            # Insert ApplicantProfile data
            f.write("-- Insert ApplicantProfile data\n")
            for profile in profiles:
                applicant_id, first_name, last_name, dob, address, phone = profile
                dob_val = escape_sql(dob.isoformat() if dob else None)
                
                insert_stmt = (
                    "INSERT INTO ApplicantProfile (applicant_id, first_name, last_name, date_of_birth, address, phone_number) VALUES ("
                    f"{applicant_id}, {escape_sql(first_name)}, {escape_sql(last_name)}, {dob_val}, "
                    f"{escape_sql(address)}, {escape_sql(phone)});\n"
                )
                f.write(insert_stmt)
            
            f.write("\n-- Insert ApplicationDetail data\n")
            for detail in details:
                detail_id, applicant_id, role, cv_path, cv_raw_text, summary, skills, experience, education, accomplishments = detail
                
                insert_stmt = (
                    "INSERT INTO ApplicationDetail (detail_id, applicant_id, application_role, cv_path, cv_raw_text, "
                    "summary_section, skills_section, experience_section, education_section, accomplishments_section) VALUES ("
                    f"{detail_id}, {applicant_id}, {escape_sql(role)}, {escape_sql(cv_path)}, {escape_sql(cv_raw_text)}, "
                    f"{escape_sql(summary)}, {escape_sql(skills)}, {escape_sql(experience)}, "
                    f"{escape_sql(education)}, {escape_sql(accomplishments)});\n"
                )
                f.write(insert_stmt)
        
        print(f"✓ Data berhasil diexport ke file: {filename}")
        
    except Exception as e:
        print(f"[!] Error saat export data: {e}")

# ========================
# Function untuk testing ekstraksi
# ========================
def test_extraction(pdf_path):
    """Test extraction on a single PDF file"""
    print(f"Testing extraction pada: {pdf_path}")
    cv_text = extract_text_from_pdf(pdf_path)
    sections = extract_cv_sections(cv_text)
    
    print("\n=== HASIL EKSTRAKSI ===")
    for section_name, content in sections.items():
        print(f"\n{section_name.upper()}:")
        print("-" * 40)
        if content:
            print(content[:200] + "..." if len(content) > 200 else content)
        else:
            print("(Tidak ditemukan)")

# ========================
# Main
# ========================
if __name__ == "__main__":
    print("=== CV ATS Extraction Tool ===\n")
    
    # Uncomment line ini untuk test ekstraksi pada satu file
    # test_extraction("../data/CHEF/10276858.pdf")
    
    # Proses semua PDF di folder data (relative path dari data-extractor)
    process_folder("../../data")
    
    # Export ke SQL file di folder doc
    export_data_to_sql("../../data/ats.sql")
    
    # Tampilkan statistik
    cursor.execute("SELECT COUNT(*) FROM ApplicantProfile")
    profile_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ApplicationDetail")
    detail_count = cursor.fetchone()[0]
    
    print(f"\n=== STATISTIK ===")
    print(f"Total Profiles: {profile_count}")
    print(f"Total Applications: {detail_count}")
    
    cursor.close()
    db.close()
    print("\n✓ Selesai!")