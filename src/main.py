import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.models import db
from src.config import config

def create_app(config_name='default'):
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    jwt = JWTManager(app)
    
    # Import models to register them
    from src.models.user import User
    from src.models.institution import Institution
    from src.models.course import Course
    from src.models.subject import Subject
    from src.models.student import Student
    from src.models.teacher import Teacher
    from src.models.class_group import ClassGroup
    from src.models.enrollment import Enrollment
    from src.models.evaluation_type import EvaluationType
    from src.models.evaluation import Evaluation
    from src.models.grade import Grade
    from src.models.attendance import Attendance
    
    # Import blueprints
    from src.routes.auth import auth_bp
    from src.routes.users import users_bp
    from src.routes.students import students_bp
    from src.routes.teachers import teachers_bp
    from src.routes.courses import courses_bp
    from src.routes.subjects import subjects_bp
    from src.routes.classes import classes_bp
    from src.routes.grades import grades_bp
    from src.routes.reports import reports_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(students_bp, url_prefix='/api/students')
    app.register_blueprint(teachers_bp, url_prefix='/api/teachers')
    app.register_blueprint(courses_bp, url_prefix='/api/courses')
    app.register_blueprint(subjects_bp, url_prefix='/api/subjects')
    app.register_blueprint(classes_bp, url_prefix='/api/classes')
    app.register_blueprint(grades_bp, url_prefix='/api/grades')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default data if needed
        from src.utils.seed_data import create_default_data
        create_default_data()
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "index.html not found", 404

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

