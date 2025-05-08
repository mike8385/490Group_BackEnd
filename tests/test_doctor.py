import pytest
from app import app
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

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