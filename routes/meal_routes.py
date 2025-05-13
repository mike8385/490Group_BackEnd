from flask import Blueprint, request, jsonify
from db import mysql
from MySQLdb.cursors import DictCursor
from collections import defaultdict
import bcrypt, base64

meal_bp = Blueprint('meal_bp', __name__)

# get meal
@meal_bp.route('/meal/<int:meal_id>', methods=['GET'])
def get_meal(meal_id):
    """
    Retrieve a meal by its ID

    ---
    tags:
      - Meal
    parameters:
      - name: meal_id
        in: path
        type: integer
        required: true
        description: ID of the meal to retrieve
    responses:
      200:
        description: Meal found and returned
        content:
          application/json:
            example:
              meal_id: 5
              meal_name: "Grilled Chicken Salad"
              meal_description: "A light salad with grilled chicken, lettuce, and vinaigrette"
              meal_calories: 350
      404:
        description: Meal not found
        content:
          application/json:
            example:
              error: Meal not found
    """
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
    """
    Get list of all meals

    ---
    tags:
      - Meal
    responses:
      200:
        description: List of meals
        content:
          application/json:
            example:
              - meal_id: 1
                meal_name: "Grilled Chicken"
                meal_description: "High-protein low-fat option"
                meal_calories: 350
    """
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
# [x] needs meal plan title made by field, no description necessary
@meal_bp.route('/create-meal-plan', methods=['POST'])
def create_meal_plan():
    """
    Create a new meal plan

    ---
    tags:
      - Meal Plan
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [meal_plan_name, meal_plan_title]
            properties:
              meal_plan_name:
                type: string
              meal_plan_title:
                type: string
              doctor_id:
                type: integer
              patient_id:
                type: integer
          example:
            meal_plan_name: "Vegan"
            meal_plan_title: "Plant-based high-fiber meals"
            doctor_id: 3
    responses:
      201:
        description: Meal plan created successfully
      400:
        description: Creation failed
    """
    data = request.get_json()
    meal_plan_name = data.get('meal_plan_name')
    meal_plan_title = data.get('meal_plan_title')
    doctor_id = data.get('doctor_id')
    patient_id = data.get('patient_id')

    cursor = mysql.connection.cursor()
    try:
        if doctor_id:
            cursor.execute("SELECT user_id FROM USER WHERE doctor_id = %s", (doctor_id,))
        elif patient_id:
            cursor.execute("SELECT user_id FROM USER WHERE patient_id = %s", (patient_id,))
        else:
            return jsonify({'error': 'Either doctor_id or patient_id is required'}), 400

        result = cursor.fetchone()
        if not result:
            return jsonify({'error': 'User not found'}), 400

        user_id = result[0]

        cursor.execute(
            "INSERT INTO MEAL_PLAN (meal_plan_name, meal_plan_title, made_by) VALUES (%s, %s, %s)",
            (meal_plan_name, meal_plan_title, user_id)
        )
        mysql.connection.commit()
        return jsonify({'message': 'Meal plan created successfully'}), 201

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()

# [x] get method for create-meal plan 
@meal_bp.route('/get-meal-plans-by-user', methods=['GET'])
def get_meal_plans_by_user():
    """
    Get meal plans created by a specific doctor or patient
    """
    doctor_id = request.args.get('doctor_id', type=int)
    patient_id = request.args.get('patient_id', type=int)

    if not doctor_id and not patient_id:
        return jsonify({'error': 'doctor_id or patient_id must be provided'}), 400

    cursor = mysql.connection.cursor()
    try:
        if doctor_id:
            cursor.execute("SELECT user_id FROM USER WHERE doctor_id = %s", (doctor_id,))
        else:
            cursor.execute("SELECT user_id FROM USER WHERE patient_id = %s", (patient_id,))

        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 400

        user_id = user[0]

        query = """
        SELECT
            mp.meal_plan_id,
            mp.meal_plan_name,
            mp.meal_plan_title,
            IF(d.first_name IS NOT NULL, d.first_name, p.first_name) AS first_name,
            IF(d.last_name IS NOT NULL, d.last_name, p.last_name) AS last_name
        FROM MEAL_PLAN mp
        JOIN USER u ON mp.made_by = u.user_id
        LEFT JOIN DOCTOR d ON u.doctor_id = d.doctor_id
        LEFT JOIN PATIENT p ON u.patient_id = p.patient_id
        WHERE mp.made_by = %s
        ORDER BY mp.created_at DESC;
        """
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()

        meal_plans = []
        for row in results:
            meal_plan_id, meal_plan_name, meal_plan_title, first_name, last_name = row
            meal_plans.append({
                'meal_plan_id': meal_plan_id,
                'meal_plan_name': meal_plan_name,
                'meal_plan_title': meal_plan_title,
                'first_name': first_name,
                'last_name': last_name
            })

        return jsonify(meal_plans), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()

# prescribes meal to meal plan entry 
# [x] get rid of meal time column
@meal_bp.route('/assign-meal', methods=['POST'])
def assign_meal_to_plan_entry():
    """
    Assign a meal to a specific day and time in a meal plan

    ---
    tags:
      - Meal Plan
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [meal_plan_id, meal_id, day_of_week, meal_time]
            properties:
              meal_plan_id:
                type: integer
              meal_id:
                type: integer
              day_of_week:
                type: string
                enum: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday]
          example:
            meal_plan_id: 2
            meal_id: 4
            day_of_week: "Tuesday"
    responses:
      200:
        description: Meal assigned successfully
      400:
        description: Assignment failed
    """
    data = request.get_json()
    meal_plan_id = data.get('meal_plan_id')
    meal_id = data.get('meal_id')
    day_of_week = data.get('day_of_week')

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO MEAL_PLAN_ENTRY (meal_plan_id, meal_id, day_of_week)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE meal_id = VALUES(meal_id)
        """, (meal_plan_id, meal_id, day_of_week))
        mysql.connection.commit()
        return jsonify({'message': 'Meal assigned successfully'}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()

# grabs each meal plan entry based on day of the week
# ex: /meal-plan-entries?meal_plan_id=1&day_of_week=Tuesday
@meal_bp.route('/meal-plan-entries', methods=['GET'])
def get_meal_plan_entries():
    """
    Get all meals assigned to a meal plan, grouped by day of the week

    ---
    tags:
      - Meal Plan
    parameters:
      - name: meal_plan_id
        in: query
        type: integer
        required: true
        description: ID of the meal plan to retrieve entries for
    responses:
      200:
        description: Meals retrieved successfully
        content:
          application/json:
            example:
              - entry_id: 1
                meal_name: "Vegan Pancakes"
                meal_description: "Made with almond flour and flaxseed"
                meal_calories: 250
                day_of_week: "Monday"
    """
    meal_plan_id = request.args.get('meal_plan_id')

    if not meal_plan_id:
        return jsonify({"error": "meal_plan_id is required"}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT mpe.entry_id, m.meal_name, m.meal_description, m.meal_calories, mpe.day_of_week, mpe.meal_time
        FROM MEAL_PLAN_ENTRY mpe
        JOIN MEAL m ON mpe.meal_id = m.meal_id
        WHERE mpe.meal_plan_id = %s
        ORDER BY FIELD(mpe.day_of_week, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
    """, (meal_plan_id,))
    
    entries = cursor.fetchall()
    cursor.close()

    return jsonify([
        {
            'entry_id': entry[0],
            'meal_name': entry[1],
            'meal_description': entry[2],
            'meal_calories': entry[3],
            'day_of_week': entry[4]
        } for entry in entries
    ]), 200

# get meal plans by prescribed type of meal - unnecessary
@meal_bp.route('/meal-plans/by-name', methods=['GET'])
def get_meal_plans_by_name():
    """
    Get meal plans by their category name

    ---
    tags:
      - Meal Plan
    parameters:
      - name: meal_plan_name
        in: query
        type: string
        enum: [Low Carb, Keto, Paleo, Mediterranean, Vegan, Vegetarian, Gluten-Free, Dairy-Free]
        required: true
    responses:
      200:
        description: Matching meal plans found
      400:
        description: Missing query parameter
      404:
        description: No matching plans found
    """
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

# [] add a meal to saved meal plans for specific patient/doctor id
@meal_bp.route('/saved-meal-plans', methods=['POST'])
def save_a_meal_plan():
    data = request.get_json()
    meal_plan_id = data.get('meal_plan_id')
    doctor_id = data.get('doctor_id')
    patient_id = data.get('patient_id')

    cursor = mysql.connection.cursor()
    try:
        if doctor_id:
            cursor.execute("SELECT user_id FROM USER WHERE doctor_id = %s", (doctor_id,))
        elif patient_id:
            cursor.execute("SELECT user_id FROM USER WHERE patient_id = %s", (patient_id,))
        else:
            return jsonify({'error': 'Either doctor_id or patient_id is required'}), 400

        result = cursor.fetchone()
        if not result:
            return jsonify({'error': 'User not found'}), 400

        user_id = result[0]

        query = """
        INSERT INTO PATIENT_PLANS (meal_plan_id, user_id) VALUES (%s, %s)
        """
        cursor.execute(query, (meal_plan_id, user_id))
        mysql.connection.commit()
        return jsonify({'message': 'Meal saved successfully'})

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 400
    
    finally:
        cursor.close()

# [x] get saved meal plan for specific patient/doctor id
@meal_bp.route('/saved-meal-plans/<int:user_id>', methods=['GET'])
def get_saved_meal_plan(user_id):
    cursor = mysql.connection.cursor(DictCursor)
    try:
        # Step 1: Confirm user exists
        cursor.execute("SELECT * FROM USER WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'User not found'}), 404

        # Step 2: Query meal plans and creator info
        query = """
            SELECT 
                pp.patient_plan_id,
                mp.meal_plan_id,
                mp.meal_plan_title,
                mp.meal_plan_name AS tag,
                mp.made_by,
                u.doctor_id,
                u.patient_id,
                d.first_name AS doctor_first,
                d.last_name AS doctor_last,
                p.first_name AS patient_first,
                p.last_name AS patient_last,
                m.meal_id,
                m.meal_name,
                m.meal_description,
                m.meal_calories,
                mpe.day_of_week,
                mpe.meal_time
            FROM PATIENT_PLANS pp
            JOIN MEAL_PLAN mp ON pp.meal_plan_id = mp.meal_plan_id
            JOIN USER u ON mp.made_by = u.user_id
            LEFT JOIN DOCTOR d ON u.doctor_id = d.doctor_id
            LEFT JOIN PATIENT p ON u.patient_id = p.patient_id
            JOIN MEAL_PLAN_ENTRY mpe ON mp.meal_plan_id = mpe.meal_plan_id
            JOIN MEAL m ON mpe.meal_id = m.meal_id
            WHERE pp.user_id = %s
            ORDER BY mp.meal_plan_id, mpe.day_of_week, mpe.meal_time
        """
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        cursor.close()

        if not rows:
            return jsonify({'message': 'No saved meal plans found for this user.'}), 200

        # Step 3: Group by meal plan
        meal_plans = defaultdict(lambda: {
            'meal_plan_id': None,
            'title': '',
            'tag': '',
            'made_by': None,
            'creator_name': '',
            'meals': []
        })

        for row in rows:
            pid = row['meal_plan_id']

            # Determine full name
            if row['doctor_first']:
                creator_name = f"Dr. {row['doctor_first']} {row['doctor_last']}"
            else:
                creator_name = f"{row['patient_first']} {row['patient_last']}"

            meal_plans[pid]['meal_plan_id'] = pid
            meal_plans[pid]['title'] = row['meal_plan_title']
            meal_plans[pid]['tag'] = row['tag']
            meal_plans[pid]['made_by'] = row['made_by']
            meal_plans[pid]['creator_name'] = creator_name
            meal_plans[pid]['meals'].append({
                'meal_id': row['meal_id'],
                'name': row['meal_name'],
                'description': row['meal_description'],
                'calories': row['meal_calories'],
                'day': row['day_of_week'],
                'time': row['meal_time']
            })

        return jsonify({'saved_meal_plans': list(meal_plans.values())}), 200

    except Exception as e:
        print("Error retrieving saved meal plans:", str(e))
        return jsonify({'error': 'Internal server error'}), 500
    
# grab all of the meal plans made by the patient + the meal plans assigned to them
@meal_bp.route('/get-saved-meal-plans/<int:patient_id>', methods=['GET'])
def get_patient_meal_plans(patient_id):
    """
    Get all meal plans made by or assigned to a patient.

    ---
    tags:
      - Meal Plan
    parameters:
      - name: patient_id
        in: path
        required: true
        schema:
          type: integer
        description: The patient ID to retrieve meal plans for
    responses:
      200:
        description: List of relevant meal plans
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  meal_plan_id:
                    type: integer
                  title:
                    type: string
                  tag:
                    type: string
                  made_by:
                    type: string
            example:
              - meal_plan_id: 1
                title: "Keto Kickstart"
                tag: "Keto"
                made_by: "Dr. Alex Kim"
              - meal_plan_id: 2
                title: "Plant Power"
                tag: "Vegan"
                made_by: "Jamie Rivera"
      404:
        description: Patient not found
    """
    cursor = mysql.connection.cursor(DictCursor)

    # Step 1: get user_id of the patient
    cursor.execute("SELECT user_id FROM USER WHERE patient_id = %s", (patient_id,))
    result = cursor.fetchone()
    if not result:
        return jsonify({"error": "Patient not found"}), 404

    user_id = result['user_id']

    # Step 2: query meal plans (created or assigned)
    query = """
    SELECT DISTINCT
        mp.meal_plan_id,
        mp.meal_plan_title AS title,
        mp.meal_plan_name AS tag,
        mp.created_at,
        CASE
            WHEN d.first_name IS NOT NULL THEN CONCAT('Dr. ', d.first_name, ' ', d.last_name)
            ELSE CONCAT(p.first_name, ' ', p.last_name)
        END AS made_by
    FROM MEAL_PLAN mp
    JOIN USER u ON mp.made_by = u.user_id
    LEFT JOIN DOCTOR d ON u.doctor_id = d.doctor_id
    LEFT JOIN PATIENT p ON u.patient_id = p.patient_id
    WHERE mp.made_by = %s
       OR mp.meal_plan_id IN (
            SELECT meal_plan_id FROM PATIENT_PLANS WHERE user_id = %s
       )
    ORDER BY mp.created_at DESC;
    """

    cursor.execute(query, (user_id, user_id))
    meal_plans = cursor.fetchall()
    cursor.close()

    return jsonify(meal_plans), 200

# need to test this
# get all meal plans in database
@meal_bp.route('/get-doctor-meal-plans/', methods=['GET'])
def get_doctor_meal_plans():
    """
    Get all meal plans

    ---
    tags:
      - Appointment
    responses:
      200:
        description: List of meal plans created by the doctor
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  meal_plan_id:
                    type: integer
                  title:
                    type: string
                  tag:
                    type: string
                  made_by:
                    type: string
            example:
              - meal_plan_id: 1
                title: "Keto Kickstart"
                tag: "Keto"
                made_by: "Dr. Alex Kim"
              - meal_plan_id: 2
                title: "Plant Power"
                tag: "Vegan"
                made_by: "Jamie Rivera"
      404:
        description: Doctor not found or no meal plans available
    """

    cursor = mysql.connection.cursor(DictCursor)

    cursor.execute("""
        SELECT *
        FROM MEAL_PLAN mp
    """)
    meal_plans = cursor.fetchall()
    cursor.close()

    if not meal_plans:
        return jsonify({'message': 'No meal plans found.'}), 404

    return jsonify(meal_plans), 200