"""Student Records REST API. Run: python app.py. Stop: Ctrl+C."""

import os
import re
import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import BadRequest, HTTPException

ROOT = Path(__file__).resolve().parent
MAX_ID = 9223372036854775807  # SQLite signed 64-bit integer limit.


def create_app(database_path=None):
    """Create the app; tests supply a temporary database instead of real records."""
    app = Flask(__name__)
    app.config['DATABASE'] = str(database_path or ROOT / 'instance' / 'students.db')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)

    def get_db():
        # Each request gets its own connection. It is closed after the request.
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'], timeout=10)
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_error):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().executescript((ROOT / 'schema.sql').read_text(encoding='utf-8'))
        get_db().commit()

    def error(message, status, details=None):
        body = {'error': message}
        if details:
            body['details'] = details
        return jsonify(body), status

    def student_id(raw):
        # Do not pass malformed or overflowing IDs to SQLite.
        if not re.fullmatch(r'[0-9]{1,19}', raw):
            return None
        value = int(raw)
        return value if 1 <= value <= MAX_ID else None

    def find_student(raw):
        value = student_id(raw)
        if value is None:
            return None, error('Student ID must be a positive integer.', 400)
        row = get_db().execute('SELECT * FROM students WHERE id = ?', (value,)).fetchone()
        if row is None:
            return None, error('Student not found.', 404)
        return row, None

    def read_student_data():
        if not request.is_json:
            return None, error('Content-Type must be application/json.', 415)
        try:
            data = request.get_json()
        except BadRequest:
            return None, error('Request body contains invalid JSON.', 400)
        if not isinstance(data, dict):
            return None, error('Request body must be a JSON object.', 400)
        required = {'name', 'rollNo', 'department', 'semester'}
        problems = {}
        for field in sorted(required - data.keys()):
            problems[field] = 'This field is required.'
        extras = sorted(data.keys() - required)
        if extras:
            problems['unknownFields'] = 'Not allowed: ' + ', '.join(extras)
        clean = {}
        for field, limit in [('name', 100), ('rollNo', 30), ('department', 100)]:
            if field not in data:
                continue
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                problems[field] = 'Must be a non-empty string.'
            elif len(value.strip()) > limit:
                problems[field] = f'Must be at most {limit} characters.'
            else:
                clean[field] = value.strip()
        if 'rollNo' in clean:
            clean['rollNo'] = clean['rollNo'].upper()
            if not re.fullmatch(r'[A-Z0-9-]+', clean['rollNo']):
                problems['rollNo'] = 'Use letters, digits or hyphens only.'
        if 'semester' in data:
            # bool is an int subclass in Python, so check the exact type.
            if type(data['semester']) is not int or not 1 <= data['semester'] <= 8:
                problems['semester'] = 'Must be an integer from 1 to 8.'
            else:
                clean['semester'] = data['semester']
        if problems:
            return None, error('Validation failed.', 400, problems)
        return clean, None

    @app.get('/')
    def home():
        return jsonify({'message': 'Student Records API is running.',
                        'students': '/api/students', 'health': '/health'})

    @app.get('/health')
    def health():
        get_db().execute('SELECT 1').fetchone()
        return jsonify({'status': 'ok', 'database': 'connected'})

    @app.get('/api/students')
    def list_students():
        rows = get_db().execute('SELECT * FROM students ORDER BY id').fetchall()
        return jsonify([dict(row) for row in rows]), 200

    @app.get('/api/students/<raw_id>')
    def get_student(raw_id):
        row, failure = find_student(raw_id)
        return failure if failure is not None else (jsonify(dict(row)), 200)

    @app.post('/api/students')
    def create_student():
        data, failure = read_student_data()
        if failure is not None:
            return failure
        db = get_db()
        try:
            with db:
                cursor = db.execute(
                    'INSERT INTO students (name, rollNo, department, semester) VALUES (?, ?, ?, ?)',
                    (data['name'], data['rollNo'], data['department'], data['semester']))
        except sqlite3.IntegrityError:
            return error('A student with this roll number already exists.', 409)
        row = db.execute('SELECT * FROM students WHERE id = ?', (cursor.lastrowid,)).fetchone()
        response = jsonify(dict(row))
        response.status_code = 201
        response.headers['Location'] = f'/api/students/{row["id"]}'
        return response

    @app.put('/api/students/<raw_id>')
    def update_student(raw_id):
        row, failure = find_student(raw_id)
        if failure is not None:
            return failure
        data, failure = read_student_data()
        if failure is not None:
            return failure
        db = get_db()
        try:
            with db:
                db.execute('UPDATE students SET name = ?, rollNo = ?, department = ?, semester = ? WHERE id = ?',
                           (data['name'], data['rollNo'], data['department'], data['semester'], row['id']))
        except sqlite3.IntegrityError:
            return error('A student with this roll number already exists.', 409)
        updated = db.execute('SELECT * FROM students WHERE id = ?', (row['id'],)).fetchone()
        return jsonify(dict(updated)), 200

    @app.delete('/api/students/<raw_id>')
    def delete_student(raw_id):
        row, failure = find_student(raw_id)
        if failure is not None:
            return failure
        with get_db():
            get_db().execute('DELETE FROM students WHERE id = ?', (row['id'],))
        return jsonify({'message': 'Student deleted successfully.', 'id': row['id']}), 200

    @app.errorhandler(HTTPException)
    def handle_http_error(exc):
        # Preserve protocol headers such as Allow while returning JSON errors.
        response = exc.get_response()
        response.data = app.json.dumps({'error': exc.name})
        response.content_type = 'application/json'
        return response

    @app.errorhandler(sqlite3.DatabaseError)
    def handle_database_error(exc):
        app.logger.error('Database operation failed: %s', exc)
        return error('Database operation failed. Check the server terminal.', 500)

    return app


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    create_app().run(host='127.0.0.1', port=port, debug=False)
