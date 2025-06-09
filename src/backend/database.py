import mysql.connector
import os
import getpass
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ApplicantProfile:
    applicant_id: int
    first_name: str
    last_name: str
    date_of_birth: str
    address: str
    phone_number: str

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

class DatabaseManager:    
    def __init__(self, host="localhost", user="root", database="ats_db", password=None):
        self.host = host
        self.user = user
        self.database = database
        self.password = password or os.getenv('MYSQL_PASSWORD', '')
        self.connection = None
        
        # Auto-detect password if not provided
        if not self.password:
            try:
                test_conn = mysql.connector.connect(host=self.host, user=self.user)
                test_conn.close()
                self.password = ""
            except:
                self.password = getpass.getpass("Enter MySQL Password: ")
    
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
    
    def get_all_applications(self) -> List[ApplicationDetail]:
        query = """
        SELECT detail_id, applicant_id, application_role, cv_path, cv_raw_text,
               summary_section, skills_section, experience_section, 
               education_section, accomplishments_section
        FROM ApplicationDetail
        """
        
        results = self.execute_query(query)
        applications = []
        
        for row in results:
            app = ApplicationDetail(
                detail_id=row[0],
                applicant_id=row[1],
                application_role=row[2] or "General Application",
                cv_path=row[3] or "",
                cv_raw_text=row[4] or "",
                summary_section=row[5] or "",
                skills_section=row[6] or "",
                experience_section=row[7] or "",
                education_section=row[8] or "",
                accomplishments_section=row[9] or ""
            )
            applications.append(app)
        
        return applications
    
    def get_application_by_id(self, detail_id: int) -> Optional[ApplicationDetail]:
        query = """
        SELECT detail_id, applicant_id, application_role, cv_path, cv_raw_text,
               summary_section, skills_section, experience_section, 
               education_section, accomplishments_section
        FROM ApplicationDetail WHERE detail_id = %s
        """
        
        results = self.execute_query(query, (detail_id,))
        if not results:
            return None
        
        row = results[0]
        return ApplicationDetail(
            detail_id=row[0],
            applicant_id=row[1],
            application_role=row[2] or "General Application",
            cv_path=row[3] or "",
            cv_raw_text=row[4] or "",
            summary_section=row[5] or "",
            skills_section=row[6] or "",
            experience_section=row[7] or "",
            education_section=row[8] or "",
            accomplishments_section=row[9] or ""
        )
    
    def get_applicant_profile(self, applicant_id: int) -> Optional[ApplicantProfile]:
        query = """
        SELECT applicant_id, first_name, last_name, date_of_birth, address, phone_number
        FROM ApplicantProfile WHERE applicant_id = %s
        """
        
        results = self.execute_query(query, (applicant_id,))
        if not results:
            return None
        
        row = results[0]
        return ApplicantProfile(
            applicant_id=row[0],
            first_name=row[1] or "",
            last_name=row[2] or "",
            date_of_birth=str(row[3]) if row[3] else "",
            address=row[4] or "",
            phone_number=row[5] or ""
        )
    
    def get_applications_by_role(self, role: str) -> List[ApplicationDetail]:
        query = """
        SELECT detail_id, applicant_id, application_role, cv_path, cv_raw_text,
               summary_section, skills_section, experience_section, 
               education_section, accomplishments_section
        FROM ApplicationDetail WHERE application_role LIKE %s
        """
        
        results = self.execute_query(query, (f"%{role}%",))
        applications = []
        
        for row in results:
            app = ApplicationDetail(
                detail_id=row[0],
                applicant_id=row[1],
                application_role=row[2] or "General Application",
                cv_path=row[3] or "",
                cv_raw_text=row[4] or "",
                summary_section=row[5] or "",
                skills_section=row[6] or "",
                experience_section=row[7] or "",
                education_section=row[8] or "",
                accomplishments_section=row[9] or ""
            )
            applications.append(app)
        
        return applications
    
    def search_applications_by_text(self, search_term: str) -> List[ApplicationDetail]:
        query = """
        SELECT detail_id, applicant_id, application_role, cv_path, cv_raw_text,
               summary_section, skills_section, experience_section, 
               education_section, accomplishments_section
        FROM ApplicationDetail 
        WHERE cv_raw_text LIKE %s 
           OR summary_section LIKE %s 
           OR skills_section LIKE %s 
           OR experience_section LIKE %s
        """
        
        search_pattern = f"%{search_term}%"
        results = self.execute_query(query, (search_pattern, search_pattern, search_pattern, search_pattern))
        
        applications = []
        for row in results:
            app = ApplicationDetail(
                detail_id=row[0],
                applicant_id=row[1],
                application_role=row[2] or "General Application",
                cv_path=row[3] or "",
                cv_raw_text=row[4] or "",
                summary_section=row[5] or "",
                skills_section=row[6] or "",
                experience_section=row[7] or "",
                education_section=row[8] or "",
                accomplishments_section=row[9] or ""
            )
            applications.append(app)
        
        return applications
    
    def get_database_stats(self) -> Dict[str, int]:
        stats = {}
        
        # Total applicants
        result = self.execute_query("SELECT COUNT(*) FROM ApplicantProfile")
        stats['total_applicants'] = result[0][0] if result else 0
        
        # Total applications
        result = self.execute_query("SELECT COUNT(*) FROM ApplicationDetail")
        stats['total_applications'] = result[0][0] if result else 0
        
        # Applications by role
        result = self.execute_query("""
            SELECT application_role, COUNT(*) as count 
            FROM ApplicationDetail 
            GROUP BY application_role 
            ORDER BY count DESC
        """)
        stats['applications_by_role'] = {row[0]: row[1] for row in result} if result else {}
        
        return stats
    
    def get_cv_texts_for_search(self) -> List[Tuple[int, str]]:
        query = "SELECT detail_id, cv_raw_text FROM ApplicationDetail WHERE cv_raw_text IS NOT NULL"
        results = self.execute_query(query)
        
        cv_data = []
        for row in results:
            detail_id, cv_text = row
            if cv_text and len(cv_text.strip()) > 0:
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


db_manager = DatabaseManager()

def get_database_connection():
    return db_manager

def test_database_connection():
    db = get_database_connection()
    
    if not db.connect():
        print("Failed to connect to database")
        return False
    
    print("Database connection successful!")
    
    # Get stats
    stats = db.get_database_stats()
    print(f"Database Statistics:")
    print(f"   Total Applicants: {stats['total_applicants']}")
    print(f"   Total Applications: {stats['total_applications']}")
    
    if stats['applications_by_role']:
        print("   Applications by Role:")
        for role, count in list(stats['applications_by_role'].items())[:5]:
            print(f"     - {role}: {count}")
    
    # Test getting some applications
    applications = db.get_all_applications()
    if applications:
        print(f"\n📄 Sample Applications (showing first 3):")
        for app in applications[:3]:
            print(f"   ID: {app.detail_id}, Role: {app.application_role}")
            print(f"   CV Length: {len(app.cv_raw_text)} characters")
            if app.skills_section:
                skills_preview = app.skills_section[:100] + "..." if len(app.skills_section) > 100 else app.skills_section
                print(f"   Skills: {skills_preview}")
            print()
    
    db.disconnect()
    return True

if __name__ == "__main__":
    print("🗄️ Testing Database Connection")
    print("=" * 40)
    test_database_connection()