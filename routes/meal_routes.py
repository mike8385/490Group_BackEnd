from flask import Blueprint, request, jsonify
from db import mysql
import bcrypt, base64

meal_bp = Blueprint('meal_bp', __name__)

# get meal
@meal_bp.route('/meal/<int:meal_id>', methods=['GET'])
def get_meal(meal_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT meal_id, meal_name, meal_description, meal_calories FROM MEAL WHERE meal_id = %s", (meal_id,))
    meal = cursor.fetchone()
    cursor.close()
    
    if meal:
        return jsonify({
            'meal_id': meal[0],
            'meal_name': meal[1],
            'meal_description': meal[2],
            'meal_calories': meal[3]
        }), 200
    else:
        return jsonify({'error': 'Meal not found'}), 404

# get all meals
@meal_bp.route('/meals', methods=['GET'])
def get_all_meals():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT meal_id, meal_name, meal_description, meal_calories 
        FROM MEAL
    """)
    meals = cursor.fetchall()
    cursor.close()

    return jsonify([
        {
            'meal_id': meal[0],
            'meal_name': meal[1],
            'meal_description': meal[2],
            'meal_calories': meal[3]
        } for meal in meals
    ]), 200

# creates meal plan
@meal_bp.route('/create-meal-plan', methods=['POST'])
def create_meal_plan():
    data = request.get_json()
    meal_plan_name = data.get('meal_plan_name')
    description = data.get('description')

    cursor = mysql.connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO MEAL_PLAN (meal_plan_name, description) VALUES (%s, %s)",
            (meal_plan_name, description)
        )
        mysql.connection.commit()
        return jsonify({'message': 'Meal plan created successfully'}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()

# prescribes meal to meal plan entry 
@meal_bp.route('/assign-meal', methods=['POST'])
def assign_meal_to_plan_entry():
    data = request.get_json()
    meal_plan_id = data.get('meal_plan_id')
    meal_id = data.get('meal_id')
    day_of_week = data.get('day_of_week')
    meal_time = data.get('meal_time')

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO MEAL_PLAN_ENTRY (meal_plan_id, meal_id, day_of_week, meal_time)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE meal_id = VALUES(meal_id)
        """, (meal_plan_id, meal_id, day_of_week, meal_time))
        mysql.connection.commit()
        return jsonify({'message': 'Meal assigned successfully'}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()

# grabs each meal plan entry based on the time of the day and day of the week
@meal_bp.route('/meal-plan-entries', methods=['GET'])
def get_meal_plan_entries_by_day_and_time():
    meal_plan_id = request.args.get('meal_plan_id')
    day_of_week = request.args.get('day_of_week')
    meal_time = request.args.get('meal_time')

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT mpe.entry_id, m.meal_name, m.meal_description, m.meal_calories
        FROM MEAL_PLAN_ENTRY mpe
        JOIN MEAL m ON mpe.meal_id = m.meal_id
        WHERE mpe.meal_plan_id = %s AND mpe.day_of_week = %s AND mpe.meal_time = %s
    """, (meal_plan_id, day_of_week, meal_time))
    
    entries = cursor.fetchall()
    cursor.close()

    return jsonify([
        {
            'entry_id': entry[0],
            'meal_name': entry[1],
            'meal_description': entry[2],
            'meal_calories': entry[3]
        } for entry in entries
    ]), 200

# get meal plans by prescribed type of meal
@meal_bp.route('/meal-plans/by-name', methods=['GET'])
def get_meal_plans_by_name():
    meal_plan_name = request.args.get('meal_plan_name')

    if not meal_plan_name:
        return jsonify({'error': 'meal_plan_name query parameter is required'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT meal_plan_id, meal_plan_name, description 
        FROM MEAL_PLAN 
        WHERE meal_plan_name = %s
    """, (meal_plan_name,))
    plans = cursor.fetchall()
    cursor.close()

    if not plans:
        return jsonify({'message': 'No meal plans found for that type'}), 404

    return jsonify([
        {
            'meal_plan_id': plan[0],
            'meal_plan_name': plan[1],
            'description': plan[2]
        } for plan in plans
    ]), 200
