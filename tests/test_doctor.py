import pytest
from unittest.mock import patch, MagicMock
from app import app
import json
import bcrypt
import base64

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with patch('routes.doctor_routes.mysql') as mock_mysql:
        # Mock cursor and commit
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_mysql.connection = mock_conn
        yield app.test_client()

def test_register_doctor_success(client):
    response = client.post('/register-doctor', json={
        "first_name": "Alice",
        "last_name": "Nguyen",
        "email": "alice.nguyen@example.com",
        "password": "SecurePass123!",
        "description": "Experienced cardiologist.",
        "license_num": "MD1234567",
        "license_exp_date": "2028-12-31",
        "dob": "1980-01-15",
        "med_school": "Harvard Medical School",
        "years_of_practice": 15,
        "specialty": "Cardiology",
        "payment_fee": 150.00,
        "gender": "Female",
        "phone_number": "1234567890",
        "address": "123 Heartbeat Lane",
        "zipcode": "10001",
        "city": "New York",
        "state": "NY",
        "doctor_picture": None
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == "Doctor registered successfully!"

def test_register_doctor_missing_required_field(client):
    # Missing email and password
    response = client.post('/register-doctor', json={
        "first_name": "Alice"
    })

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data

def test_get_doctor_success(client):
    # Patch the fetchone return value just for this test
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor:
        mock_cursor_instance = MagicMock()
        mock_cursor_instance.fetchone.return_value = (
            1, "Alice", "Nguyen", "alice@example.com", "Expert cardiologist.",
            "MD1234567", "2028-12-31", "1980-01-15", "Harvard Medical School",
            "Cardiology", 15, 150.0, "Female", "1234567890", "123 Heartbeat Lane",
            "10001", "New York", "NY", None, True, 4.8
        )
        mock_cursor.return_value = mock_cursor_instance

        response = client.get('/doctor/1')

    assert response.status_code == 200
    data = response.get_json()
    assert data['doctor_id'] == 1
    assert data['first_name'] == 'Alice'
    assert data['doctor_rating'] == 4.8

def test_get_doctor_not_found(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor:
        mock_cursor_instance = MagicMock()
        mock_cursor_instance.fetchone.return_value = None
        mock_cursor.return_value = mock_cursor_instance

        response = client.get('/doctor/999')

    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == "Doctor not found"

def test_login_doctor_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()

        # Prevent the route from treating password as plaintext
        mock_cursor.fetchall.return_value = [("someoneelse@example.com",)]

        # Generate a real, matching hash of "SecurePass123!"
        raw_password = "SecurePass123!"
        hashed_pw = bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt()).decode()

        # Use that exact hash as the one stored in the DB
        mock_cursor.fetchone.return_value = (1, hashed_pw)

        mock_cursor_factory.return_value = mock_cursor

        # Send the matching password
        response = client.post('/login-doctor', json={
            "email": "alice.nguyen@example.com",
            "password": raw_password
        })

    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data['message'].startswith("Login successful")
    assert data['doctor_id'] == 1

def test_login_doctor_invalid_password(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()

        mock_cursor.fetchall.return_value = [("someoneelse@example.com",)]

        # Correct hash, but wrong input password
        valid_hash = "$2b$12$uiZUP4d61OgzBCVQ6GvZ6.4oX5zS53B3/OI25gxqdVddR5SS/OzWy"
        mock_cursor.fetchone.return_value = (1, valid_hash)

        mock_cursor_factory.return_value = mock_cursor

        response = client.post('/login-doctor', json={
            "email": "alice.nguyen@example.com",
            "password": "WrongPassword!"
        })

    assert response.status_code == 401
    data = response.get_json()
    assert data['error'] == "Invalid credentials"

def test_get_all_doctors_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()

        mock_cursor.fetchall.return_value = [
            (
                1, "Alice", "Nguyen", "alice@example.com", "Cardiology specialist", "MD123",
                "2028-12-31", "1980-01-15", "Harvard", "Cardiology", 10, 200.0,
                "Female", "1234567890", "123 Lane", "10001", "New York", "NY",
                b"binarypicdata",          # [18] doctor_picture
                True,                      # [19] accepting_patients
                4.9,                       # [20] doctor_rating
                "2021-01-01",              # [21] created_at
                "2022-01-01"               # [22] updated_at
            )
        ]

        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doctors')
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert data[0]['first_name'] == "Alice"
        assert data[0]['doctor_picture'] == base64.b64encode(b"binarypicdata").decode()
        assert data[0]['accepting_patients'] is True
        assert data[0]['doctor_rating'] == 4.9

def test_get_all_doctors_empty(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doctors')
        assert response.status_code == 200
        assert response.get_json() == []

def test_get_appointments_by_doctor_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()

        # Simulated columns returned by cursor.description
        mock_cursor.description = [
            ("patient_appt_id",), ("patient_id",), ("appointment_datetime",),
            ("reason_for_visit",), ("current_medications",), ("exercise_frequency",),
            ("doctor_appointment_note",), ("accepted",), ("meal_prescribed",),
            ("created_at",), ("updated_at",),
            ("patient_first_name",), ("patient_last_name",)
        ]

        # Simulated row(s) returned by fetchall()
        mock_cursor.fetchall.return_value = [
            (
                101, 201, "2025-06-01 14:00:00", "Checkup", "Aspirin", "Daily",
                "Needs follow-up", True, "Low-carb", "2025-05-01", "2025-05-02",
                "Jane", "Doe"
            )
        ]

        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doc-appointments/1')
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert data[0]['patient_appt_id'] == 101
        assert data[0]['patient_first_name'] == "Jane"
        assert data[0]['doctor_appointment_note'] == "Needs follow-up"

def test_get_appointments_by_doctor_empty(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ("patient_appt_id",), ("patient_id",), ("appointment_datetime",),
            ("reason_for_visit",), ("current_medications",), ("exercise_frequency",),
            ("doctor_appointment_note",), ("accepted",), ("meal_prescribed",),
            ("created_at",), ("updated_at",),
            ("patient_first_name",), ("patient_last_name",)
        ]
        mock_cursor.fetchall.return_value = []

        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doc-appointments/99')  # Assume doctor 99 has no appts
        assert response.status_code == 200
        assert response.get_json() == []

def test_get_appointments_by_doctor_error(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Mock DB failure")

        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doc-appointments/1')
        assert response.status_code == 400
        assert "error" in response.get_json()

def test_update_appointment_status_accept(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor_factory.return_value = mock_cursor

        response = client.patch('/doc-appointments-status/42', json={"accepted": 1})

        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == "Appointment accepted successfully."

def test_update_appointment_status_deny(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor_factory.return_value = mock_cursor

        response = client.patch('/doc-appointments-status/42', json={"accepted": 0})

        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == "Appointment denied (status set to 0.5) successfully."

def test_update_appointment_status_invalid_input(client):
    response = client.patch('/doc-appointments-status/42', json={"accepted": 2})
    assert response.status_code == 400
    assert "Invalid status" in response.get_json()["error"]

def test_update_appointment_status_db_error(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_cursor_factory.return_value = mock_cursor

        response = client.patch('/doc-appointments-status/42', json={"accepted": 1})
        assert response.status_code == 400
        assert "error" in response.get_json()

def test_add_prescription_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor_factory.return_value = mock_cursor

        payload = {
            "patient_id": 1,
            "medicine_id": 101,
            "quantity": 2
        }

        response = client.post('/prescription/add', json=payload)
        assert response.status_code == 201
        assert response.get_json()["message"] == "Prescription added successfully."

def test_add_prescription_missing_fields(client):
    response = client.post('/prescription/add', json={
        "patient_id": 1,  # Missing medicine_id and quantity
    })
    assert response.status_code == 400
    assert "required" in response.get_json()["error"]

def test_add_prescription_invalid_quantity(client):
    response = client.post('/prescription/add', json={
        "patient_id": 1,
        "medicine_id": 101,
        "quantity": 0  # Invalid
    })
    assert response.status_code == 400
    assert "positive integer" in response.get_json()["error"]

def test_add_prescription_db_error(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Insert failed")
        mock_cursor_factory.return_value = mock_cursor

        payload = {
            "patient_id": 1,
            "medicine_id": 101,
            "quantity": 3
        }

        response = client.post('/prescription/add', json=payload)
        assert response.status_code == 400
        assert "Insert failed" in response.get_json()["error"]

def test_update_accepting_status_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1  # simulate row updated
        mock_cursor_factory.return_value = mock_cursor

        response = client.patch('/doctor-accepting-status/5', json={"accepting_patients": 1})
        assert response.status_code == 200
        assert "updated successfully" in response.get_json()["message"]

def test_update_accepting_status_invalid_value(client):
    response = client.patch('/doctor-accepting-status/5', json={"accepting_patients": 2})
    assert response.status_code == 400
    assert "Invalid status" in response.get_json()["error"]

def test_update_accepting_status_not_found(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0  # simulate no rows affected
        mock_cursor_factory.return_value = mock_cursor

        response = client.patch('/doctor-accepting-status/99', json={"accepting_patients": 0})
        assert response.status_code == 404
        assert "not found" in response.get_json()["error"]

def test_update_accepting_status_db_error(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database failure")
        mock_cursor_factory.return_value = mock_cursor

        response = client.patch('/doctor-accepting-status/5', json={"accepting_patients": 1})
        assert response.status_code == 400
        assert "Database failure" in response.get_json()["error"]

def test_add_appointment_note_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1  # simulate successful update
        mock_cursor_factory.return_value = mock_cursor

        response = client.patch('/appointment/42/add_note', json={"doctor_appointment_note": "Follow-up in 2 weeks"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["appt_id"] == 42
        assert data["doctor_appointment_note"] == "Follow-up in 2 weeks"

def test_add_appointment_note_not_found(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0  # simulate no such appointment
        mock_cursor_factory.return_value = mock_cursor

        response = client.patch('/appointment/999/add_note', json={"doctor_appointment_note": "Test note"})
        assert response.status_code == 404
        assert "not found" in response.get_json()["error"]

def test_add_appointment_note_db_error(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Update failed")
        mock_cursor_factory.return_value = mock_cursor

        response = client.patch('/appointment/42/add_note', json={"doctor_appointment_note": "Test error"})
        assert response.status_code == 400
        assert "Update failed" in response.get_json()["error"]

def test_get_doctor_average_rating_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (4.25,)  # average
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doctor/1/rating')
        assert response.status_code == 200
        data = response.get_json()
        assert data['average_rating'] == 4.25

def test_get_doctor_average_rating_none(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (None,)
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doctor/1/rating')
        assert response.status_code == 200
        data = response.get_json()
        assert data['average_rating'] is None
        assert "no ratings" in data['message']

def test_get_doctor_average_rating_db_error(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doctor/1/rating')
        assert response.status_code == 400
        assert "error" in response.get_json()

def test_get_patients_by_doctor_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (
                1, 1, "patient@example.com", "1234567890",
                "John", "Doe", "Asthma", 2, b"picdata",
                "Appendectomy", "A+", "Weight loss", "High",
                "BlueCross", "12345", "2025-12-31",
                200.50, "2024-01-01", "2024-04-01"
            )
        ]
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doc_patients/1')
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)

def test_get_patients_by_doctor_none(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doc_patients/99')
        assert response.status_code == 404

def test_get_past_appointments_by_doctor_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.description = [("patient_appt_id",), ("patient_id",), ("appointment_datetime",), ("reason_for_visit",)]
        mock_cursor.fetchall.return_value = [
            (1, 2, "2024-01-01 09:00", "Checkup")
        ]
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doc-past/1')
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)

def test_get_past_appointments_by_doctor_error(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Query failed")
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doc-past/1')
        assert response.status_code == 400

def test_get_upcoming_appointments_by_doctor_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.description = [("patient_appt_id",), ("patient_id",)]
        mock_cursor.fetchall.return_value = [(1, 2)]
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doc-upcoming/1')
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)

def test_get_upcoming_appointments_by_doctor_error(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB issue")
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/doc-upcoming/1')
        assert response.status_code == 400

def test_get_requested_appointments_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.description = [("patient_appt_id",), ("patient_id",)]
        mock_cursor.fetchall.return_value = [(5, 10)]
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/requested-appointments/1')
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)

def test_get_requested_appointments_error(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB failed")
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/requested-appointments/1')
        assert response.status_code == 400

def test_request_prescription_success(client):
    with patch('routes.doctor_routes.send_medication_request') as mock_send:
        response = client.post('/request-prescription', json={
            "appt_id": 1,
            "medicine_id": 101,
            "quantity": 2
        })
        assert response.status_code == 200
        assert response.get_json()["message"] == "Prescription request sent successfully"
        mock_send.assert_called_once()

def test_request_prescription_missing_fields(client):
    response = client.post('/request-prescription', json={
        "appt_id": 1,
        "medicine_id": 101  # quantity missing
    })
    assert response.status_code == 400
    assert "Missing required fields" in response.get_json()["error"]

def test_request_prescription_error(client):
    with patch('routes.doctor_routes.send_medication_request', side_effect=Exception("Mock failure")):
        response = client.post('/request-prescription', json={
            "appt_id": 1,
            "medicine_id": 101,
            "quantity": 2
        })
        assert response.status_code == 500
        assert "Mock failure" in response.get_json()["error"]

def test_edit_doctor_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor_factory.return_value = mock_cursor

        payload = {
            "doctor_id": 1,
            "first_name": "Alice",
            "last_name": "Nguyen",
            "email": "alice@example.com",
            "description": "Expert",
            "years_of_practice": 10,
            "specialty": "Cardiology",
            "payment_fee": 200,
            "gender": "Female",
            "phone_number": "1234567890",
            "address": "123 St",
            "zipcode": "10001",
            "city": "NY",
            "state": "NY"
        }

        response = client.put('/edit-doctor', json=payload)
        assert response.status_code == 200
        assert "updated successfully" in response.get_json()["message"]

def test_edit_doctor_db_error(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Update failed")
        mock_cursor_factory.return_value = mock_cursor

        payload = {
            "doctor_id": 1,
            "first_name": "Alice",
            "last_name": "Nguyen",
            "email": "alice@example.com",
            "description": "Expert",
            "years_of_practice": 10,
            "specialty": "Cardiology",
            "payment_fee": 200,
            "gender": "Female",
            "phone_number": "1234567890",
            "address": "123 St",
            "zipcode": "10001",
            "city": "NY",
            "state": "NY"
        }

        response = client.put('/edit-doctor', json=payload)
        assert response.status_code == 500
        assert "Update failed" in response.get_json()["error"]

def test_get_top_doctors_success(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Alice", "Nguyen", "Expert in Cardiology", 4.9, None),
            ("Bob", "Smith", "General Practitioner", 4.8, None),
            ("Carol", "Lee", "Pediatrics", 4.7, None)
        ]
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/top-doctors')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3
        assert data[0]["first_name"] == "Alice"

def test_get_top_doctors_not_found(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/top-doctors')
        assert response.status_code == 404
        assert "Ratings not found" in response.get_json()["error"]

def test_get_top_doctors_error(client):
    with patch('routes.doctor_routes.mysql.connection.cursor') as mock_cursor_factory:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB crashed")
        mock_cursor_factory.return_value = mock_cursor

        response = client.get('/top-doctors')
        assert response.status_code == 400
        assert "DB crashed" in response.get_json()["error"]
