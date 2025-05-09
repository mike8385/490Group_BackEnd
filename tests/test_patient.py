import pytest
from unittest.mock import patch, MagicMock
from app import app
import json
import bcrypt
from datetime import datetime

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with patch('routes.patient_routes.mysql') as mock_mysql:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_mysql.connection = mock_conn
        yield app.test_client(), mock_cursor, mock_conn

def test_register_patient_with_survey_success(client):
    test_client, mock_cursor, mock_conn = client

    # Simulate finding pharmacy
    mock_cursor.fetchone.side_effect = [(1,)]  # First fetch is pharmacy

    test_data = {
        "patient_email": "test@example.com",
        "patient_password": "secret123",
        "first_name": "John",
        "last_name": "Doe",
        "pharmacy_name": "HealthRx",
        "pharmacy_address": "123 Main St",
        "pharmacy_zipcode": "12345",
        "insurance_provider": "Aetna",
        "insurance_policy_number": "ABC123",
        "insurance_expiration_date": "2025-12-31",
        "mobile_number": "1234567890",
        "dob": "1990-01-01",
        "gender": "Male",
        "height": 175.5,
        "weight": 70.2,
        "activity": 3.5,
        "health_goals": "Lose weight",
        "dietary_restrictions": "None",
        "blood_type": "O+",
        "patient_address": "456 Elm St",
        "patient_zipcode": "54321",
        "patient_city": "Metropolis",
        "patient_state": "NY",
        "medical_conditions": "None",
        "family_history": "Heart disease",
        "past_procedures": "Appendectomy"
    }

    response = test_client.post(
        '/register-patient-with-survey',
        data=json.dumps(test_data),
        content_type='application/json'
    )

    assert response.status_code == 201
    assert b"Patient registered successfully" in response.data
    assert mock_conn.commit.called

def test_register_patient_with_survey_no_pharmacy(client):
    test_client, mock_cursor, _ = client

    # Simulate missing pharmacy
    mock_cursor.fetchone.return_value = None

    test_data = {
        "patient_email": "fail@example.com",
        "patient_password": "secret123",
        "first_name": "John",
        "last_name": "Doe",
        "pharmacy_name": "Unknown",
        "pharmacy_address": "404 Nowhere",
        "pharmacy_zipcode": "00000",
        "insurance_provider": "None",
        "insurance_policy_number": "N/A",
        "insurance_expiration_date": "2025-12-31",
        "mobile_number": "1234567890",
        "dob": "1990-01-01",
        "gender": "Other",
        "height": 160.0,
        "weight": 60.0,
        "activity": 2.0,
        "health_goals": "Gain muscle",
        "dietary_restrictions": "Gluten-free",
        "blood_type": "A-",
        "patient_address": "789 Hill",
        "patient_zipcode": "99999",
        "patient_city": "Nowhere",
        "patient_state": "NA",
        "medical_conditions": "Asthma",
        "family_history": "None",
        "past_procedures": "None"
    }

    response = test_client.post(
        '/register-patient-with-survey',
        data=json.dumps(test_data),
        content_type='application/json'
    )

    assert response.status_code == 400
    assert b"Pharmacy not found" in response.data

def test_get_patient_success(client):
    test_client, mock_cursor, _ = client
    mock_cursor.fetchone.return_value = (
        1, "test@example.com", "John", "Doe", 2, 1, None, "Aetna", "ABC123", "2025-12-31"
    )

    response = test_client.get('/patient/1')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["patient_email"] == "test@example.com"
    assert data["first_name"] == "John"

def test_get_patient_not_found(client):
    test_client, mock_cursor, _ = client
    mock_cursor.fetchone.return_value = None

    response = test_client.get('/patient/999')

    assert response.status_code == 404
    assert b"Patient not found" in response.data

def test_get_patient_init_survey_success(client):
    test_client, mock_cursor, _ = client

    mock_cursor.fetchone.return_value = (
        1, 1, "1234567890", "1990-01-01", "Male", 175.5, 70.2, "None", "O+",
        "456 Elm St", "54321", "Metropolis", "NY", "None", "Heart disease", "Appendectomy",
        "test@example.com", "John", "Doe", "Salmon", "Lose weight"
    )

    response = test_client.get('/init-patient-survey/1')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["first_name"] == "John"
    assert data["blood_type"] == "O+"

def test_get_patient_init_survey_not_found(client):
    test_client, mock_cursor, _ = client
    mock_cursor.fetchone.return_value = None

    response = test_client.get('/init-patient-survey/999')

    assert response.status_code == 404
    assert b"Patient survey not found" in response.data

def test_select_doctor_success(client):
    test_client, mock_cursor, mock_conn = client

    # Simulate successful update
    response = test_client.post(
        '/select-doctor',
        data=json.dumps({'doctor_id': 1, 'patient_id': 42}),
        content_type='application/json'
    )

    assert response.status_code == 200
    assert b"Doctor assigned successfully" in response.data
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

def test_select_doctor_exception(client):
    test_client, mock_cursor, mock_conn = client

    # Simulate DB exception
    mock_cursor.execute.side_effect = Exception("DB error")

    response = test_client.post(
        '/select-doctor',
        data=json.dumps({'doctor_id': 1, 'patient_id': 42}),
        content_type='application/json'
    )

    assert response.status_code == 400
    assert b"error" in response.data
    mock_conn.rollback.assert_called_once()

def test_remove_doctor_success(client):
    test_client, mock_cursor, mock_conn = client

    # Simulate patient exists and has a doctor assigned
    mock_cursor.fetchone.return_value = (3,)  # doctor_id is 3

    response = test_client.put('/remove_doctor/42')

    assert response.status_code == 200
    assert b"Doctor successfully removed" in response.data
    assert mock_cursor.execute.call_count >= 2  # one SELECT, one UPDATE
    mock_conn.commit.assert_called_once()

def test_remove_doctor_already_none(client):
    test_client, mock_cursor, mock_conn = client

    # Simulate patient exists but doctor_id is NULL
    mock_cursor.fetchone.return_value = (None,)

    response = test_client.put('/remove_doctor/42')

    assert response.status_code == 200
    assert b"already has no assigned doctor" in response.data
    mock_conn.commit.assert_not_called()

def test_remove_doctor_patient_not_found(client):
    test_client, mock_cursor, _ = client

    # Simulate no patient found
    mock_cursor.fetchone.return_value = None

    response = test_client.put('/remove_doctor/999')

    assert response.status_code == 404
    assert b"Patient not found" in response.data

def test_remove_doctor_exception(client):
    test_client, mock_cursor, mock_conn = client

    # Raise exception in SELECT
    mock_cursor.execute.side_effect = Exception("DB failure")

    response = test_client.put('/remove_doctor/1')

    assert response.status_code == 400
    assert b"error" in response.data
    mock_conn.rollback.assert_called_once()

def test_add_daily_survey_success(client):
    test_client, mock_cursor, mock_conn = client

    data = {
        "patient_id": 1,
        "date": "2025-05-01",
        "water_intake": 8,
        "calories_consumed": 2200,
        "heart_rate": 72,
        "exercise": 45,
        "mood": "Happy",
        "follow_plan": 1
    }

    response = test_client.post('/daily-survey', data=json.dumps(data), content_type='application/json')

    assert response.status_code == 201
    assert b"Daily survey submitted successfully" in response.data
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

def test_add_daily_survey_exception(client):
    test_client, mock_cursor, mock_conn = client
    mock_cursor.execute.side_effect = Exception("DB error")

    data = {
        "patient_id": 1,
        "date": "2025-05-01",
        "water_intake": 8,
        "calories_consumed": 2200,
        "heart_rate": 72,
        "exercise": 45
    }

    response = test_client.post('/daily-survey', data=json.dumps(data), content_type='application/json')

    assert response.status_code == 400
    assert b"error" in response.data
    mock_conn.rollback.assert_called_once()

def test_get_daily_surveys_success(client):
    test_client, mock_cursor, _ = client

    mock_cursor.description = [
        ("ds_id",), ("patient_id",), ("date",), ("water_intake",),
        ("calories_consumed",), ("heart_rate",), ("exercise",), ("mood",), ("follow_plan",)
    ]
    mock_cursor.fetchall.return_value = [
        (1, 1, "2025-05-01", 8, 2200, 72, 45, "Happy", 1),
        (2, 1, "2025-05-02", 7, 2100, 70, 30, "Tired", 0)
    ]

    response = test_client.get('/daily-surveys/1')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert data[0]["mood"] == "Happy"

def test_get_daily_surveys_exception(client):
    test_client, mock_cursor, _ = client
    mock_cursor.execute.side_effect = Exception("Query error")

    response = test_client.get('/daily-surveys/1')

    assert response.status_code == 400
    assert b"error" in response.data

def test_add_weekly_survey_success(client):
    test_client, mock_cursor, mock_conn = client

    data = {
        "patient_id": 1,
        "week_start": "2025-04-28",
        "blood_pressure": "120/80",
        "weight_change": -1.2
    }

    response = test_client.post('/weekly-survey', data=json.dumps(data), content_type='application/json')

    assert response.status_code == 201
    assert b"Weekly survey submitted successfully" in response.data
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

def test_add_weekly_survey_exception(client):
    test_client, mock_cursor, mock_conn = client
    mock_cursor.execute.side_effect = Exception("Insert error")

    data = {
        "patient_id": 1,
        "week_start": "2025-04-28",
        "blood_pressure": "110/70",
        "weight_change": 0.0
    }

    response = test_client.post('/weekly-survey', data=json.dumps(data), content_type='application/json')

    assert response.status_code == 400
    assert b"error" in response.data
    mock_conn.rollback.assert_called_once()

def test_get_weekly_surveys_success(client):
    test_client, mock_cursor, _ = client

    mock_cursor.description = [
        ("ws_id",), ("patient_id",), ("week_start",), ("blood_pressure",), ("weight_change",)
    ]
    mock_cursor.fetchall.return_value = [
        (1, 1, "2025-04-28", "120/80", -1.5),
        (2, 1, "2025-05-05", "118/76", -0.8)
    ]

    response = test_client.get('/weekly-surveys/1')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert data[1]["blood_pressure"] == "118/76"

def test_get_weekly_surveys_exception(client):
    test_client, mock_cursor, _ = client
    mock_cursor.execute.side_effect = Exception("DB failure")

    response = test_client.get('/weekly-surveys/1')

    assert response.status_code == 400
    assert b"error" in response.data

@pytest.mark.parametrize("endpoint,data,expected_status,message", [
    (
        "/appointments",
        {
            "patient_id": 1,
            "doctor_id": 2,
            "appointment_datetime": "2025-05-01T10:30:00",
            "reason_for_visit": "Check-up and blood pressure",
            "current_medications": "Lisinopril",
            "exercise_frequency": "3x/week",
            "doctor_appointment_note": "",
            "accepted": 0,
            "meal_prescribed": "Mediterranean"
        },
        201,
        "Appointment created successfully"
    ),
    (
        "/appointment/rate",
        {"appt_id": 10, "rating": 4.5},
        200,
        "Appointment rated successfully"
    )
])

def test_appointment_post_endpoints(client, endpoint, data, expected_status, message):
    test_client, mock_cursor, mock_conn = client

    if endpoint == "/appointment/rate":
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.side_effect = [(2,), (4.5,)]
        response = test_client.patch(endpoint, data=json.dumps(data), content_type='application/json')
    else:
        response = test_client.post(endpoint, data=json.dumps(data), content_type='application/json')

    assert response.status_code == expected_status
    assert message.encode() in response.data
    assert mock_cursor.execute.called
    assert mock_conn.commit.called

def test_get_all_appointments(client):
    test_client, mock_cursor, _ = client
    mock_cursor.description = [("patient_appt_id",), ("patient_id",), ("doctor_id",), ("appointment_datetime",)]
    mock_cursor.fetchall.return_value = [(1, 1, 2, "2025-05-01 10:30:00")]

    response = test_client.get("/appointments/1")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert data[0]["patient_appt_id"] == 1

def test_get_upcoming_and_past_appointments(client):
    test_client, mock_cursor, _ = client
    mock_cursor.description = [("patient_appt_id",), ("appointment_datetime",)]
    mock_cursor.fetchall.return_value = [(1, "2025-06-01 09:00:00")]

    for route in ["appointmentsupcoming", "appointmentspast"]:
        response = test_client.get(f"/{route}/1")
        assert response.status_code == 200
        assert b"appointment_datetime" in response.data

def test_get_single_appointment_by_id_success(client):
    test_client, mock_cursor, _ = client
    mock_cursor.description = [("patient_appt_id",), ("patient_name",), ("doctor_name",)]
    mock_cursor.fetchone.return_value = (10, "John Doe", "Dr. Smith")

    response = test_client.get("/single_appointment/10")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["patient_appt_id"] == 10

def test_cancel_appointment_success(client):
    test_client, mock_cursor, mock_conn = client
    mock_cursor.rowcount = 1

    response = test_client.delete("/cancel-appointment/10")
    assert response.status_code == 200
    assert b"Appointment cancelled successfully" in response.data
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

def test_cancel_appointment_not_found(client):
    test_client, mock_cursor, _ = client
    mock_cursor.rowcount = 0

    response = test_client.delete("/cancel-appointment/999")
    assert response.status_code == 404
    assert b"Appointment not found" in response.data

def test_get_all_bills_for_patient_success(client):
    test_client, mock_cursor, _ = client

    # Mock one charge and one credit record
    mock_cursor.fetchall.return_value = [
    (1, 'charge', 'Appt 1', datetime(2025, 5, 1), 75.0, 45.0, None, 120.0),
    (2, 'credit', 'credit', datetime(2025, 5, 2), None, None, 100.0, 0.0)
    ]

    response = test_client.get('/patient/1/bills')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert data[0]["article"] == "Appt 1"
    assert data[1]["credit"] == 100.0


def test_get_all_bills_for_patient_failure(client):
    test_client, mock_cursor, _ = client
    mock_cursor.execute.side_effect = Exception("SQL error")

    response = test_client.get('/patient/1/bills')
    assert response.status_code == 400
    assert b"error" in response.data


def test_edit_patient_success(client):
    test_client, mock_cursor, mock_conn = client

    payload = {
        "patient_id": 101,
        "email": "john.doe@example.com",
        "password": "newSecurePass123",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "555-1234",
        "dob": "1990-01-01",
        "gender": "Male",
        "height": 180.5,
        "weight": 75.0,
        "blood_type": "O+",
        "dietary_restrictions": "Peanuts",
        "activity": 3.5,
        "health_conditions": "Asthma",
        "family_history": "Diabetes",
        "past_procedures": "Appendectomy",
        "address": "123 Main St",
        "zipcode": "10001",
        "city": "New York",
        "state": "NY"
    }

    response = test_client.put('/edit-patient', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 200
    assert b"updated successfully" in response.data
    assert mock_cursor.execute.call_count == 2
    assert mock_conn.commit.called

def test_edit_patient_failure(client):
    test_client, mock_cursor, mock_conn = client
    mock_cursor.execute.side_effect = Exception("DB error")

    payload = {
        "patient_id": 101,
        "email": "john.doe@example.com",
        "password": "badpass",
        "first_name": "John",
        "last_name": "Doe"
    }

    response = test_client.put('/edit-patient', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 500
    assert b"error" in response.data
    assert mock_conn.rollback.called
