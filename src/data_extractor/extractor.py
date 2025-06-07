import os
import glob
import re
import json
from faker import Faker
from PyPDF2 import PdfReader
import mysql.connector
from datetime import datetime

# database configuration
DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "ats_db"

import os
DB_PASSWORD = os.getenv('MYSQL_PASSWORD', '')  

if not DB_PASSWORD:
    try:
        test_conn = mysql.connector.connect(host=DB_HOST, user=DB_USER)
        test_conn.close()
    except:
        DB_PASSWORD = input("Input MySQL Password: ")

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
        reader = PdfReader(pdf_path)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
        return text.strip()
    except Exception as e:
        print(f"Failed to read {pdf_path}: {e}")
        return ""

def extract_cv_sections(cv_text):
    sections = {'summary': '', 'skills': '', 'experience': '', 'education': '', 'accomplishments': ''}
    
    # normalize text
    text = cv_text.replace('\n', ' ').replace('\r', ' ')
    text = ' '.join(text.split())  
    text_lower = text.lower()
    
    # summary
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
    
    # skills and highlights - combine both sections
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
    
    # get skills section at end of cv
    skills_patterns = [
        r'(?:^|\s)skills\s+(.*?)(?=certifications|interests|additional information|$)',
        r'technical skills\s+(.*?)(?=certifications|interests|additional information|$)',
        r'professional skills\s+(.*?)(?=certifications|interests|additional information|$)'
    ]
    
    for pattern in skills_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            skills_content.append(match.group(1).strip())
            break
    
    if skills_content:
        sections['skills'] = ' '.join(skills_content)[:1500]
    
    # experience
    experience_patterns = [
        r'experience\s+(.*?)(?=education|certifications|interests|additional|skills\s+(?:accounting|general))',
        r'work experience\s+(.*?)(?=education|certifications|interests|additional|skills\s+(?:accounting|general))',
        r'employment history\s+(.*?)(?=education|certifications|interests|additional|skills\s+(?:accounting|general))',
        r'professional experience\s+(.*?)(?=education|certifications|interests|additional|skills\s+(?:accounting|general))'
    ]
    
    for pattern in experience_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            exp_text = match.group(1).strip()
            exp_text = re.sub(r'company\s*name', 'Company Name', exp_text, flags=re.IGNORECASE)
            exp_text = re.sub(r'city\s*,\s*state', 'City, State', exp_text, flags=re.IGNORECASE)
            sections['experience'] = exp_text[:2000]
            break
    
    # education
    education_patterns = [
        r'education\s+(.*?)(?=certifications|interests|additional|skills\s+(?:accounting|general)|$)',
        r'academic background\s+(.*?)(?=certifications|interests|additional|skills\s+(?:accounting|general)|$)',
        r'qualifications\s+(.*?)(?=certifications|interests|additional|skills\s+(?:accounting|general)|$)'
    ]
    
    for pattern in education_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            edu_text = match.group(1).strip()
            sections['education'] = edu_text[:1000]
            break
    
    # accomplishments
    accomplishments_patterns = [
        r'accomplishments\s+(.*?)(?=experience|education|certifications|interests|additional|skills)',
        r'achievements\s+(.*?)(?=experience|education|certifications|interests|additional|skills)',
        r'key achievements\s+(.*?)(?=experience|education|certifications|interests|additional|skills)'
    ]
    
    for pattern in accomplishments_patterns:
        match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
        if match:
            sections['accomplishments'] = match.group(1).strip()[:1500]
            break
    
    # fallback parsing
    if not any(sections.values()):
        sections = extract_cv_sections_fallback(cv_text)
    
    return sections

def extract_cv_sections_fallback(cv_text):
    sections = {'summary': '', 'skills': '', 'experience': '', 'education': '', 'accomplishments': ''}
    
    lines = cv_text.split('\n')
    current_section = None
    content = []
    
    section_keywords = {
        'summary': ['summary', 'profile', 'overview', 'about'],
        'skills': ['highlights', 'skills', 'technical skills', 'competencies', 'core competencies'],
        'experience': ['experience', 'work experience', 'employment', 'professional experience'],
        'education': ['education', 'academic', 'qualifications'],
        'accomplishments': ['accomplishments', 'achievements', 'certifications', 'awards']
    }
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        line_lower = line.lower()
        
        found_section = None
        for section, keywords in section_keywords.items():
            if any(keyword in line_lower and len(line) < 50 for keyword in keywords):
                if current_section and content:
                    sections[current_section] = ' '.join(content)[:1500]
                
                found_section = section
                content = []
                break
        
        if found_section:
            current_section = found_section
        elif current_section:
            content.append(line)
            
            if len(' '.join(content)) > 1500:
                break
    
    if current_section and content:
        sections[current_section] = ' '.join(content)[:1500]
    
    return sections

def insert_applicant_profile(profile_data):
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

def process_folder(base_folder):
    pdf_files = glob.glob(os.path.join(base_folder, "**/*.pdf"), recursive=True)
    
    if not pdf_files:
        print("No PDF file found in data and its subfiles")
        return
    
    total_files = len(pdf_files)
    print(f"Found {total_files} PDF files to process")
    
    # CLEAR DATABASE FIRST - removed from here since it's in main now
    # print("Clearing existing data...")
    # cursor.execute("DELETE FROM ApplicationDetail")
    # cursor.execute("DELETE FROM ApplicantProfile")
    # db.commit()
    # print("Database cleared")
    
    # create base profiles for one-to-many
    base_profiles = []
    num_base_profiles = 200  # Fixed number for testing
    
    print(f"Creating {num_base_profiles} base profiles")
    
    for i in range(num_base_profiles):
        profile_data = generate_fake_profile()
        applicant_id = insert_applicant_profile(profile_data)
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
            
            insert_application_detail(applicant_id, path, cv_text, sections)
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
                original_id, first_name, last_name, dob, address, phone = profile
                dob_val = escape_sql(dob.isoformat() if dob else None)
                
                # use sequential IDs starting from 1
                insert_stmt = (
                    "INSERT INTO ApplicantProfile (applicant_id, first_name, last_name, date_of_birth, address, phone_number) VALUES ("
                    f"{i}, {escape_sql(first_name)}, {escape_sql(last_name)}, {dob_val}, "
                    f"{escape_sql(address)}, {escape_sql(phone)});\n"
                )
                f.write(insert_stmt)
            
            f.write("\n-- Insert ApplicationDetail data\n")
            
            # create mapping from old IDs to new IDs to maintain relationships
            id_mapping = {}
            for i, profile in enumerate(profiles, 1):
                original_id = profile[0]
                id_mapping[original_id] = i
            
            for i, detail in enumerate(details, 1):  # start from 1
                detail_id, original_applicant_id, role, cv_path, cv_raw_text, summary, skills, experience, education, accomplishments = detail
                new_applicant_id = id_mapping[original_applicant_id]  # maintain one-to-many relationships
                
                insert_stmt = (
                    "INSERT INTO ApplicationDetail (detail_id, applicant_id, application_role, cv_path, cv_raw_text, "
                    "summary_section, skills_section, experience_section, education_section, accomplishments_section) VALUES ("
                    f"{i}, {new_applicant_id}, {escape_sql(role)}, {escape_sql(cv_path)}, {escape_sql(cv_raw_text)}, "
                    f"{escape_sql(summary)}, {escape_sql(skills)}, {escape_sql(experience)}, "
                    f"{escape_sql(education)}, {escape_sql(accomplishments)});\n"
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
    print("=== CV ATS Extraction App ===\n")
    
    # CLEAR DATABASE FIRST
    print("Clearing existing data...")
    cursor.execute("DELETE FROM ApplicationDetail")
    cursor.execute("DELETE FROM ApplicantProfile")
    cursor.execute("ALTER TABLE ApplicantProfile AUTO_INCREMENT = 1")
    cursor.execute("ALTER TABLE ApplicationDetail AUTO_INCREMENT = 1")
    db.commit()
    print("Database cleared and AUTO_INCREMENT reset")
    
    # test_extraction("../../data/CHEF/10276858.pdf")
    
    process_folder("../../data")
    export_data_to_sql("../../data/ats.sql")
    
    cursor.close()
    db.close()