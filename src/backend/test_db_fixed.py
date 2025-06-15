import mysql.connector
import os

def test_database_connection():
    print("🗄️ Testing database connection...")
    
    # Get password from environment or ask once
    password = os.getenv('MYSQL_PASSWORD')
    if not password:
        password = input("Enter MySQL Password: ")
    
    try:
        # Try connection with auth_plugin specified
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password=password,
            database="ats_db",
            auth_plugin='mysql_native_password'  # Fix for auth plugin issue
        )
        
        print("Database connected successfully!")
        
        # Test getting data
        cursor = connection.cursor()
        
        # Check if tables exist
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"Tables found: {[table[0] for table in tables]}")
        
        # Check data counts
        try:
            cursor.execute("SELECT COUNT(*) FROM ApplicantProfile")
            applicant_count = cursor.fetchone()[0]
            print(f"Applicants: {applicant_count}")
            
            cursor.execute("SELECT COUNT(*) FROM ApplicationDetail")
            application_count = cursor.fetchone()[0]
            print(f"Applications: {application_count}")
            
            if application_count > 0:
                print("Database has data - ready for testing!")
                return True
            else:
                print("Database is empty - need to run extractor.py first")
                return False
                
        except mysql.connector.Error as e:
            print(f"Tables might not exist: {e}")
            print("Run your extractor.py to create tables and data")
            return False
            
    except mysql.connector.Error as e:
        print(f"Database connection failed: {e}")
        
        if "auth_plugin" in str(e):
            print("\nAUTH PLUGIN FIX:")
            print("Try connecting to MySQL and run:")
            print("ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your_password';")
            print("FLUSH PRIVILEGES;")
        
        return False
        
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    test_database_connection()