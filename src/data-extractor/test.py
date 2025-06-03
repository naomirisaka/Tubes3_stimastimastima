import mysql.connector
import json
import os

# Database config
DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "ats_db"

# Auto-detect password
DB_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
if not DB_PASSWORD:
    try:
        # Try without password first
        test_conn = mysql.connector.connect(host=DB_HOST, user=DB_USER)
        test_conn.close()
        print("✓ Connected to MySQL without password")
    except:
        DB_PASSWORD = input("Password MySQL: ")

def view_specific_cv(applicant_id=None):
    """View specific CV sections in detail"""
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
                       d.education_section, d.accomplishments_section
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
        
        result = cursor.fetchone()
        if result:
            first, last, role, summary, skills, experience, education, accomplishments, cv_path = result
            
            print(f"\n🔍 DETAILED CV VIEW: {first} {last} ({role})")
            print(f"📁 CV File: {cv_path}")
            print("=" * 70)
            
            sections = [
                ("📝 SUMMARY", summary),
                ("🔧 SKILLS", skills), 
                ("💼 EXPERIENCE", experience),
                ("🎓 EDUCATION", education),
                ("🏆 ACCOMPLISHMENTS", accomplishments)
            ]
            
            for title, content in sections:
                print(f"\n{title}:")
                print("-" * 30)
                if content and content.strip():
                    print(content)
                else:
                    print("(No data extracted)")
                print()
        else:
            print("No data found!")
            
        cursor.close()
        db.close()
        
    except Exception as e:
        print(f"Error: {e}")

def test_database():
    try:
        # Connect to database
        db = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = db.cursor()
        
        print("=== ATS DATABASE TEST ===\n")
        
        # 1. Count records
        cursor.execute("SELECT COUNT(*) FROM ApplicantProfile")
        profile_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ApplicationDetail")
        detail_count = cursor.fetchone()[0]
        
        print(f"📊 Total Profiles: {profile_count}")
        print(f"📊 Total Applications: {detail_count}\n")
        
        # 2. Show sample profiles
        print("👥 SAMPLE PROFILES:")
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
        
        # 3. Show roles distribution
        print(f"\n🎯 ROLES DISTRIBUTION:")
        cursor.execute("""
            SELECT application_role, COUNT(*) as count 
            FROM ApplicationDetail 
            GROUP BY application_role 
            ORDER BY count DESC
        """)
        
        for role, count in cursor.fetchall():
            print(f"  {role}: {count}")
        
        # 4. Test sections extraction
        print(f"\n📝 SECTIONS EXTRACTION TEST:")
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
        
        # 5. Show sample extracted data (FULL CONTENT)
        print(f"\n📄 SAMPLE EXTRACTED DATA (FULL):")
        cursor.execute("""
            SELECT p.first_name, p.last_name, d.application_role, 
                   d.skills_section, d.summary_section, d.experience_section, d.cv_path
            FROM ApplicantProfile p 
            JOIN ApplicationDetail d ON p.applicant_id = d.applicant_id 
            WHERE d.skills_section IS NOT NULL AND d.skills_section != ''
            LIMIT 2
        """)
        
        for first, last, role, skills, summary, experience, cv_path in cursor.fetchall():
            print(f"👤 {first} {last} ({role})")
            print(f"📁 CV Path: {cv_path}")
            print("=" * 50)
            
            if skills:
                print("🔧 SKILLS:")
                print(skills)
                print()
            
            if summary:
                print("📝 SUMMARY:")
                print(summary)
                print()
                
            if experience:
                print("💼 EXPERIENCE:")
                print(experience[:500] + "..." if len(experience) > 500 else experience)
                print()
            
            print("-" * 50)
            print()
        
        cursor.close()
        db.close()
        print("✅ Database test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("1. Basic test")
    print("2. View detailed CV")
    choice = input("Choose (1/2): ")
    
    if choice == "2":
        applicant_id = input("Enter applicant ID (or press Enter for first record): ")
        if applicant_id.strip():
            view_specific_cv(int(applicant_id))
        else:
            view_specific_cv()
    else:
        test_database()