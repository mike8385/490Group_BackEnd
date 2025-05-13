import pytest
import json
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with patch('routes.meal_routes.mysql') as mock_mysql:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_mysql.connection = mock_conn
        yield app.test_client(), mock_cursor, mock_conn

def test_get_meal_success(client):
    test_client, mock_cursor, _ = client
    mock_cursor.fetchone.return_value = (1, "Grilled Chicken", "Tasty and lean", 300)

    response = test_client.get('/meal/1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['meal_name'] == "Grilled Chicken"

def test_get_meal_not_found(client):
    test_client, mock_cursor, _ = client
    mock_cursor.fetchone.return_value = None

    response = test_client.get('/meal/999')
    assert response.status_code == 404
    assert b"Meal not found" in response.data

def test_get_all_meals(client):
    test_client, mock_cursor, _ = client
    mock_cursor.fetchall.return_value = [
        (1, "Meal 1", "Desc 1", 300),
        (2, "Meal 2", "Desc 2", 400)
    ]

    response = test_client.get('/meals')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert data[0]['meal_name'] == "Meal 1"

def test_create_meal_plan_success(client):
    test_client, mock_cursor, mock_conn = client
    mock_cursor.fetchone.return_value = (10,)  # user_id

    payload = {
        "meal_plan_name": "Vegan",
        "meal_plan_title": "Plant Based",
        "doctor_id": 1
    }
    response = test_client.post('/create-meal-plan', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 201
    assert b"Meal plan created successfully" in response.data
    assert mock_conn.commit.called

def test_create_meal_plan_user_not_found(client):
    test_client, mock_cursor, _ = client
    mock_cursor.fetchone.return_value = None

    payload = {
        "meal_plan_name": "Vegan",
        "meal_plan_title": "Plant Based",
        "doctor_id": 1
    }
    response = test_client.post('/create-meal-plan', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 400
    assert b"User not found" in response.data

def test_get_meal_plans_by_user_success(client):
    test_client, mock_cursor, _ = client
    mock_cursor.fetchone.return_value = (20,)  # user_id
    mock_cursor.fetchall.return_value = [
        (1, "Keto", "Low carb", "Alice", "Smith")
    ]

    response = test_client.get('/get-meal-plans-by-user?doctor_id=1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]["meal_plan_name"] == "Keto"

def test_assign_meal_to_plan_entry(client):
    test_client, mock_cursor, mock_conn = client

    payload = {
        "meal_plan_id": 1,
        "meal_id": 2,
        "day_of_week": "Monday"
    }
    response = test_client.post('/assign-meal', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 200
    assert b"Meal assigned successfully" in response.data
    assert mock_conn.commit.called

def test_get_meal_plan_entries_by_day_and_time(client):
    test_client, mock_cursor, _ = client
    mock_cursor.fetchall.return_value = [
        (1, "Tofu Stir Fry", "Healthy veggie stir fry", 350, "Tuesday")
    ]
    url = '/meal-plan-entries?meal_plan_id=1'
    response = test_client.get(url)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data[0]["meal_name"] == "Tofu Stir Fry"
    assert data[0]["day_of_week"] == "Tuesday"

def test_get_meal_plans_by_name(client):
    test_client, mock_cursor, _ = client
    mock_cursor.fetchall.return_value = [
        (1, "Keto", "Low carb plan")
    ]
    response = test_client.get('/meal-plans/by-name?meal_plan_name=Keto')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data[0]["meal_plan_name"] == "Keto"

def test_save_a_meal_plan_success(client):
    test_client, mock_cursor, mock_conn = client
    mock_cursor.fetchone.return_value = (33,)  # user_id

    payload = {
        "meal_plan_id": 1,
        "patient_id": 2
    }
    response = test_client.post('/saved-meal-plans', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 200
    assert b"Meal saved successfully" in response.data

def test_get_saved_meal_plan(client):
    test_client, mock_cursor, _ = client

    # Step 1: user exists
    mock_cursor.fetchone.return_value = True

    # Step 2: data rows for meal plan
    mock_cursor.fetchall.return_value = [{
        'meal_plan_id': 1,
        'meal_plan_title': 'Balanced Meals',
        'tag': 'Balanced',
        'made_by': 1,
        'doctor_first': 'Alice',
        'doctor_last': 'Smith',
        'patient_first': None,
        'patient_last': None,
        'meal_id': 1,
        'meal_name': 'Oats',
        'meal_description': 'Healthy oats with banana',
        'meal_calories': 300,
        'day_of_week': 'Monday',
        'meal_time': 'Breakfast'
    }]

    response = test_client.get('/saved-meal-plans/1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "saved_meal_plans" in data
    assert data["saved_meal_plans"][0]["meals"][0]["name"] == "Oats"

