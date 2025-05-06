from flask import Blueprint, request, jsonify
from db import mysql
import bcrypt, base64

comm_bp = Blueprint('comm_bp', __name__)

# get community post
@comm_bp.route('/posts', methods=['GET'])
def get_all_posts():
    """
    Retrieve all community posts

    """
    cursor = mysql.connection.cursor()
    query = """
        SELECT CP.post_id, CP.meal_id, CP.user_id, CP.description, CP.picture, CP.created_at,
          M.meal_name, M.meal_calories,
          COALESCE(P.first_name, D.first_name) AS first_name,
          COALESCE(P.last_name, D.last_name) AS last_name,
          MP.meal_plan_name
        FROM COMMUNITY_POST AS CP
        JOIN MEAL AS M ON CP.meal_id = M.meal_id
        JOIN USER AS U ON CP.user_id = U.user_id
        LEFT JOIN PATIENT AS P ON U.patient_id = P.patient_id
        LEFT JOIN DOCTOR AS D ON U.doctor_id = D.doctor_id
        LEFT JOIN MEAL_PLAN_ENTRY AS MPE ON CP.meal_id = MPE.meal_id
        LEFT JOIN MEAL_PLAN AS MP ON MPE.meal_plan_id = MP.meal_plan_id
        ORDER BY CP.post_id DESC;
    """
    cursor.execute(query)
    posts = cursor.fetchall()

    result = []
    for post in posts:
        post_picture = post[4]
        if post_picture:
            if isinstance(post_picture, str):
                post_picture = post_picture.encode('utf-8')
            post_picture = base64.b64encode(post_picture).decode('utf-8')

        result.append({
            "post_id": post[0],
            "meal_id": post[1],
            "user_id": post[2],
            "description": post[3],
            "picture": post_picture,
            "created_at": post[5],
            "meal_name": post[6],
            "meal_calories": post[7],
            "first_name": post[8],
            "last_name": post[9],
            "tag": post[10], # meal plan name, but we're using this as a tag
        })
    return jsonify(result), 200

# add community post

# get liked posts /posts/liked?patient_id=5
@comm_bp.route('/posts/liked', methods=['GET'])
def get_liked_posts():
    """
    Retrieve liked posts for a patient or doctor

    ---
    tags:
      - Community
    parameters:
      - name: patient_id
        in: query
        type: integer
        required: false
      - name: doctor_id
        in: query
        type: integer
        required: false
    responses:
      200:
        description: List of liked posts
      400:
        description: Missing user identifier
      404:
        description: User not found
    """
    patient_id = request.args.get('patient_id', type=int)
    doctor_id = request.args.get('doctor_id', type=int)

    if not patient_id and not doctor_id:
        return jsonify({"error": "Must provide either patient_id or doctor_id."}), 400

    cursor = mysql.connection.cursor()

    try:
        # Get user_id from USER table
        if patient_id:
            cursor.execute("""
                SELECT user_id
                FROM USER
                WHERE patient_id = %s
            """, (patient_id,))
        else:
            cursor.execute("""
                SELECT user_id
                FROM USER
                WHERE doctor_id = %s
            """, (doctor_id,))

        user_result = cursor.fetchone()

        if not user_result:
            return jsonify({"error": "User not found."}), 404

        user_id = user_result[0]

        # Get liked posts for this user
        cursor.execute("""
            SELECT lp.liked_id, lp.post_id, lp.user_id, lp.liked_at
            FROM LIKED_POSTS lp
            WHERE lp.user_id = %s
            ORDER BY lp.liked_at DESC
        """, (user_id,))
        liked_posts = cursor.fetchall()

        if not liked_posts:
            return jsonify({"message": "No liked posts found for this user."}), 200

        results = []
        for post in liked_posts:
            results.append({
                "liked_id": post[0],
                "post_id": post[1],
                "user_id": post[2],
                "liked_at": post[3]
            })

        return jsonify({
            "user_id": user_id,
            "liked_posts": results
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

# like a post, add it to liked post table
@comm_bp.route('/posts/like', methods=['POST'])
def like_post():
    """
    Like a community post

    ---
    tags:
      - Community
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [post_id]
            properties:
              post_id:
                type: integer
              patient_id:
                type: integer
              doctor_id:
                type: integer
          example:
            post_id: 5
            patient_id: 1
    responses:
      201:
        description: Post liked successfully
      400:
        description: Input error or database failure
      404:
        description: User not found
      409:
        description: Post already liked
    """
    data = request.get_json()
    post_id = data.get('post_id')
    patient_id = data.get('patient_id')
    doctor_id = data.get('doctor_id')

    cursor = mysql.connection.cursor()

    try:
        # Get user_id
        if patient_id:
            cursor.execute("""
                SELECT user_id
                FROM USER
                WHERE patient_id = %s
            """, (patient_id,))
        else:
            cursor.execute("""
                SELECT user_id
                FROM USER
                WHERE doctor_id = %s
            """, (doctor_id,))
        
        user_result = cursor.fetchone()

        if not user_result:
            return jsonify({"error": "User not found."}), 404

        user_id = user_result[0]

        # Insert like
        cursor.execute("""
            INSERT INTO LIKED_POSTS (post_id, user_id)
            VALUES (%s, %s)
        """, (post_id, user_id))

        mysql.connection.commit()

        return jsonify({
            "message": "Post liked successfully.",
            "post_id": post_id,
            "user_id": user_id
        }), 201

    except Exception as e:
        mysql.connection.rollback()
        error_message = str(e)
        
        if "Duplicate entry" in error_message:
            return jsonify({"error": "You have already liked this post."}), 409
        
        return jsonify({"error": error_message}), 400
    finally:
        cursor.close()

# add a comment

# get all comments for a post

# add post to meal plan
