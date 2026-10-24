# Student Records REST API

A Software Quality Engineering project using Python, Flask, SQLite and Postman.
It creates, lists, retrieves, updates and deletes student records. Data is stored
in `instance/students.db` and survives server restarts.

## Start here

Open `START_HERE.html` in a browser for the complete beginner guide in Roman Urdu.
Open `docs/Project_Report_Draft.docx` for the report that you complete with your
own student information, Postman evidence, repository URL and video URL.

## Windows quick start

Open the extracted folder that contains `app.py` in VS Code. Open its terminal.
Use Python 3.11 or newer. The verification environment used Python 3.12.

With uv:

```powershell
uv venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Alternative with a standard Python installation, if uv is unavailable:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000/health. Expected:

```json
{"database":"connected","status":"ok"}
```

Leave the server terminal running. Ctrl+C stops it. Do not delete the database
to restart the app. A new installation starts with an empty student table.

## Endpoints

| Method | Path | Success | Error examples |
|---|---|---|---|
| POST | /api/students | 201, created JSON record | 400 invalid data; 409 duplicate; 415 content type |
| GET | /api/students | 200, JSON array | |
| GET | /api/students/{id} | 200, JSON record | 400 malformed ID; 404 missing record |
| PUT | /api/students/{id} | 200, updated JSON record | 400 validation; 404 missing; 409 duplicate |
| DELETE | /api/students/{id} | 200, message and ID | 400 malformed ID; 404 missing |

Additional diagnostic endpoints: `/` and `/health`. URLs have no trailing slash.
POST and PUT require `Content-Type: application/json` and all four fields:

```json
{
  "name": "Ali Ahmed",
  "rollNo": "K26SW001",
  "department": "Software Engineering",
  "semester": 1
}
```

The server assigns the ID. PUT replaces all four editable fields; it is not a
partial update. Names/departments are trimmed and limited to 100 characters.
Roll numbers are trimmed, uppercased, unique ignoring case, 1-30 characters,
and contain letters, digits or hyphens. Semester is an integer 1-8, not a string
or boolean. Unknown fields are rejected. These are project design decisions,
not additional rules claimed from the teacher's brief. IDs must be positive
SQLite 64-bit integers. Invalid ID format returns 400; a valid but missing ID
returns 404. Payload limit is 16 KiB (413 if exceeded).

## Postman

Import `postman/StudentRecords.postman_collection.json`. The collection's
`baseUrl` is `http://127.0.0.1:5000`. Select no environment to avoid overriding
collection variables. Send TC01 through TC22 in order. TC02 generates a new
fictional roll number and stores `studentId`. Later requests use that ID.
The collection ends by deleting only the record it created; existing records
remain untouched. Re-running TC02 before finishing abandons the earlier test
record, so finish the sequence first.

Open Test Results to review assertions. Error scenarios pass when the expected
error response is received. Save screenshots and fill `docs/Test_Cases.csv`.
Manual request-by-request execution is useful for screenshots and understanding.
The collection can also be run in order with the Postman Collection Runner.

## Verify the actual database

In a second VS Code terminal:

```powershell
.\.venv\Scripts\python.exe show_database.py
```

Run this after TC02, TC11 and TC18. It shows the saved rows without modifying
them. Also check persistence by stopping and restarting the API after TC02
and retrieving the captured ID before continuing TC03.

## Automated regression tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

20 test methods use isolated temporary databases. These tests include database
changes, persistence across app instances, validation boundaries and malformed
inputs. They never modify your `instance/students.db`. They supplement the
required Postman testing; they do not replace your own Postman evidence.

## Files

- `app.py`: routes, validation, database connections and JSON error responses.
- `schema.sql`: non-destructive table initialization and database constraints.
- `requirements.txt`: Flask dependency.
- `show_database.py`: read-only database viewer.
- `tests/test_api.py`: repeatable automated regression tests.
- `postman/`: importable requests and response assertions.
- `docs/`: report draft, test worksheet, viva notes and verification details.
- `evidence/`: put your actual screenshots here.

## Scope and submission

This is a local teaching API with no login or public hosting. Use fictional
student information. The Flask development server is used on localhost.
Complete the report's pending fields and capture your own results. Understand
and adapt the code and follow your institution's assistance/disclosure rules.
Upload source code to your own GitHub repository, make its link accessible to
the instructor, record your demonstration, add both links to the report, and
submit the report to Google Classroom by 11 November 2026.

## Official references

- Flask: https://flask.palletsprojects.com/en/stable/
- SQLite with Flask: https://flask.palletsprojects.com/en/stable/tutorial/database/
- Flask tests: https://flask.palletsprojects.com/en/stable/testing/
- Python sqlite3: https://docs.python.org/3/library/sqlite3.html
- uv environments: https://docs.astral.sh/uv/pip/environments/
- Postman imports: https://learning.postman.com/docs/getting-started/importing-and-exporting/importing-data/
- Postman test scripts: https://learning.postman.com/docs/tests-and-scripts/write-scripts/test-scripts/
