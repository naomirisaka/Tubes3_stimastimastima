-- database_setup.sql
-- Database schema untuk ATS system

CREATE DATABASE IF NOT EXISTS ats_db;
USE ats_db;

-- Tabel untuk menyimpan profil pelamar
CREATE TABLE ApplicantProfile (
    applicant_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    address TEXT,
    phone_number VARCHAR(20),
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Tabel untuk menyimpan detail aplikasi dan CV
CREATE TABLE ApplicationDetail (
    detail_id INT AUTO_INCREMENT PRIMARY KEY,
    applicant_id INT NOT NULL,
    application_role VARCHAR(150) DEFAULT 'General',
    cv_path TEXT NOT NULL,
    cv_raw_text LONGTEXT,
    summary_section TEXT,
    skills_section TEXT,
    experience_section TEXT,
    education_section TEXT,
    accomplishments_section TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    extraction_status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
    extraction_timestamp TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (applicant_id) REFERENCES ApplicantProfile(applicant_id) ON DELETE CASCADE
);

-- Indexes untuk optimasi query
CREATE INDEX idx_applicant_name ON ApplicantProfile(first_name, last_name);
CREATE INDEX idx_application_role ON ApplicationDetail(application_role);
CREATE INDEX idx_extraction_status ON ApplicationDetail(extraction_status);
CREATE INDEX idx_cv_path ON ApplicationDetail(cv_path(255));

-- Sample data untuk testing (sesuai dengan tugas besar)
INSERT INTO ApplicantProfile (first_name, last_name, date_of_birth, address, phone_number) VALUES
('John', 'Doe', '1990-05-15', '123 Tech Street, Silicon Valley, CA', '+1-555-0123'),
('Jane', 'Smith', '1988-08-22', '456 Code Avenue, Seattle, WA', '+1-555-0124'),
('Michael', 'Johnson', '1992-03-10', '789 Developer Lane, Austin, TX', '+1-555-0125'),
('Sarah', 'Williams', '1985-11-30', '321 Programming Blvd, Boston, MA', '+1-555-0126'),
('David', 'Brown', '1991-07-18', '654 Software Circle, Denver, CO', '+1-555-0127'),
('Lisa', 'Davis', '1989-12-05', '987 Algorithm Way, Portland, OR', '+1-555-0128'),
('Robert', 'Wilson', '1987-04-14', '147 Data Science Dr, Chicago, IL', '+1-555-0129'),
('Emily', 'Taylor', '1993-09-27', '258 Machine Learning St, NYC, NY', '+1-555-0130'),
('James', 'Anderson', '1986-02-12', '369 Cloud Computing Ave, Miami, FL', '+1-555-0131'),
('Ashley', 'Thomas', '1994-06-08', '741 Frontend Rd, Los Angeles, CA', '+1-555-0132');

-- Sample application details dengan path CV yang sesuai struktur tugas
INSERT INTO ApplicationDetail (applicant_id, application_role, cv_path, cv_raw_text, summary_section, skills_section, experience_section, education_section, accomplishments_section, extraction_status) VALUES
(1, 'Software Engineer', 'data/ENGINEERING/10276858.pdf', 'Experienced software engineer with expertise in Python, Java, and web development...', 'Passionate software engineer with 5+ years experience', 'Python, Java, JavaScript, React, Node.js, SQL, Git', 'Senior Software Engineer at TechCorp (2020-2023), Software Developer at StartupXYZ (2018-2020)', 'B.S. Computer Science, Stanford University (2018)', 'Led development of microservices architecture, Increased system performance by 40%', 'completed'),
(2, 'Data Scientist', 'data/DATASCI/11234567.pdf', 'Data scientist with strong background in machine learning and statistical analysis...', 'Data scientist specializing in predictive analytics', 'Python, R, Machine Learning, TensorFlow, pandas, SQL, Tableau', 'Data Scientist at DataTech Inc (2019-2023), Junior Analyst at Research Corp (2017-2019)', 'M.S. Data Science, MIT (2017), B.S. Mathematics, UC Berkeley (2015)', 'Published 3 research papers, Built recommendation system serving 1M+ users', 'completed'),
(3, 'Frontend Developer', 'data/ENGINEERING/12345678.pdf', 'Frontend developer specializing in modern web technologies and user experience...', 'Creative frontend developer with eye for design', 'JavaScript, TypeScript, React, Vue.js, HTML5, CSS3, Sass', 'Frontend Developer at WebStudio (2020-2023), UI Developer at DesignCorp (2018-2020)', 'B.A. Web Design, Art Institute (2018)', 'Redesigned company website increasing conversion by 25%', 'completed'),
(4, 'Backend Developer', 'data/ENGINEERING/13149176.pdf', 'Backend developer with expertise in server-side technologies and database design...', 'Backend developer focused on scalable systems', 'Python, Java, Node.js, PostgreSQL, MongoDB, Docker, Kubernetes', 'Backend Developer at CloudTech (2019-2023), Junior Developer at ServerSoft (2017-2019)', 'B.S. Computer Engineering, Carnegie Mellon (2017)', 'Designed distributed system handling 100K+ concurrent users', 'completed'),
(5, 'DevOps Engineer', 'data/ENGINEERING/14567890.pdf', 'DevOps engineer with experience in cloud infrastructure and automation...', 'DevOps engineer passionate about automation', 'AWS, Docker, Kubernetes, Terraform, Jenkins, Python, Linux', 'DevOps Engineer at CloudFirst (2020-2023), System Administrator at TechOps (2018-2020)', 'B.S. Information Technology, Georgia Tech (2018)', 'Reduced deployment time by 80% through automation', 'completed'),
(6, 'Product Manager', 'data/BUSINESS/15678901.pdf', 'Product manager with track record of successful product launches...', 'Strategic product manager with technical background', 'Product Strategy, Agile, Scrum, SQL, Analytics, A/B Testing', 'Senior Product Manager at ProductCorp (2020-2023), Product Analyst at StartupABC (2018-2020)', 'MBA, Harvard Business School (2018), B.S. Engineering, Stanford (2016)', 'Launched 3 successful products generating $50M+ revenue', 'completed'),
(7, 'UX Designer', 'data/DESIGN/16789012.pdf', 'UX designer focused on user-centered design and research...', 'User-centered designer with research expertise', 'Figma, Sketch, Adobe Creative Suite, User Research, Prototyping', 'Senior UX Designer at DesignLab (2019-2023), UX Researcher at UserFirst (2017-2019)', 'M.A. Human-Computer Interaction, Carnegie Mellon (2017)', 'Improved user satisfaction scores by 35% through redesign', 'completed'),
(8, 'Machine Learning Engineer', 'data/DATASCI/17890123.pdf', 'ML engineer specializing in production machine learning systems...', 'ML engineer bridging research and production', 'Python, TensorFlow, PyTorch, MLflow, Kubernetes, AWS, SQL', 'ML Engineer at AITech (2020-2023), Data Scientist at MLCorp (2018-2020)', 'M.S. Machine Learning, Stanford (2018), B.S. Computer Science, MIT (2016)', 'Deployed ML models serving 10M+ predictions daily', 'completed'),
(9, 'Security Engineer', 'data/ENGINEERING/18901234.pdf', 'Security engineer with expertise in cybersecurity and threat analysis...', 'Cybersecurity expert protecting digital assets', 'Network Security, Penetration Testing, CISSP, Python, Linux', 'Security Engineer at SecureTech (2019-2023), Security Analyst at CyberGuard (2017-2019)', 'M.S. Cybersecurity, Carnegie Mellon (2017), B.S. Computer Science, CalTech (2015)', 'Prevented 99.9% of security incidents, Certified Ethical Hacker', 'completed'),
(10, 'QA Engineer', 'data/ENGINEERING/19012345.pdf', 'Quality assurance engineer ensuring software reliability and performance...', 'QA engineer committed to software quality', 'Selenium, Jest, Python, Java, Test Automation, Performance Testing', 'Senior QA Engineer at QualityFirst (2020-2023), QA Analyst at TestCorp (2018-2020)', 'B.S. Software Engineering, University of Washington (2018)', 'Reduced bug reports by 60% through comprehensive testing', 'completed');

-- View untuk menampilkan data yang sudah di-join
CREATE VIEW cv_search_view AS
SELECT 
    ad.detail_id,
    ad.applicant_id,
    CONCAT(ap.first_name, ' ', ap.last_name) as applicant_name,
    ap.phone_number,
    ap.address,
    ad.application_role,
    ad.cv_path,
    ad.cv_raw_text,
    ad.summary_section,
    ad.skills_section,
    ad.experience_section,
    ad.education_section,
    ad.accomplishments_section,
    ad.extraction_status,
    ad.created_at
FROM ApplicationDetail ad
JOIN ApplicantProfile ap ON ad.applicant_id = ap.applicant_id
WHERE ad.extraction_status = 'completed';

-- Stored procedure untuk statistik
DELIMITER //
CREATE PROCEDURE GetATSStatistics()
BEGIN
    SELECT 
        COUNT(DISTINCT ap.applicant_id) as total_applicants,
        COUNT(ad.detail_id) as total_applications,
        COUNT(CASE WHEN ad.extraction_status = 'completed' THEN 1 END) as completed_extractions,
        COUNT(CASE WHEN ad.extraction_status = 'pending' THEN 1 END) as pending_extractions,
        COUNT(CASE WHEN ad.extraction_status = 'failed' THEN 1 END) as failed_extractions
    FROM ApplicantProfile ap
    LEFT JOIN ApplicationDetail ad ON ap.applicant_id = ad.applicant_id;
    
    SELECT 
        application_role,
        COUNT(*) as count
    FROM ApplicationDetail
    WHERE application_role IS NOT NULL
    GROUP BY application_role
    ORDER BY count DESC;
END //
DELIMITER ;

-- Trigger untuk update timestamp
DELIMITER //
CREATE TRIGGER update_applicant_timestamp 
    BEFORE UPDATE ON ApplicantProfile 
    FOR EACH ROW 
    SET NEW.updated_at = CURRENT_TIMESTAMP;
//

CREATE TRIGGER update_application_timestamp 
    BEFORE UPDATE ON ApplicationDetail 
    FOR EACH ROW 
    SET NEW.updated_at = CURRENT_TIMESTAMP;
//
DELIMITER ;

-- Grant permissions untuk user aplikasi
-- Ganti 'ats_user' dengan username yang akan digunakan aplikasi
-- CREATE USER 'ats_user'@'localhost' IDENTIFIED BY 'your_password_here';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ats_db.* TO 'ats_user'@'localhost';
-- FLUSH PRIVILEGES;

-- Verification queries
SELECT 'Database setup completed successfully!' as status;
SELECT COUNT(*) as total_applicants FROM ApplicantProfile;
SELECT COUNT(*) as total_applications FROM ApplicationDetail;
SELECT application_role, COUNT(*) as count FROM ApplicationDetail GROUP BY application_role;