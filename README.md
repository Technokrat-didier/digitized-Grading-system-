# School Grading Management System

A fully functional web application for registering students, entering examination
marks, automatically calculating grades, and printing professional report cards.

Built with **Python 3 + Flask + SQLite** on the backend and plain
**HTML5 / CSS3 / vanilla JavaScript** on the frontend (no frontend frameworks).

## Features

- Register, search, edit and delete students (unique admission numbers).
- Enter up to **8 subjects** per student with marks from **0 to 100**
  (decimal marks such as 72.5 are accepted).
- Automatic grading:

  | Marks | Grade |
  |-------|-------|
  | 80–100 | A |
  | 70–79 | B |
  | 60–69 | C |
  | 50–59 | D |
  | 40–49 | E |
  | 0–39 | F |

- Total marks, average (displayed to 2 decimal places), mean grade
  (computed from the **unrounded** average), and highest/lowest subjects
  including ties.
- Dashboard with school-wide statistics and ranked results list.
- Printable report card — use **Print Results / Save as PDF** and choose
  "Save as PDF" in the browser print dialog.
- Configurable school name (Settings page).
- Validation on both the frontend and the backend.
- Records persist in `school.db` between restarts.

## Project structure

```
school_grading_system/
├── app.py                  # Flask routes
├── database.py             # SQLite schema and queries
├── grading.py              # Validation and grading calculations
├── requirements.txt
├── README.md
├── school.db               # Created automatically on first run
├── templates/              # HTML pages (Jinja2)
└── static/
    ├── css/style.css
    └── js/script.js
```

## Installation

1. **Install Python 3.9 or newer** from <https://www.python.org/downloads/>.
   On Windows, tick "Add Python to PATH" during installation.

2. Open a terminal in the `school_grading_system` folder and install the
   dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

   (Use `python3` instead of `python` on macOS/Linux if needed.)

## Database initialisation

No manual step is required. The SQLite database file `school.db` and all
tables are created automatically the first time the application starts
(see `init_db()` in `database.py`). To start completely fresh, stop the
application and delete `school.db` — it will be recreated on the next run.

## Running the application

```bash
python app.py
```

Then open your browser at:

```
http://127.0.0.1:5000
```

### Typical workflow

1. **Register Student** — enter name, admission number, class and year.
2. You are taken to **Enter Examination Marks** — add subjects (up to 8)
   and marks, then click **Save Results**.
3. The **results report** opens with the full performance summary.
4. Use **Student Records** to search, edit, enter marks or delete students.
5. Use **Results & Reports** for the ranked list, and **Settings** to
   change the school name shown on reports.

### Printing / saving as PDF

Open a student's report and click **Print Results / Save as PDF**. The
browser print dialog opens with navigation and buttons hidden. Choose your
printer, or select **Save as PDF** as the destination.

## Stopping and restarting

- Stop: press `Ctrl + C` in the terminal running the application.
- Restart: run `python app.py` again. All records remain in `school.db`.

## Running the tests

An automated test suite covers registration, validation, grading boundaries,
ties, editing, deletion, search, dashboard statistics and persistence:

```bash
python test_app.py
```

It uses a temporary database, so your real `school.db` is never touched.

## Notes

- Subject marks are stored individually; totals, averages and grades are
  recalculated from them on every request, so results always match the marks.
- Deleting a student automatically deletes their subject records
  (foreign key `ON DELETE CASCADE`).
- The app runs on Flask's built-in server, which is intended for local /
  small-school use. For public deployment, use a production WSGI server
  (e.g. waitress or gunicorn) and change `app.secret_key` in `app.py`.