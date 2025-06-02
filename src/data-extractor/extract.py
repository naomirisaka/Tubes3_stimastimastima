import os
import glob
from faker import Faker
from PyPDF2 import PdfReader
import mysql.connector

# ========================
# Konfigurasi Database (ubah sesuai MySQL kamu)
# ========================
DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "ats_db"

# Password minta input supaya fleksibel
DB_PASSWORD = input("Masukkan password MySQL user root: ")

# ========================
# SQL untuk buat tabel applicants
# ========================
create_table_sql = """
CREATE TABLE IF NOT EXISTS applicants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    phone VARCHAR(15),
    birthdate DATE,
    address TEXT,
    cv_text LONGTEXT,
    cv_path VARCHAR(255)
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
cursor.execute(create_table_sql)
db.commit()

# ========================
# Utility Faker dan fungsi bantu
# ========================
faker = Faker('id_ID')

def generate_phone():
    # 08 + 10 digit angka random
    return "08" + ''.join(faker.random_choices(elements='0123456789', length=10))

def generate_fake_data():
    return {
        "name": faker.name(),
        "phone": generate_phone(),
        "birthdate": faker.date_of_birth(minimum_age=22, maximum_age=60).isoformat(),
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

def insert_applicant(data, cv_text, path):
    cursor.execute("""
        INSERT INTO applicants (name, phone, birthdate, address, cv_text, cv_path)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        data['name'],
        data['phone'],
        data['birthdate'],
        data['address'],
        cv_text,
        path
    ))

# ========================
# Proses folder recursive cari PDF
# ========================
def process_folder(base_folder):
    pdf_files = glob.glob(os.path.join(base_folder, "**/*.pdf"), recursive=True)
    for path in pdf_files:
        print(f"Memproses: {path}")
        cv_text = extract_text_from_pdf(path)
        fake_data = generate_fake_data()
        insert_applicant(fake_data, cv_text, path)
        print(f"Disimpan: {fake_data['name']}")
    db.commit()
    print("Semua data berhasil dimasukkan ke database.")

# ========================
# Export data lengkap ke file SQL (buat backend bisa import)
# ========================
def export_data_to_sql(filename):
    cursor.execute("SELECT * FROM applicants")
    rows = cursor.fetchall()

    def escape_sql(val):
        if val is None:
            return "NULL"
        # Escape single quote dengan dua single quote untuk SQL string literal
        return "'" + str(val).replace("'", "''") + "'"

    with open(filename, "w", encoding="utf-8") as f:
        # Create database & use
        f.write(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};\n")
        f.write(f"USE {DB_NAME};\n\n")
        # Create table
        f.write(create_table_sql.strip() + ";\n\n")
        # Insert all rows
        for row in rows:
            id_, name, phone, birthdate, address, cv_text, cv_path = row

            bd_val = escape_sql(birthdate.isoformat() if birthdate else None)

            insert_stmt = (
                "INSERT INTO applicants (id, name, phone, birthdate, address, cv_text, cv_path) VALUES ("
                f"{id_}, {escape_sql(name)}, {escape_sql(phone)}, {bd_val}, "
                f"{escape_sql(address)}, {escape_sql(cv_text)}, {escape_sql(cv_path)});\n"
            )
            f.write(insert_stmt)

    print(f"[+] Data berhasil diexport ke file: {filename}")

# ========================
# Main
# ========================
if __name__ == "__main__":
    process_folder("data")               # scan folder data/ dan subfoldernya
    export_data_to_sql("../../data/ats.sql")  # generate file SQL lengkap di folder data/
    cursor.close()
    db.close()
