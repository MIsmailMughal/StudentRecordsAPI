-- IF NOT EXISTS keeps existing student records when the server restarts.
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),
    rollNo TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK(length(rollNo) BETWEEN 1 AND 30),
    department TEXT NOT NULL CHECK(length(trim(department)) BETWEEN 1 AND 100),
    semester INTEGER NOT NULL CHECK(typeof(semester) = 'integer' AND semester BETWEEN 1 AND 8)
);
