"""SQLite database layer for the School Grading Management System.

The database file (school.db) is created automatically on first run.
Subject marks are stored individually; totals and averages are always
calculated from them so results can never drift out of sync.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "school.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    admission_number TEXT NOT NULL UNIQUE,
    class_name TEXT NOT NULL,
    academic_year TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject_name TEXT NOT NULL,
    marks REAL NOT NULL CHECK (marks >= 0 AND marks <= 100),
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    UNIQUE (student_id, subject_name)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def get_connection():
    """Open a connection with dict-like rows and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they do not exist and set default settings."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('school_name', 'Springfield Secondary School')"
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- students

def create_student(full_name, admission_number, class_name, academic_year):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO students (full_name, admission_number, class_name, academic_year) "
            "VALUES (?, ?, ?, ?)",
            (full_name, admission_number, class_name, academic_year),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_student(student_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def admission_number_exists(admission_number, exclude_id=None):
    conn = get_connection()
    try:
        if exclude_id is None:
            row = conn.execute(
                "SELECT id FROM students WHERE admission_number = ? COLLATE NOCASE",
                (admission_number,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id FROM students WHERE admission_number = ? COLLATE NOCASE AND id != ?",
                (admission_number, exclude_id),
            ).fetchone()
        return row is not None
    finally:
        conn.close()


def list_students(search=None):
    """All students, optionally filtered by name or admission number."""
    conn = get_connection()
    try:
        if search:
            pattern = f"%{search}%"
            rows = conn.execute(
                "SELECT * FROM students WHERE full_name LIKE ? OR admission_number LIKE ? "
                "ORDER BY full_name",
                (pattern, pattern),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM students ORDER BY full_name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_student(student_id, full_name, admission_number, class_name, academic_year):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE students SET full_name = ?, admission_number = ?, class_name = ?, "
            "academic_year = ? WHERE id = ?",
            (full_name, admission_number, class_name, academic_year, student_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_student(student_id):
    """Delete a student; ON DELETE CASCADE removes their subjects too."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- subjects

def get_subjects(student_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT subject_name, marks FROM subjects WHERE student_id = ? ORDER BY id",
            (student_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_subjects():
    """Every subject row, used to build dashboard statistics."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT student_id, subject_name, marks FROM subjects ORDER BY student_id, id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_subjects(student_id, subjects):
    """Replace a student's subjects with a validated list, atomically."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM subjects WHERE student_id = ?", (student_id,))
        conn.executemany(
            "INSERT INTO subjects (student_id, subject_name, marks) VALUES (?, ?, ?)",
            [(student_id, s["subject_name"], s["marks"]) for s in subjects],
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- settings

def get_setting(key, default=""):
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key, value):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()