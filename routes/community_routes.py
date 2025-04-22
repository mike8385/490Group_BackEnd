from flask import Blueprint, request, jsonify
from db import mysql
import bcrypt, base64

comm_bp = Blueprint('comm_bp', __name__)