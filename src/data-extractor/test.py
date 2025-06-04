import mysql.connector
import os

# database config
DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "ats_db"

DB_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
if not DB_PASSWORD:
    try:
        test_conn = mysql.connector.connect(host=DB_HOST, user=DB_USER)
        test_conn.close()
    except:
        DB_PASSWORD = input("Input MySQL Password: ")

def view_specific_cv(applicant_id=None):
    try:
        db = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = db.cursor()
        
        if applicant_id:
            cursor.execute("""
                SELECT p.first_name, p.last_name, d.application_role, 
                       d.summary_section, d.skills_section, d.experience_section, 
                       d.education_section, d.accomplishments_section, d.cv_path
                FROM ApplicantProfile p 
                JOIN ApplicationDetail d ON p.applicant_id = d.applicant_id 
                WHERE p.applicant_id = %s
            """, (applicant_id,))
        else:
            cursor.execute("""
                SELECT p.first_name, p.last_name, d.application_role, 
                       d.summary_section, d.skills_section, d.experience_section, 
                       d.education_section, d.accomplishments_section, d.cv_path
                FROM ApplicantProfile p 
                JOIN ApplicationDetail d ON p.applicant_id = d.applicant_id 
                LIMIT 1
            """)
        
        results = cursor.fetchall()
        if results:
            if len(results) > 1:
                print(f"\nFound {len(results)} applications for this applicant:")
                
            for i, result in enumerate(results, 1):
                first, last, role, summary, skills, experience, education, accomplishments, cv_path = result
                
                if len(results) > 1:
                    print(f"\n--- Application {i} ---")
                
                print(f"\nDetailed CV")
                print(f"Name: {first} {last}")
                print(f"Applied Position: {role}")
                print(f"CV File: {cv_path}")
                print("=" * 70)
                
                sections = [
                    ("SUMMARY", summary),
                    ("SKILLS", skills), 
                    ("EXPERIENCE", experience),
                    ("EDUCATION", education),
                    ("ACCOMPLISHMENTS", accomplishments)
                ]
                
                for title, content in sections:
                    print(f"\n{title}:")
                    print("-" * 30)
                    if content and content.strip():
                        print(content)
                    else:
                        print("(No data extracted)")
                    print()
                
                if len(results) > 1 and i < len(results):
                    print("=" * 70)
        else:
            print("No data found!")
            
        cursor.close()
        db.close()
        
    except Exception as e:
        print(f"Error: {e}")

def test_database():
    try:
        db = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = db.cursor()
        
        print("ATS DATABASE\n")
        cursor.execute("SELECT COUNT(*) FROM ApplicantProfile")
        profile_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ApplicationDetail")
        detail_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT applicant_id) FROM ApplicationDetail")
        unique_profiles_used = cursor.fetchone()[0]
        
        print(f"Total Profiles: {profile_count}")
        print(f"Total Applications: {detail_count}")
        print(f"Unique Profiles Used: {unique_profiles_used}")
        print(f"One-to-Many Relationships: {detail_count - unique_profiles_used}")
        print(f"Average Applications per Profile: {detail_count/unique_profiles_used:.2f}\n")
        
        print("Sample Profiles with Multiple Applications:")
        cursor.execute("""
            SELECT p.applicant_id, p.first_name, p.last_name, COUNT(d.detail_id) as app_count,
                   GROUP_CONCAT(d.application_role SEPARATOR ', ') as roles
            FROM ApplicantProfile p 
            JOIN ApplicationDetail d ON p.applicant_id = d.applicant_id 
            GROUP BY p.applicant_id, p.first_name, p.last_name
            HAVING app_count > 1
            ORDER BY app_count DESC
            LIMIT 5
        """)
        
        multiple_apps = cursor.fetchall()
        if multiple_apps:
            for id, first, last, count, roles in multiple_apps:
                print(f"  [{id}] {first} {last} - {count} applications ({roles})")
        else:
            print("  No profiles with multiple applications found")
        
        print(f"\nSample Profiles:")
        cursor.execute("""
            SELECT p.applicant_id, p.first_name, p.last_name, p.phone_number, d.application_role, d.cv_path
            FROM ApplicantProfile p 
            JOIN ApplicationDetail d ON p.applicant_id = d.applicant_id 
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            id, first, last, phone, role, cv_path = row
            filename = cv_path.split('/')[-1] if '/' in cv_path else cv_path.split('\\')[-1]
            print(f"  [{id}] {first} {last} | {phone} | {role} | {filename}")
        
        print(f"\nRoles Distribution:")
        cursor.execute("""
            SELECT application_role, COUNT(*) as count 
            FROM ApplicationDetail 
            GROUP BY application_role 
            ORDER BY count DESC
        """)
        
        for role, count in cursor.fetchall():
            print(f"  {role}: {count}")
        
        print(f"\nSections Extraction Success Rate:")
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN summary_section IS NOT NULL AND summary_section != '' THEN 1 END) as summary_count,
                COUNT(CASE WHEN skills_section IS NOT NULL AND skills_section != '' THEN 1 END) as skills_count,
                COUNT(CASE WHEN experience_section IS NOT NULL AND experience_section != '' THEN 1 END) as exp_count,
                COUNT(CASE WHEN education_section IS NOT NULL AND education_section != '' THEN 1 END) as edu_count,
                COUNT(CASE WHEN accomplishments_section IS NOT NULL AND accomplishments_section != '' THEN 1 END) as acc_count,
                COUNT(*) as total
            FROM ApplicationDetail
        """)
        
        summary, skills, exp, edu, acc, total = cursor.fetchone()
        print(f"  Summary: {summary}/{total} ({summary/total*100:.1f}%)")
        print(f"  Skills: {skills}/{total} ({skills/total*100:.1f}%)")
        print(f"  Experience: {exp}/{total} ({exp/total*100:.1f}%)")
        print(f"  Education: {edu}/{total} ({edu/total*100:.1f}%)")
        print(f"  Accomplishments: {acc}/{total} ({acc/total*100:.1f}%)")
        
        print(f"\nSample Extracted Data:")
        cursor.execute("""
            SELECT p.first_name, p.last_name, d.application_role, 
                   d.skills_section, d.summary_section, d.experience_section, d.cv_path
            FROM ApplicantProfile p 
            JOIN ApplicationDetail d ON p.applicant_id = d.applicant_id 
            WHERE d.skills_section IS NOT NULL AND d.skills_section != ''
            LIMIT 2
        """)
        
        for first, last, role, skills, summary, experience, cv_path in cursor.fetchall():
            print(f"Profile: {first} {last} ({role})")
            print(f"CV Path: {cv_path}")
            print("=" * 50)
            
            if skills:
                print("SKILLS:")
                print(skills)
                print()
            
            if summary:
                print("SUMMARY:")
                print(summary)
                print()
                
            if experience:
                print("EXPERIENCE:")
                print(experience[:500] + "..." if len(experience) > 500 else experience)
                print()
            
            print("-" * 50)
            print()
        
        cursor.close()
        db.close()
        print("Database test completed")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("1. Overall data")
    print("2. View detailed CV")
    choice = input("Input the option (1/2): ")
    
    if choice == "2":
        applicant_id = input("Enter applicant ID (or press Enter for first record): ")
        if applicant_id.strip():
            view_specific_cv(int(applicant_id))
        else:
            view_specific_cv()
    else:
        test_database()