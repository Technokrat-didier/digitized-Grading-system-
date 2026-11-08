"""Automated tests for the School Grading Management System.

Run with:  python test_app.py
Uses a temporary database so your real school.db is never touched.
"""

import os
import tempfile
import unittest

import database as db

# Point the database at a temp file BEFORE importing the Flask app.
TEST_DB = os.path.join(tempfile.gettempdir(), "school_grading_test.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
db.DB_PATH = TEST_DB

import grading  # noqa: E402
from app import app  # noqa: E402


def register(client, name="Alice Example", adm="ADM001", cls="Form 3", year="2026"):
    return client.post(
        "/students/register",
        data={"full_name": name, "admission_number": adm, "class_name": cls, "academic_year": year},
        follow_redirects=True,
    )


def save_marks(client, student_id, subjects):
    return client.post(
        f"/students/{student_id}/marks",
        data={"subject_name": [s[0] for s in subjects], "marks": [s[1] for s in subjects]},
        follow_redirects=True,
    )


class GradingUnitTests(unittest.TestCase):
    def test_grade_boundaries(self):
        cases = {
            0: "F", 39: "F", 39.9: "F", 40: "E", 49: "E", 50: "D",
            59: "D", 60: "C", 69: "C", 70: "B", 79: "B", 80: "A", 100: "A",
        }
        for marks, expected in cases.items():
            self.assertEqual(grading.assign_grade(marks), expected, f"marks={marks}")

    def test_marks_validation(self):
        self.assertEqual(grading.validate_marks("72.5"), 72.5)
        self.assertEqual(grading.validate_marks(0), 0.0)
        self.assertEqual(grading.validate_marks(100), 100.0)
        for bad in ["-1", "101", "abc", "", None, "inf"]:
            with self.assertRaises(grading.ValidationError, msg=f"value={bad}"):
                grading.validate_marks(bad)

    def test_unrounded_average_for_mean_grade(self):
        # Average 79.5 must be grade B, not A (rounding first would give 80).
        subjects = [{"subject_name": "A", "marks": 79}, {"subject_name": "B", "marks": 80}]
        results = grading.compute_results(subjects)
        self.assertEqual(results["average"], 79.5)
        self.assertEqual(results["average_display"], "79.50")
        self.assertEqual(results["mean_grade"], "B")

    def test_tied_highest_and_lowest(self):
        subjects = [
            {"subject_name": "Math", "marks": 90},
            {"subject_name": "English", "marks": 90},
            {"subject_name": "History", "marks": 40},
            {"subject_name": "Geography", "marks": 40},
        ]
        self.assertEqual(grading.highest_subjects(subjects), ["Math", "English"])
        self.assertEqual(grading.lowest_subjects(subjects), ["History", "Geography"])

    def test_subject_rules(self):
        with self.assertRaises(grading.ValidationError):
            grading.validate_subjects([])  # no subjects
        with self.assertRaises(grading.ValidationError):
            grading.validate_subjects([(f"S{i}", 50) for i in range(9)])  # 9 subjects
        with self.assertRaises(grading.ValidationError):
            grading.validate_subjects([("Math", 50), ("math", 60)])  # duplicate
        with self.assertRaises(grading.ValidationError):
            grading.validate_subjects([("  ", 50)])  # empty name


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        # Fresh database for every test.
        conn = db.get_connection()
        conn.execute("DELETE FROM subjects")
        conn.execute("DELETE FROM students")
        conn.commit()
        conn.close()

    def test_register_and_view_student(self):
        response = register(self.client)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"registered successfully", response.data)
        students = db.list_students()
        self.assertEqual(len(students), 1)
        page = self.client.get("/students")
        self.assertIn(b"Alice Example", page.data)

    def test_register_multiple_students(self):
        register(self.client, "Alice", "A1")
        register(self.client, "Bob", "A2")
        register(self.client, "Carol", "A3")
        self.assertEqual(len(db.list_students()), 3)

    def test_duplicate_admission_number_rejected(self):
        register(self.client, "Alice", "A1")
        response = register(self.client, "Another Alice", "A1")
        self.assertIn(b"already registered", response.data)
        self.assertEqual(len(db.list_students()), 1)

    def test_missing_student_info_rejected(self):
        response = self.client.post(
            "/students/register",
            data={"full_name": "", "admission_number": "", "class_name": "", "academic_year": ""},
        )
        self.assertIn(b"is required", response.data)
        self.assertEqual(len(db.list_students()), 0)

    def test_eight_subjects_allowed(self):
        register(self.client)
        student = db.list_students()[0]
        subjects = [(f"Subject {i}", 50 + i) for i in range(8)]
        response = save_marks(self.client, student["id"], subjects)
        self.assertIn(b"Results saved successfully", response.data)
        self.assertEqual(len(db.get_subjects(student["id"])), 8)

    def test_ninth_subject_rejected(self):
        register(self.client)
        student = db.list_students()[0]
        subjects = [(f"Subject {i}", 50) for i in range(9)]
        response = save_marks(self.client, student["id"], subjects)
        self.assertIn(b"maximum of 8 subjects", response.data)
        self.assertEqual(len(db.get_subjects(student["id"])), 0)

    def test_boundary_marks_via_web(self):
        register(self.client)
        student = db.list_students()[0]
        for marks, should_pass in [("0", True), ("100", True), ("72.5", True),
                                   ("-1", False), ("101", False), ("abc", False), ("nan", False)]:
            response = save_marks(self.client, student["id"], [("Math", marks)])
            self.assertEqual(response.status_code, 200, f"marks={marks}")
            if should_pass:
                self.assertIn(b"Results saved successfully", response.data, f"marks={marks}")
            else:
                self.assertNotIn(b"Results saved successfully", response.data, f"marks={marks}")
                self.assertIn(b"flash-error", response.data, f"marks={marks}")

    def test_empty_subject_and_no_subjects_rejected(self):
        register(self.client)
        student = db.list_students()[0]
        response = save_marks(self.client, student["id"], [("", 50)])
        self.assertIn(b"cannot be empty", response.data)
        response = save_marks(self.client, student["id"], [])
        self.assertIn(b"at least one subject", response.data)

    def test_duplicate_subject_rejected(self):
        register(self.client)
        student = db.list_students()[0]
        response = save_marks(self.client, student["id"], [("Math", 50), ("MATH", 60)])
        self.assertIn(b"Duplicate subject", response.data)

    def test_results_report_content(self):
        register(self.client)
        student = db.list_students()[0]
        save_marks(self.client, student["id"], [("Mathematics", 85), ("English", 72), ("Computer Studies", 91)])
        response = self.client.get(f"/students/{student['id']}/results")
        self.assertEqual(response.status_code, 200)
        for expected in [b"Mathematics", b"85", b"248", b"82.67", b"Computer Studies", b"English", b"Print Results"]:
            self.assertIn(expected, response.data)
        # Mean grade A from unrounded average 82.666...
        self.assertIn(b'grade-A', response.data)

    def test_results_without_subjects_redirects(self):
        register(self.client)
        student = db.list_students()[0]
        response = self.client.get(f"/students/{student['id']}/results")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/marks", response.headers["Location"])

    def test_edit_student_info(self):
        register(self.client)
        student = db.list_students()[0]
        response = self.client.post(
            f"/students/{student['id']}/edit",
            data={"full_name": "Alice Updated", "admission_number": "ADM001",
                  "class_name": "Form 4", "academic_year": "2026"},
            follow_redirects=True,
        )
        self.assertIn(b"updated", response.data)
        self.assertEqual(db.get_student(student["id"])["full_name"], "Alice Updated")

    def test_edit_marks_recalculates(self):
        register(self.client)
        student = db.list_students()[0]
        save_marks(self.client, student["id"], [("Math", 85), ("English", 72)])
        save_marks(self.client, student["id"], [("Math", 30), ("English", 40)])
        subjects = db.get_subjects(student["id"])
        self.assertEqual(len(subjects), 2)
        results = grading.compute_results(subjects)
        self.assertEqual(results["average_display"], "35.00")
        self.assertEqual(results["mean_grade"], "F")

    def test_delete_student_cascades(self):
        register(self.client)
        student = db.list_students()[0]
        save_marks(self.client, student["id"], [("Math", 85)])
        response = self.client.post(f"/students/{student['id']}/delete", follow_redirects=True)
        self.assertIn(b"deleted", response.data)
        self.assertEqual(db.list_students(), [])
        self.assertEqual(db.get_subjects(student["id"]), [])

    def test_search(self):
        register(self.client, "Alice Example", "A1")
        register(self.client, "Bob Builder", "B2")
        page = self.client.get("/students?q=alice")
        self.assertIn(b"Alice Example", page.data)
        self.assertNotIn(b"Bob Builder", page.data)
        page = self.client.get("/students?q=B2")
        self.assertIn(b"Bob Builder", page.data)

    def test_dashboard_statistics(self):
        register(self.client, "Alice", "A1")
        register(self.client, "Bob", "A2")
        alice, bob = db.list_students()
        save_marks(self.client, alice["id"], [("Math", 90)])
        save_marks(self.client, bob["id"], [("Math", 50)])
        page = self.client.get("/")
        self.assertIn(b"Registered Students", page.data)
        self.assertIn(b"70.00", page.data)  # overall average of 90 and 50
        self.assertIn(b"Alice", page.data)

    def test_settings_school_name(self):
        response = self.client.post(
            "/settings", data={"school_name": "Test Valley High"}, follow_redirects=True
        )
        self.assertIn(b"Settings saved", response.data)
        page = self.client.get("/")
        self.assertIn(b"Test Valley High", page.data)
        response = self.client.post("/settings", data={"school_name": "  "})
        self.assertIn(b"cannot be empty", response.data)

    def test_404_for_unknown_student(self):
        response = self.client.get("/students/9999/results")
        self.assertEqual(response.status_code, 404)

    def test_persistence_across_connections(self):
        register(self.client)
        student = db.list_students()[0]
        save_marks(self.client, student["id"], [("Math", 85)])
        # Simulate closing and reopening the app: brand-new connection reads disk.
        fresh = db.get_connection()
        count = fresh.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        marks = fresh.execute("SELECT marks FROM subjects").fetchone()[0]
        fresh.close()
        self.assertEqual(count, 1)
        self.assertEqual(marks, 85.0)
        self.assertTrue(os.path.exists(TEST_DB))


if __name__ == "__main__":
    unittest.main(verbosity=2)