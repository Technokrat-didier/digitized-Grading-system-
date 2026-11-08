"""Grading logic for the School Grading Management System.

All calculation rules live here so they can be reused and tested
independently of the Flask routes.
"""

MIN_MARKS = 0
MAX_MARKS = 100
MAX_SUBJECTS = 8

# Grading scale: (minimum marks, grade). Checked from highest to lowest.
GRADE_SCALE = [
    (80, "A"),
    (70, "B"),
    (60, "C"),
    (50, "D"),
    (40, "E"),
    (0, "F"),
]


class ValidationError(ValueError):
    """Raised when user input fails validation."""


def validate_marks(value):
    """Convert a raw marks value to a float between 0 and 100.

    Accepts decimal marks (e.g. 72.5). Raises ValidationError with a
    clear message for empty, non-numeric or out-of-range values.
    """
    if value is None or str(value).strip() == "":
        raise ValidationError("Marks cannot be empty.")
    try:
        marks = float(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"Marks must be a number (got '{value}').")
    if marks != marks or marks in (float("inf"), float("-inf")):
        raise ValidationError("Marks must be a finite number.")
    if marks < MIN_MARKS:
        raise ValidationError(f"Marks cannot be negative (got {value}).")
    if marks > MAX_MARKS:
        raise ValidationError(f"Marks cannot exceed {MAX_MARKS} (got {value}).")
    return marks


def assign_grade(marks):
    """Return the letter grade for a score using the grading scale."""
    for minimum, grade in GRADE_SCALE:
        if marks >= minimum:
            return grade
    return "F"


def calculate_total(subjects):
    """Sum the marks of all subjects. `subjects` is a list of dicts
    with 'subject_name' and 'marks' keys."""
    return sum(s["marks"] for s in subjects)


def calculate_average(subjects):
    """Total marks divided by the number of subjects (unrounded)."""
    if not subjects:
        raise ValidationError("A student must have at least one subject.")
    return calculate_total(subjects) / len(subjects)


def determine_mean_grade(subjects):
    """Overall grade based on the UNROUNDED average."""
    return assign_grade(calculate_average(subjects))


def highest_subjects(subjects):
    """Names of all subjects tied for the highest marks."""
    if not subjects:
        return []
    top = max(s["marks"] for s in subjects)
    return [s["subject_name"] for s in subjects if s["marks"] == top]


def lowest_subjects(subjects):
    """Names of all subjects tied for the lowest marks."""
    if not subjects:
        return []
    bottom = min(s["marks"] for s in subjects)
    return [s["subject_name"] for s in subjects if s["marks"] == bottom]


def validate_subjects(raw_subjects):
    """Validate a list of (subject_name, raw_marks) pairs.

    Returns a clean list of dicts. Enforces: 1-8 subjects, non-empty
    names, no duplicate names (case-insensitive), marks 0-100.
    """
    if not raw_subjects:
        raise ValidationError("Enter at least one subject before submitting results.")
    if len(raw_subjects) > MAX_SUBJECTS:
        raise ValidationError(f"A student can take a maximum of {MAX_SUBJECTS} subjects.")

    cleaned = []
    seen = set()
    for name, raw_marks in raw_subjects:
        name = (name or "").strip()
        if not name:
            raise ValidationError("Subject names cannot be empty.")
        key = name.lower()
        if key in seen:
            raise ValidationError(f"Duplicate subject name: '{name}'.")
        seen.add(key)
        marks = validate_marks(raw_marks)
        cleaned.append({"subject_name": name, "marks": marks})
    return cleaned


def compute_results(subjects):
    """Build the full results summary for a student's subject list."""
    average = calculate_average(subjects)
    return {
        "subjects": [
            {**s, "grade": assign_grade(s["marks"])} for s in subjects
        ],
        "total": calculate_total(subjects),
        "count": len(subjects),
        "average": average,
        "average_display": f"{average:.2f}",
        "mean_grade": assign_grade(average),
        "highest": highest_subjects(subjects),
        "lowest": lowest_subjects(subjects),
    }