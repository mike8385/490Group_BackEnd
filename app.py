from flask import Flask
from flask_cors import CORS
from db import mysql
import config

# Blueprints
from routes.doctor_routes import doctor_bp
from routes.pharmacy_routes import pharmacy_bp
from routes.patient_routes import patient_bp
from routes.meal_routes import meal_bp
from routes.community_routes import comm_bp
from routes.testing import test_bp

app = Flask(__name__)
CORS(app)

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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
