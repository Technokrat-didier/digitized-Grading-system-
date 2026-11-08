"""School Grading Management System - Flask application.

Run with:  python app.py
Then open: http://127.0.0.1:5000
"""

from flask import Flask, flash, redirect, render_template, request, url_for

import database as db
import grading

app = Flask(__name__)
# Used to sign flash messages / session cookies. Change for production use.
app.secret_key = "school-grading-system-dev-key"

# Create the database tables automatically on startup.
db.init_db()


@app.template_filter("fmt_mark")
def fmt_mark(value):
    """Show 85.0 as '85' and 72.5 as '72.5'.

    Invalid input (e.g. 'abc') is echoed back unchanged so the user can
    see and correct what they typed after a validation error.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number != number or number in (float("inf"), float("-inf")):
        return str(value)
    if number == int(number):
        return str(int(number))
    return f"{number:g}"


@app.context_processor
def inject_school_name():
    """Make the configurable school name available in every template."""
    return {"school_name": db.get_setting("school_name", "Springfield Secondary School")}


def validate_student_form(form, exclude_id=None):
    """Validate student info fields. Returns (data, errors)."""
    data = {
        "full_name": form.get("full_name", "").strip(),
        "admission_number": form.get("admission_number", "").strip(),
        "class_name": form.get("class_name", "").strip(),
        "academic_year": form.get("academic_year", "").strip(),
    }
    errors = []
    labels = {
        "full_name": "Full name",
        "admission_number": "Admission number",
        "class_name": "Class/Form",
        "academic_year": "academic year",
    }
    for field, label in labels.items():
        if not data[field]:
            errors.append(f"{label} is required.")
    if data["admission_number"] and db.admission_number_exists(
        data["admission_number"], exclude_id=exclude_id
    ):
        errors.append(
            f"Admission number '{data['admission_number']}' is already registered."
        )
    return data, errors


def student_rows(search=None):
    """Student list enriched with average and mean grade for tables."""
    students = db.list_students(search)
    subjects_by_student = {}
    for subject in db.get_all_subjects():
        subjects_by_student.setdefault(subject["student_id"], []).append(subject)

    rows = []
    for student in students:
        subjects = subjects_by_student.get(student["id"], [])
        results = grading.compute_results(subjects) if subjects else None
        rows.append({"student": student, "results": results})
    return rows


# ------------------------------------------------------------------ pages

@app.route("/")
def dashboard():
    rows = student_rows()
    with_results = [r for r in rows if r["results"]]
    overall_average = None
    top_student = None
    if with_results:
        overall_average = sum(r["results"]["average"] for r in with_results) / len(with_results)
        top_student = max(with_results, key=lambda r: r["results"]["average"])
    return render_template(
        "dashboard.html",
        rows=rows,
        total_students=len(rows),
        students_with_results=len(with_results),
        overall_average=f"{overall_average:.2f}" if overall_average is not None else None,
        top_student=top_student,
        active_page="dashboard",
    )


@app.route("/students/register", methods=["GET", "POST"])
def register_student():
    data = {"full_name": "", "admission_number": "", "class_name": "", "academic_year": ""}
    if request.method == "POST":
        data, errors = validate_student_form(request.form)
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            student_id = db.create_student(**data)
            flash(f"Student '{data['full_name']}' registered successfully.", "success")
            return redirect(url_for("enter_marks", student_id=student_id))
    return render_template("register_student.html", data=data, active_page="register")


@app.route("/students")
def students():
    search = request.args.get("q", "").strip()
    return render_template(
        "students.html",
        rows=student_rows(search or None),
        search=search,
        active_page="students",
        page_title="Student Records",
    )


@app.route("/results")
def results_and_reports():
    rows = [r for r in student_rows() if r["results"]]
    rows.sort(key=lambda r: r["results"]["average"], reverse=True)
    return render_template(
        "results_list.html", rows=rows, active_page="results", page_title="Results & Reports"
    )


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def edit_student(student_id):
    student = db.get_student(student_id)
    if student is None:
        return render_template("404.html"), 404
    data = student
    if request.method == "POST":
        data, errors = validate_student_form(request.form, exclude_id=student_id)
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            db.update_student(student_id, **data)
            flash("Student information updated.", "success")
            return redirect(url_for("students"))
    return render_template("edit_student.html", student=student, data=data, active_page="students")


@app.route("/students/<int:student_id>/delete", methods=["POST"])
def delete_student(student_id):
    student = db.get_student(student_id)
    if student is None:
        return render_template("404.html"), 404
    db.delete_student(student_id)
    flash(f"Student '{student['full_name']}' and their subject records were deleted.", "success")
    return redirect(url_for("students"))


@app.route("/students/<int:student_id>/marks", methods=["GET", "POST"])
def enter_marks(student_id):
    student = db.get_student(student_id)
    if student is None:
        return render_template("404.html"), 404

    if request.method == "POST":
        names = request.form.getlist("subject_name")
        marks = request.form.getlist("marks")
        if len(names) != len(marks):
            flash("Invalid form submission: subject and marks fields do not match.", "error")
        else:
            try:
                subjects = grading.validate_subjects(list(zip(names, marks)))
            except grading.ValidationError as exc:
                flash(str(exc), "error")
            else:
                db.save_subjects(student_id, subjects)
                flash("Results saved successfully.", "success")
                return redirect(url_for("student_results", student_id=student_id))
        # Re-display what the user typed so nothing is lost on error.
        subjects = [{"subject_name": n, "marks": m} for n, m in zip(names, marks)]
    else:
        subjects = db.get_subjects(student_id)

    return render_template(
        "enter_marks.html", student=student, subjects=subjects,
        max_subjects=grading.MAX_SUBJECTS, active_page="students",
    )


@app.route("/students/<int:student_id>/results")
def student_results(student_id):
    student = db.get_student(student_id)
    if student is None:
        return render_template("404.html"), 404
    subjects = db.get_subjects(student_id)
    if not subjects:
        flash("No results recorded yet. Enter subject marks first.", "error")
        return redirect(url_for("enter_marks", student_id=student_id))
    return render_template(
        "results.html", student=student, results=grading.compute_results(subjects),
        active_page="results",
    )


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        name = request.form.get("school_name", "").strip()
        if not name:
            flash("School name cannot be empty.", "error")
        else:
            db.set_setting("school_name", name)
            flash("Settings saved.", "success")
            return redirect(url_for("settings"))
    return render_template("settings.html", active_page="settings")


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html", active_page=""), 404


if __name__ == "__main__":
    # debug=False so the app behaves like a normal production-style server.
    app.run(host="127.0.0.1", port=5000, debug=False)