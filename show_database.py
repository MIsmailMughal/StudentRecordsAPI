"""Read-only database viewer: run in a SECOND terminal while API is running."""
import json
import sqlite3
from pathlib import Path

path = Path(__file__).resolve().parent / 'instance' / 'students.db'
if not path.exists():
    print('Database is not created yet. Run app.py first.')
else:
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute('SELECT * FROM students ORDER BY id').fetchall()
        print('Database:', path)
        print('Total records:', len(rows))
        print(json.dumps([dict(row) for row in rows], indent=2, ensure_ascii=False))
    finally:
        connection.close()
