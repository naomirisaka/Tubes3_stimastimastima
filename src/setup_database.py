#!/usr/bin/env python3
"""
Simple SQL File Executor for ATS System
Just reads and executes the ats.sql file.
"""

import os
import sys
import mysql.connector
import getpass

def get_mysql_connection():
    """Get MySQL connection"""
    print("🔗 Connecting to MySQL...")
    
    host = input("MySQL Host (default: localhost): ").strip() or "localhost"
    user = input("MySQL Username (default: root): ").strip() or "root"
    
    # Try without password first
    try:
        connection = mysql.connector.connect(host=host, user=user)
        print("✅ Connected without password")
        return connection
    except mysql.connector.Error:
        pass
    
    # Ask for password
    password = getpass.getpass("MySQL Password: ")
    
    try:
        connection = mysql.connector.connect(host=host, user=user, password=password)
        print("✅ Connected with password")
        return connection
    except mysql.connector.Error as e:
        print(f"❌ Failed to connect: {e}")
        return None

def execute_sql_file(connection, sql_file):
    """Execute SQL file with better error handling"""
    print(f"📄 Reading SQL file: {sql_file}")
    
    try:
        with open(sql_file, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        print(f"📊 File size: {len(sql_content)} characters")
        
        cursor = connection.cursor()
        
        # Enable multi-statement execution
        cursor = connection.cursor()
        
        # Split into statements - simple approach
        statements = []
        current = ""
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('--') or line.startswith('#'):
                continue
            
            current += line + " "
            
            # End of statement
            if line.endswith(';'):
                statements.append(current.strip())
                current = ""
        
        # Add any remaining content
        if current.strip():
            statements.append(current.strip())
        
        print(f"🔢 Found {len(statements)} SQL statements")
        
        # Execute each statement
        for i, stmt in enumerate(statements, 1):
            stmt = stmt.strip()
            if not stmt:
                continue
                
            print(f"⚙️ Executing statement {i}: {stmt[:60]}{'...' if len(stmt) > 60 else ''}")
            
            try:
                # Execute single statement
                cursor.execute(stmt)
                connection.commit()
                
            except mysql.connector.Error as e:
                # Check if it's a "duplicate key" or "table doesn't exist" error
                if e.errno == 1061:  # Duplicate key name
                    print(f"   ⚠️ Skipping duplicate index creation")
                    continue
                elif e.errno == 1146:  # Table doesn't exist
                    print(f"   ❌ Table doesn't exist - this might be a problem with the SQL file")
                    print(f"   Error: {e}")
                    
                    # Ask if user wants to continue
                    response = input("   Continue anyway? (y/N): ")
                    if response.lower() not in ['y', 'yes']:
                        return False
                    continue
                elif e.errno == 1062:  # Duplicate entry
                    print(f"   ⚠️ Skipping duplicate data insertion")
                    continue
                else:
                    print(f"   ❌ Error: {e}")
                    response = input("   Continue with remaining statements? (y/N): ")
                    if response.lower() not in ['y', 'yes']:
                        return False
                    continue
        
        print("✅ SQL file executed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error reading/executing SQL file: {e}")
        return False

def check_tables(connection):
    """Check what tables exist and their content"""
    print("\n🔍 Checking database content...")
    
    try:
        cursor = connection.cursor()
        
        # Use the database
        cursor.execute("USE ats_db")
        
        # Show tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        if not tables:
            print("❌ No tables found")
            return
        
        print(f"📊 Found {len(tables)} table(s):")
        
        for table_tuple in tables:
            table_name = table_tuple[0]
            
            # Count rows
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            print(f"   📋 {table_name}: {row_count} rows")
            
            # Show some sample data if it's a main table
            if 'applicant' in table_name.lower() or 'application' in table_name.lower():
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                
                if rows:
                    # Get column names
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = [col[0] for col in cursor.fetchall()]
                    
                    print(f"      Sample data:")
                    for row in rows:
                        # Show first few columns only
                        sample_data = []
                        for i, col_name in enumerate(columns[:3]):
                            value = str(row[i])[:30] + "..." if len(str(row[i])) > 30 else str(row[i])
                            sample_data.append(f"{col_name}: {value}")
                        print(f"        {' | '.join(sample_data)}")
        
    except mysql.connector.Error as e:
        print(f"❌ Error checking tables: {e}")

def main():
    """Main function"""
    print("🎯 Simple SQL File Executor")
    print("=" * 40)
    
    # Find ats.sql file
    possible_locations = [
        "ats.sql",
        "../data/ats.sql", 
        "data/ats.sql",
        "../ats.sql"
    ]
    
    sql_file = None
    for location in possible_locations:
        if os.path.exists(location):
            sql_file = location
            break
    
    if not sql_file:
        print("❌ ats.sql file not found!")
        print("Searched in:")
        for loc in possible_locations:
            print(f"   - {loc}")
        sys.exit(1)
    
    print(f"📁 Found SQL file: {sql_file}")
    
    # Connect to MySQL
    connection = get_mysql_connection()
    if not connection:
        sys.exit(1)
    
    try:
        # Execute the SQL file
        if execute_sql_file(connection, sql_file):
            print("\n🎉 SQL file executed!")
            
            # Check what we got
            check_tables(connection)
            
            print("\nYou can now run your ATS application!")
        else:
            print("\n❌ SQL execution failed!")
            
    finally:
        connection.close()
        print("\n🔒 Connection closed")

if __name__ == "__main__":
    main()