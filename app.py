from flask import Flask
from flask_cors import CORS
from db import mysql
from flasgger import Swagger
from flask_socketio import SocketIO, emit
import config
from datetime import datetime

# Blueprints
from routes.doctor_routes import doctor_bp
from routes.pharmacy_routes import pharmacy_bp
from routes.patient_routes import patient_bp
from routes.meal_routes import meal_bp
from routes.community_routes import comm_bp
from routes.testing import test_bp
from routes.chat import chat_bp

app = Flask(__name__)
CORS(app)

swagger = Swagger(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# MySQL config
app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB
# app.config['MYSQL_PORT'] = 3306

mysql.init_app(app)

# Register routes
app.register_blueprint(doctor_bp)
app.register_blueprint(pharmacy_bp)
app.register_blueprint(patient_bp)
app.register_blueprint(test_bp)
app.register_blueprint(meal_bp)
app.register_blueprint(comm_bp)
app.register_blueprint(chat_bp)

@socketio.on('send_message')
def handle_send_message(data):
    print("Message received:", data)
    if 'timestamp' not in data:
        data['timestamp'] = datetime.utcnow().isoformat()
    emit('receive_message', data, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
