"""Independent repeatable checks; only temporary databases are modified."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app


class StudentAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'test.db'
        self.app = create_app(self.path)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.data = {'name': 'Ali Ahmed', 'rollNo': 'K26SW001',
                     'department': 'Software Engineering', 'semester': 1}

    def tearDown(self):
        self.temp.cleanup()

    def create(self, **changes):
        return self.client.post('/api/students', json=self.data | changes)

    def rows(self):
        db = sqlite3.connect(self.path)
        try:
            return db.execute(
                'SELECT id, name, rollNo, department, semester '
                'FROM students ORDER BY id'
            ).fetchall()
        finally:
            db.close()
    def test_health_and_empty_list(self):
        self.assertEqual(self.client.get('/health').json, {'status': 'ok', 'database': 'connected'})
        response = self.client.get('/api/students')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    def test_create_and_read_with_database_verification(self):
        created = self.create()
        self.assertEqual(created.status_code, 201)
        sid = created.json['id']
        self.assertEqual(created.json, self.data | {'id': sid})
        self.assertEqual(created.headers['Location'], f'/api/students/{sid}')
        self.assertEqual(self.rows()[0][1:], ('Ali Ahmed', 'K26SW001', 'Software Engineering', 1))
        self.assertEqual(self.client.get(f'/api/students/{sid}').json, created.json)
        self.assertEqual(self.client.get('/api/students').json, [created.json])

    def test_update_is_persisted_and_id_is_unchanged(self):
        sid = self.create().json['id']
        updated = self.client.put(f'/api/students/{sid}', json=self.data | {'semester': 2})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json['id'], sid)
        self.assertEqual(updated.json['semester'], 2)
        self.assertEqual(self.rows()[0][-1], 2)
        self.assertEqual(self.client.get(f'/api/students/{sid}').json, updated.json)

    def test_delete_and_get_deleted_record(self):
        sid = self.create().json['id']
        self.assertEqual(self.client.delete(f'/api/students/{sid}').status_code, 200)
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.client.get(f'/api/students/{sid}').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/students/{sid}').status_code, 404)

    def test_missing_fields(self):
        response = self.client.post('/api/students', json={'name': 'Ali'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json['details']), {'rollNo', 'department', 'semester'})
        self.assertEqual(self.rows(), [])

    def test_invalid_semesters(self):
        for value in [0, 9, -1, '1', 1.5, True, None]:
            with self.subTest(value=value):
                self.assertEqual(self.create(semester=value).status_code, 400)
        self.assertEqual(self.rows(), [])

    def test_semester_boundaries(self):
        for value in [1, 8]:
            with self.subTest(value=value):
                self.assertEqual(self.create(semester=value, rollNo=f'BOUNDARY{value}').status_code, 201)

    def test_invalid_text_and_unknown_fields(self):
        for changes in [{'name': '  '}, {'name': 42}, {'name': 'a' * 101},
                        {'department': None}, {'department': 'd' * 101},
                        {'rollNo': 'bad space'}, {'rollNo': 'r' * 31}, {'id': 5}]:
            with self.subTest(changes=changes):
                self.assertEqual(self.create(**changes).status_code, 400)

    def test_duplicate_roll_number_is_case_insensitive(self):
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(self.create(rollNo='k26sw001').status_code, 409)
        self.assertEqual(len(self.rows()), 1)

    def test_conflicting_update_keeps_original_data(self):
        self.create()
        sid = self.create(rollNo='K26SW002').json['id']
        response = self.client.put(f'/api/students/{sid}', json=self.data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get(f'/api/students/{sid}').json['rollNo'], 'K26SW002')

    def test_invalid_update_keeps_original_data(self):
        sid = self.create().json['id']
        response = self.client.put(f'/api/students/{sid}', json=self.data | {'semester': 99})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.rows()[0][-1], 1)

    def test_missing_ids_for_get_put_delete(self):
        for method in ['get', 'put', 'delete']:
            with self.subTest(method=method):
                response = getattr(self.client, method)('/api/students/999999', json=self.data)
                self.assertEqual(response.status_code, 404)

    def test_malformed_ids_for_get_put_delete(self):
        for sid in ['abc', '0', '-1', '1.5', '9223372036854775808', '9' * 100]:
            for method in ['get', 'put', 'delete']:
                with self.subTest(sid=sid, method=method):
                    response = getattr(self.client, method)(f'/api/students/{sid}', json=self.data)
                    self.assertEqual(response.status_code, 400)

    def test_malformed_json(self):
        response = self.client.post('/api/students', data='{"name":', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_json_must_be_object(self):
        for body in ['null', '[]', '"hello"', '5']:
            with self.subTest(body=body):
                response = self.client.post('/api/students', data=body, content_type='application/json')
                self.assertEqual(response.status_code, 400)

    def test_wrong_content_type(self):
        response = self.client.post('/api/students', data='hello', content_type='text/plain')
        self.assertEqual(response.status_code, 415)

    def test_normalization_and_parameterized_sql(self):
        response = self.create(name="  O'Neil  ", rollNo='k26sw001')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['name'], "O'Neil")
        self.assertEqual(response.json['rollNo'], 'K26SW001')
        self.assertEqual(len(self.rows()), 1)

    def test_records_survive_app_restart(self):
        created = self.create().json
        second_app = create_app(self.path)
        self.assertEqual(second_app.test_client().get('/api/students').json, [created])

    def test_unknown_route_and_wrong_method_return_json(self):
        self.assertEqual(self.client.get('/not-a-route').status_code, 404)
        response = self.client.patch('/api/students/1', json=self.data)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(response.is_json)
        self.assertIn('PUT', response.headers['Allow'])

    def test_request_size_limit(self):
        response = self.client.post('/api/students', data='x' * 17000, content_type='application/json')
        self.assertEqual(response.status_code, 413)
        self.assertTrue(response.is_json)


if __name__ == '__main__':
    unittest.main(verbosity=2)
