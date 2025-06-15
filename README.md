# <p align = center>Tugas Besar 3 IF2211 Strategi Algoritma</p>
# <p align = center>Pemanfaatan Pattern Matching untuk Membangun Sistem ATS (Applicant Tracking System) Berbasis CV Digital</p>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/PyMuPDF-latest-4D4D4D?logo=acrobatreader&logoColor=white" />
  <img src="https://img.shields.io/badge/Flet-latest-009688?logo=flutter&logoColor=white" />
  <img src="https://img.shields.io/badge/MySQL-8.x-4479A1?logo=mysql&logoColor=white" />
</p>

![image](https://github.com/user-attachments/assets/9417d9a5-113f-4ca5-aa94-cd919a667d39)

### Kelompok 32: stimastimastima
| Nama | NIM |
|------|-----|
| Jessica Allen | 13523057 |
| Anella Utari Gunadi | 13523078 |
| Naomi Risaka Sitorus | 13523122 |

## Deskripsi
Matchify adalah aplikasi ATS (Applicant Tracking System) berbasis desktop yang mampu mencocokkan CV pelamar dengan kata kunci tertentu menggunakan algoritma pencocokan string. 
Tujuannya adalah membantu recruiter menemukan kandidat yang paling relevan secara otomatis dan efisien dari kumpulan CV digital.

## Fitur
### 1. Algoritma Knuth-Morris-Pratt (KMP)
Algoritma Knuth-Morris-Pratt (KMP) adalah algoritma pencocokan string yang menghindari pemeriksaan ulang karakter yang sudah diperiksa sebelumnya. 
Algoritma ini bekerja dengan membangun prefix table (failure function) untuk mempercepat proses pencarian pola di dalam teks.
### 2.  Algoritma Boyer-Moore (BM)
Algoritma Boyer-Moore (BM) adalah salah satu algoritma string matching tercepat untuk teks panjang. 
Algoritma ini membandingkan pola dari kanan ke kiri dan menggunakan dua strategi utama, yaitu bad character rule dan good suffix rule.

## Requirements
- Python 3.10 atau lebih baru
- pip
- MySQL 8.0 atau lebih baru
- Package Python dalam "requirements.txt", seperti PyMuPDF, Flet, dan mysql-connector-python
  
## Cara Menjalankan
1. Clone repository ini dengan menjalankan perintah di bawah ini pada terminal IDE yang mendukung Go:
   ```sh
   git clone https://github.com/naomirisaka/Tubes3_stimastimastima.git
2. Buka folder hasil clone di IDE.
3. Lakukan instalasi requirements Matchify dengan:
   ```sh
   pip install -r requirements.txt
4. Pindah ke directory src dengan:
   ```sh
   cd src
5. Jalankan Matchify lewat terminal dengan:
    ```sh
    python -m frontend.main