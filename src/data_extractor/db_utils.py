import mysql.connector
from typing import Optional
import os

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": "ats_db"
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def get_all_cv_paths():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT cv_path FROM ApplicationDetail")
    paths = [str(row["cv_path"]) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return paths

def get_applicant_id_by_cv(cv_path: str) -> Optional[int]:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT applicant_id FROM ApplicationDetail WHERE cv_path = %s", (cv_path,))
    row: dict = cursor.fetchone()
    cursor.close()
    conn.close()
    return row.get("applicant_id") if row else None

def get_summary_by_applicant(applicant_id: int) -> Optional[dict]:
    conn = get_connection()
    
    cursor1 = conn.cursor(dictionary=True)
    cursor1.execute("SELECT * FROM ApplicantProfile WHERE applicant_id = %s", (applicant_id,))
    profile = cursor1.fetchone()
    cursor1.nextset()  # 🔥 ini penting!
    cursor1.close()

    cursor2 = conn.cursor(dictionary=True)
    cursor2.execute("SELECT * FROM ApplicationDetail WHERE applicant_id = %s", (applicant_id,))
    details = cursor2.fetchone()
    cursor2.nextset()  # 🔥 tambahkan juga
    cursor2.close()

    conn.close()

    if not profile or not details:
        return None

    return {
        "first_name": profile.get("first_name", ""),
        "last_name": profile.get("last_name", ""),
        "phone": profile.get("phone_number", ""),
        "address": profile.get("address", ""),
        "summary": details.get("summary_section", ""),
        "skills": details.get("skills_section", ""),
        "experience": details.get("experience_section", ""),
        "education": details.get("education_section", ""),
        "accomplishments": details.get("accomplishments_section", "")
    }