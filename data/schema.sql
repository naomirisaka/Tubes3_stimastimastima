CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    skills TEXT
);

INSERT INTO users (id, name, email, skills) VALUES
(1, 'Alice', 'alice@example.com', 'React, HTML, CSS, JavaScript'),
(2, 'Bob', 'bob@example.com', 'Next.js, HTML, React'),
(3, 'Charlie', 'charlie@example.com', 'Vue, Tailwind, HTML');

CREATE TABLE frameworks (
    id INT PRIMARY KEY,
    name VARCHAR(50),
    description TEXT
);

INSERT INTO frameworks (id, name, description) VALUES
(1, 'React', 'A JavaScript library for building user interfaces'),
(2, 'Next.js', 'A React framework for server-rendered apps'),
(3, 'HTML', 'Standard markup language for documents designed to be displayed in a web browser');

SELECT * FROM users WHERE skills LIKE '%React%';
