from flask import Blueprint, request, jsonify
from azure.storage.blob import BlobServiceClient
from db import mysql
import os
import time
from werkzeug.utils import secure_filename

comm_bp = Blueprint('comm_bp', __name__)



AZURE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = 'images'
blob_service_client = None
if AZURE_CONNECTION_STRING:
  blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
  container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
# get a post by post_id
@comm_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_posts(post_id):
    """
    Retrieve community post by ID
    ---
    tags:
      - Community
    parameters:
      - name: post_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Post data returned
      404:
        description: Post not found
    """

    cursor = mysql.connection.cursor()
    query = """
        SELECT CP.post_id, CP.meal_id, CP.user_id, CP.description, CP.picture, CP.created_at,
          M.meal_name, M.meal_calories,
          COALESCE(P.first_name, D.first_name) AS first_name,
          COALESCE(P.last_name, D.last_name) AS last_name,
          CONCAT_WS(', ',
            (
                SELECT GROUP_CONCAT(DISTINCT MP.meal_plan_name SEPARATOR ', ')
                FROM MEAL_PLAN_ENTRY AS MPE
                JOIN MEAL_PLAN AS MP ON MPE.meal_plan_id = MP.meal_plan_id
                WHERE MPE.meal_id = CP.meal_id
            ),
            CP.add_tag
        ) AS tag
        FROM COMMUNITY_POST AS CP
        JOIN MEAL AS M ON CP.meal_id = M.meal_id
        JOIN USER AS U ON CP.user_id = U.user_id
        LEFT JOIN PATIENT AS P ON U.patient_id = P.patient_id
        LEFT JOIN DOCTOR AS D ON U.doctor_id = D.doctor_id
        LEFT JOIN MEAL_PLAN_ENTRY AS MPE ON CP.meal_id = MPE.meal_id
        LEFT JOIN MEAL_PLAN AS MP ON MPE.meal_plan_id = MP.meal_plan_id
        WHERE CP.post_id = %s;
    """
    cursor.execute(query, (post_id,))
    post = cursor.fetchone()

    if not post:
        return jsonify({"error": "Post not found."}), 404
    
    like_query = """
        SELECT COUNT(*)
        FROM LIKED_POSTS AS LP
        WHERE LP.post_id = %s;
    """
    cursor.execute(like_query, (post_id,))
    like_count = cursor.fetchone()[0]

    comment_query = """
        SELECT COUNT(*)
        FROM POST_COMMENTS AS PC
        WHERE PC.post_id = %s;
    """
    cursor.execute(comment_query, (post_id,))
    comment_count = cursor.fetchone()[0]

    mysql.connection.commit()

    # post_picture = post[4]
    # if post_picture:
    #     if isinstance(post_picture, str):
    #         post_picture = post_picture.encode('utf-8')
    #     post_picture = base64.b64encode(post_picture).decode('utf-8')

    result = {
        "post_id": post[0],
        "meal_id": post[1],
        "user_id": post[2],
        "description": post[3],
        "picture": post[4],
        "created_at": post[5],
        "meal_name": post[6],
        "meal_calories": post[7],
        "first_name": post[8],
        "last_name": post[9],
        "tag": post[10], # meal plan name, but we're using this as a tag
        "like_count": like_count,
        "comment_count": comment_count
    }
    return jsonify(result), 200
#convert image
@comm_bp.route('/upload-image', methods=['POST'])
def upload_image():
    """
    Upload image to Azure Blob Storage
    ---
    tags:
      - Upload
    requestBody:
      required: true
      content:
        multipart/form-data:
          schema:
            type: object
            properties:
              image:
                type: string
                format: binary
    responses:
      200:
        description: Image uploaded
      400:
        description: Upload failed
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    try:
        filename = secure_filename(image_file.filename)
        unique_filename = f"{int(time.time())}_{filename}"
        blob_client = container_client.get_blob_client(unique_filename)
        blob_client.upload_blob(image_file, overwrite=True)

        image_url = f"https://{blob_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{unique_filename}"
        return jsonify({'url': image_url}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400
# get post by the creator's id
@comm_bp.route('/posts/user/<int:user_id>', methods=['GET'])
def get_posts_by_user(user_id):
    """
    Retrieve community posts by user ID
    ---
    tags:
      - Community
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: List of posts
      404:
        description: No posts found
    """
    cursor = mysql.connection.cursor()
    query = """
        SELECT CP.post_id, CP.meal_id, CP.user_id, CP.description, CP.picture, CP.created_at,
          M.meal_name, M.meal_calories,
          COALESCE(P.first_name, D.first_name) AS first_name,
          COALESCE(P.last_name, D.last_name) AS last_name,
          CONCAT_WS(', ',
            (
                SELECT GROUP_CONCAT(DISTINCT MP.meal_plan_name SEPARATOR ', ')
                FROM MEAL_PLAN_ENTRY AS MPE
                JOIN MEAL_PLAN AS MP ON MPE.meal_plan_id = MP.meal_plan_id
                WHERE MPE.meal_id = CP.meal_id
            ),
            CP.add_tag
        ) AS tag,
        COALESCE(likes.like_count, 0) AS like_count,
        COALESCE(comments.comment_count, 0) AS comment_count
        FROM COMMUNITY_POST AS CP
        JOIN MEAL AS M ON CP.meal_id = M.meal_id
        JOIN USER AS U ON CP.user_id = U.user_id
        LEFT JOIN PATIENT AS P ON U.patient_id = P.patient_id
        LEFT JOIN DOCTOR AS D ON U.doctor_id = D.doctor_id
        LEFT JOIN (
            SELECT post_id, COUNT(*) AS like_count
            FROM LIKED_POSTS
            GROUP BY post_id
        ) AS likes ON CP.post_id = likes.post_id
        LEFT JOIN (
            SELECT post_id, COUNT(*) AS comment_count
            FROM POST_COMMENTS
            GROUP BY post_id
        ) AS comments ON CP.post_id = comments.post_id
        WHERE CP.user_id = %s;
    """
    cursor.execute(query, (user_id,))
    posts = cursor.fetchall()

    if not posts:
        return jsonify({"error": "No posts found for this user."}), 404

    result = []
    for post in posts:
        # post_picture = post[4]
        # if post_picture:
        #     if isinstance(post_picture, str):
        #         post_picture = post_picture.encode('utf-8')
        #     post_picture = base64.b64encode(post_picture).decode('utf-8')

        result.append({
            "post_id": post[0],
            "meal_id": post[1],
            "user_id": post[2],
            "description": post[3],
            "picture": post[4],
            "created_at": post[5],
            "meal_name": post[6],
            "meal_calories": post[7],
            "first_name": post[8],
            "last_name": post[9],
            "tag": post[10], # meal plan name, but we're using this as a tag
            "like_count": post[11] if post[11] is not None else 0,
            "comment_count": post[12] if post[12] is not None else 0
        })
    return jsonify(result), 200

# get all community posts
@comm_bp.route('/posts', methods=['GET'])
def get_all_posts():
    """
    Retrieve all community posts
    ---
    tags:
      - Community
    responses:
      200:
        description: List of all community posts
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
                properties:
                  post_id:
                    type: integer
                  meal_id:
                    type: integer
                  user_id:
                    type: integer
                  description:
                    type: string
                  picture:
                    type: string
                    nullable: true
                    description: URL or encoded string of the image
                  created_at:
                    type: string
                    format: date-time
                  meal_name:
                    type: string
                  meal_calories:
                    type: integer
                  first_name:
                    type: string
                  last_name:
                    type: string
                  tag:
                    type: string
                    description: Comma-separated tags from meal plans or custom tags
                  like_count:
                    type: integer
                    description: Number of likes on the post
                  comment_count:
                    type: integer
                    description: Number of comments on the post
            example:
              - post_id: 101
                meal_id: 12
                user_id: 5
                description: "Great low-carb recipe!"
                picture: "https://storage.googleapis.com/mybucket/post101.jpg"
                created_at: "2025-05-12T14:00:00"
                meal_name: "Grilled Chicken Salad"
                meal_calories: 320
                first_name: "Alex"
                last_name: "Kim"
                tag: "Keto, Protein Rich"
                like_count: 14
                comment_count: 3
    """
    cursor = mysql.connection.cursor()
    query = """
        SELECT 
          CP.post_id, CP.meal_id, CP.user_id, CP.description, CP.picture, CP.created_at,
          M.meal_name, M.meal_calories,
          COALESCE(P.first_name, D.first_name) AS first_name,
          COALESCE(P.last_name, D.last_name) AS last_name,
          CONCAT_WS(', ',
              (
                  SELECT GROUP_CONCAT(DISTINCT MP.meal_plan_name SEPARATOR ', ')
                  FROM MEAL_PLAN_ENTRY AS MPE
                  JOIN MEAL_PLAN AS MP ON MPE.meal_plan_id = MP.meal_plan_id
                  WHERE MPE.meal_id = CP.meal_id
              ),
              CP.add_tag
          ) AS tag,
          COALESCE(likes.like_count, 0) AS like_count,
          COALESCE(comments.comment_count, 0) AS comment_count
        FROM COMMUNITY_POST AS CP
        JOIN MEAL AS M ON CP.meal_id = M.meal_id
        JOIN USER AS U ON CP.user_id = U.user_id
        LEFT JOIN PATIENT AS P ON U.patient_id = P.patient_id
        LEFT JOIN DOCTOR AS D ON U.doctor_id = D.doctor_id
        LEFT JOIN (
            SELECT post_id, COUNT(*) AS like_count
            FROM LIKED_POSTS
            GROUP BY post_id
        ) AS likes ON CP.post_id = likes.post_id
        LEFT JOIN (
            SELECT post_id, COUNT(*) AS comment_count
            FROM POST_COMMENTS
            GROUP BY post_id
        ) AS comments ON CP.post_id = comments.post_id
        ORDER BY CP.post_id DESC;
    """
    cursor.execute(query)
    posts = cursor.fetchall()

    result = []
    for post in posts:
        # post_picture = post[4]
        # if post_picture:
        #     if isinstance(post_picture, str):
        #         post_picture = post_picture.encode('utf-8')
        #     post_picture = base64.b64encode(post_picture).decode('utf-8')

        result.append({
            "post_id": post[0],
            "meal_id": post[1],
            "user_id": post[2],
            "description": post[3],
            "picture": post[4],
            "created_at": post[5],
            "meal_name": post[6],
            "meal_calories": post[7],
            "first_name": post[8],
            "last_name": post[9],
            "tag": post[10], # meal plan name, but we're using this as a tag
            "like_count": post[11] if post[11] is not None else 0,
            "comment_count": post[12] if post[12] is not None else 0
        })
    return jsonify(result), 200

# add community post
@comm_bp.route('/add-post', methods=['POST'])
def add_post():
    """
    Add a community post

    ---
    tags:
      - Community
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - user_id
              - description
              - picture
              - meal_name
              - meal_calories
              - add_tag
            properties:
              user_id:
                type: integer
              meal_name:
                type: string
              meal_calories:
                type: integer
              description:
                type: string
              picture:
                type: string
              add_tag:
                type: string
            example:
              user_id: 1
              meal_name: "Protein Salad"
              meal_calories: 400
              description: "Tasty and healthy!"
              picture: "https://<your-azure-url>.blob.core.windows.net/images/protein_salad_1_123456.png"
              add_tag: "Vegan"
    responses:
      201:
        description: Post added successfully
      400:
        description: Input error or database failure
    """
    data = request.get_json()

    user_id = data.get('user_id')
    meal_name = data.get('meal_name')
    meal_calories = data.get('meal_calories')
    description = data.get('description')
    meal_picture_url = data.get('picture')  # <-- Now it's already a URL
    add_tag = data.get('add_tag')

    if not all([user_id, meal_name, meal_calories, description, meal_picture_url, add_tag]):
        return jsonify({"error": "Missing required fields"}), 400

    cursor = mysql.connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO MEAL (meal_name, meal_description, meal_calories)
            VALUES (%s, %s, %s)
        """, (meal_name, description, meal_calories))

        meal_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO COMMUNITY_POST (meal_id, user_id, description, picture, add_tag)
            VALUES (%s, %s, %s, %s, %s)
        """, (meal_id, user_id, description, meal_picture_url, add_tag))

        mysql.connection.commit()

        return jsonify({
            "message": "Post added successfully.",
            "meal_id": meal_id,
            "user_id": user_id,
            "meal_name": meal_name,
            "meal_calories": meal_calories,
            "description": description,
            "picture": meal_picture_url,
            "add_tag": add_tag
        }), 201

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()


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
        schema:
          type: integer
        required: false
      - name: doctor_id
        in: query
        schema:
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

        post_ids = tuple(post[1] for post in liked_posts)

        # Like counts
        cursor.execute("""
            SELECT post_id, COUNT(*) AS like_count
            FROM LIKED_POSTS
            WHERE post_id IN %s
            GROUP BY post_id
        """, (post_ids,))

        like_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Comment counts
        cursor.execute("""
            SELECT post_id, COUNT(*) AS comment_count
            FROM POST_COMMENTS
            WHERE post_id IN %s
            GROUP BY post_id
        """, (post_ids,))

        comment_counts = {row[0]: row[1] for row in cursor.fetchall()}

        results = []
        for post in liked_posts:
          post_id = post[1]
          results.append({
              "liked_id": post[0],
              "post_id": post_id,
              "user_id": post[2],
              "liked_at": post[3],
              "liked_count": like_counts.get(post_id, 0),
              "comment_count": comment_counts.get(post_id, 0)
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
        return jsonify({"error": error_message}), 400
    finally:
        cursor.close()

  
# unlike a post, remove it from liked post table
@comm_bp.route('/posts/unlike', methods=['DELETE'])
def unlike_post():
    """
    Unlike a community post

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
      200:
        description: Post unliked successfully
      400:
        description: Input error or database failure
      404:
        description: User not found or post not liked
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

        # Remove like from LIKED_POSTS table
        cursor.execute("""
            DELETE FROM LIKED_POSTS 
            WHERE post_id = %s AND user_id = %s;
        """, (post_id, user_id))

        mysql.connection.commit()

        return jsonify({
            "message": "Post unliked successfully.",
            "post_id": post_id,
            "user_id": user_id,
        }), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        cursor.close()
        
# add a comment
@comm_bp.route('/posts/comment', methods=['POST'])
def add_comment():
    """
    Add a comment to a community post
    ---
    tags:
      - Community
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - post_id
              - user_id
              - comment_text
            properties:
              post_id:
                type: integer
              user_id:
                type: integer
              comment_text:
                type: string
            example:
              post_id: 5
              user_id: 1
              comment_text: "This is a great meal!"
    responses:
      201:
        description: Comment added successfully
      400:
        description: Input error or database failure
    """
    data = request.get_json()
    post_id = data.get('post_id')
    user_id = data.get('user_id')
    comment_text = data.get('comment_text')

    cursor = mysql.connection.cursor()

    try:
        # Insert comment into the database
        cursor.execute("""
            INSERT INTO POST_COMMENTS (post_id, user_id, comment_text)
            VALUES (%s, %s, %s)
        """, (post_id, user_id, comment_text))

        mysql.connection.commit()

        return jsonify({
            "message": "Comment added successfully.",
            "post_id": post_id,
            "user_id": user_id,
            "comment": comment_text
        }), 201

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

# get all comments for a post
@comm_bp.route('/posts/comment/<int:post_id>', methods=['GET'])
def get_comments(post_id):
    """
    Get all comments for a post
    ---
    tags:
      - Community
    parameters:
      - name: post_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: List of comments
      400:
        description: Failed to fetch comments
    """
    cursor = mysql.connection.cursor()
    try:
      query = """
          SELECT PC.comment_id, PC.post_id, PC.user_id, PC.comment_text, PC.created_at,
            COALESCE(P.first_name, D.first_name) AS first_name,
            COALESCE(P.last_name, D.last_name) AS last_name,
            U.doctor_id, U.patient_id
          FROM POST_COMMENTS AS PC
          JOIN USER AS U ON PC.user_id = U.user_id
          LEFT JOIN PATIENT AS P ON U.patient_id = P.patient_id
          LEFT JOIN DOCTOR AS D ON U.doctor_id = D.doctor_id
          WHERE PC.post_id = %s
          ORDER BY PC.created_at DESC;
      """
      cursor.execute(query, (post_id,))
      comments = cursor.fetchall()

      result = []
      for comment in comments:
          result.append({
              "comment_id": comment[0],
              "post_id": comment[1],
              "user_id": comment[2],
              "comment_text": comment[3],
              "created_at": comment[4],
              "first_name": comment[5],
              "last_name": comment[6],
              "doctor_id": comment[7],
              "patient_id": comment[8]
          })
      return jsonify(result), 200
    except Exception as e:
      return jsonify({"Failed to fetch comments. Error": str(e)}), 400

# Save a post/meal
@comm_bp.route('/posts/save', methods=['POST'])
def save_post():
    """
    Save a post/meal
    ---
    tags:
      - Community
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - post_id
              - user_id
            properties:
              post_id:
                type: integer
              user_id:
                type: integer
            example:
              post_id: 5
              user_id: 1
    responses:
      201:
        description: Post saved successfully
      400:
        description: Input error or database failure
    """
    data = request.get_json()
    user_id = data.get('user_id')
    post_id = data.get('post_id')
    meal_id = post_id

    cursor = mysql.connection.cursor()

    try:
      # Insert into saved posts table
      cursor.execute("""
          INSERT INTO SAVED_MEAL (user_id, meal_id, post_id)
          VALUES (%s, %s, %s)
      """, (user_id, post_id, meal_id))

      mysql.connection.commit()

      return jsonify({
          "message": "Post saved successfully.",
          "post_id": post_id,
          "user_id": user_id
      }), 201

    except Exception as e:
      mysql.connection.rollback()
      return jsonify({"Failed to save post. Error": str(e)}), 400
    finally:
      cursor.close()

# get saved posts/meals by id
@comm_bp.route('/posts/save/<int:user_id>', methods=['GET'])
def get_saved(user_id):
    """
    Get saved posts/meals by user_id
    ---
    tags:
      - Community
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: integer
    responses:
      200:
        description: List of saved posts
      400:
        description: Failed to fetch saved posts
    """
    cursor = mysql.connection.cursor()
    try:
      query = """
          SELECT SM.saved_meal_id, SM.user_id, SM.meal_id, SM.post_id,
                M.meal_name, M.meal_calories,
                COALESCE(P.first_name, D.first_name) AS first_name,
                COALESCE(P.last_name, D.last_name) AS last_name,
                CONCAT_WS(', ',
                    (
                        SELECT GROUP_CONCAT(DISTINCT MP.meal_plan_name SEPARATOR ', ')
                        FROM MEAL_PLAN_ENTRY AS MPE
                        JOIN MEAL_PLAN AS MP ON MPE.meal_plan_id = MP.meal_plan_id
                        WHERE MPE.meal_id = CP.meal_id
                    ),
                    CP.add_tag
                ) AS tag
          FROM SAVED_MEAL AS SM
          JOIN MEAL AS M ON SM.meal_id = M.meal_id
          JOIN USER AS U ON SM.user_id = U.user_id
          JOIN COMMUNITY_POST AS CP ON SM.post_id = CP.post_id
          LEFT JOIN PATIENT AS P ON U.patient_id = P.patient_id
          LEFT JOIN DOCTOR AS D ON U.doctor_id = D.doctor_id
          WHERE SM.user_id = %s
          ORDER BY SM.saved_meal_id DESC;
      """
      cursor.execute(query, (user_id,))
      saved_posts = cursor.fetchall()

      result = []
      for post in saved_posts:
          result.append({
              "saved_meal_id": post[0],
              "user_id": post[1],
              "meal_id": post[2],
              "post_id": post[3],
              "meal_name": post[4],
              "meal_calories": post[5],
              "first_name": post[6],
              "last_name": post[7],
              "tag": post[8]
          })
      return jsonify(result), 200
    except Exception as e:
        return jsonify({"Failed to fetch posts due to this error": str(e)}), 400
    finally:
        cursor.close()

# if post is saved
@comm_bp.route('/posts/is-saved', methods=['POST'])
def is_saved():
    """
    Check if a post is saved by a user
    ---
    tags:
      - Community
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - user_id
              - post_id
            properties:
              user_id:
                type: integer
              post_id:
                type: integer
    responses:
      200:
        description: Result indicating if post is saved
      400:
        description: Input error
    """
    data = request.get_json()
    user_id = data.get('user_id')
    post_id = data.get('post_id')

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            SELECT 1 FROM SAVED_MEAL WHERE user_id = %s AND post_id = %s
        """, (user_id, post_id))
        result = cursor.fetchone()
        return jsonify({"is_saved": result is not None}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

@comm_bp.route('/posts/is-liked', methods=['POST'])
def is_liked():
    """
    Check if a post is liked by a user
    ---
    tags:
      - Community
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - user_id
              - post_id
            properties:
              user_id:
                type: integer
              post_id:
                type: integer
    responses:
      200:
        description: Result indicating if post is liked
      400:
        description: Input error
    """
    data = request.get_json()
    user_id = data.get('user_id')
    post_id = data.get('post_id')

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            SELECT 1 FROM LIKED_POSTS WHERE user_id = %s AND post_id = %s
        """, (user_id, post_id))
        result = cursor.fetchone()
        return jsonify({"is_liked": result is not None}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()

@comm_bp.route('/posts/unsave', methods=['DELETE'])
def unsave_post():
    """
    Unsave a post
    ---
    tags:
      - Community
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - user_id
              - post_id
            properties:
              user_id:
                type: integer
              post_id:
                type: integer
    responses:
      200:
        description: Post unsaved successfully
      400:
        description: Input error
    """

    data = request.get_json()
    user_id = data.get('user_id')
    post_id = data.get('post_id')

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            DELETE FROM SAVED_MEAL WHERE user_id = %s AND post_id = %s
        """, (user_id, post_id))
        mysql.connection.commit()
        return jsonify({"message": "Post unsaved successfully."}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()