from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from src.models.user import User

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def coordinator_or_admin_required(f):
    """Decorator to require coordinator or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.role not in ['admin', 'coordinator']:
            return jsonify({'error': 'Coordinator or admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def teacher_or_above_required(f):
    """Decorator to require teacher, coordinator or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.role not in ['admin', 'coordinator', 'teacher']:
            return jsonify({'error': 'Teacher access or above required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Helper function to get current user"""
    current_user_id = get_jwt_identity()
    return User.query.get(current_user_id) if current_user_id else None

