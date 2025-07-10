import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from src.models.simple_models import db, User, Institution, Course, Student, Teacher, Subject, ClassGroup, create_default_data
from src.config import config

def create_app(config_name='default'):
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    jwt = JWTManager(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        create_default_data()
    
    # Authentication routes
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            access_token = create_access_token(identity=user.id)
            return jsonify({
                'access_token': access_token,
                'user': user.to_dict()
            }), 200
        
        return jsonify({'error': 'Invalid credentials'}), 401
    
    @app.route('/api/auth/me', methods=['GET'])
    @jwt_required()
    def get_current_user():
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
    
    # Dashboard stats
    @app.route('/api/dashboard/stats', methods=['GET'])
    @jwt_required()
    def get_dashboard_stats():
        stats = {
            'total_students': Student.query.filter_by(status='active').count(),
            'total_teachers': Teacher.query.filter_by(status='active').count(),
            'total_courses': Course.query.filter_by(is_active=True).count(),
            'total_subjects': Subject.query.filter_by(is_active=True).count(),
            'active_classes': ClassGroup.query.filter_by(status='active').count()
        }
        return jsonify(stats), 200
    
    # Students routes
    @app.route('/api/students', methods=['GET'])
    @jwt_required()
    def get_students():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        students = Student.query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'students': [student.to_dict() for student in students.items],
            'total': students.total,
            'pages': students.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
    
    @app.route('/api/students', methods=['POST'])
    @jwt_required()
    def create_student():
        data = request.get_json()
        
        # Create user first
        user = User(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role='student',
            phone=data.get('phone')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()
        
        # Create student
        student = Student(
            user_id=user.id,
            student_number=data['student_number'],
            course_id=data['course_id'],
            enrollment_date=data.get('enrollment_date'),
            birth_date=data.get('birth_date'),
            gender=data.get('gender')
        )
        
        db.session.add(student)
        db.session.commit()
        
        return jsonify({
            'message': 'Student created successfully',
            'student': student.to_dict()
        }), 201
    
    # Teachers routes
    @app.route('/api/teachers', methods=['GET'])
    @jwt_required()
    def get_teachers():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        teachers = Teacher.query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'teachers': [teacher.to_dict() for teacher in teachers.items],
            'total': teachers.total,
            'pages': teachers.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
    
    # Courses routes
    @app.route('/api/courses', methods=['GET'])
    @jwt_required()
    def get_courses():
        courses = Course.query.filter_by(is_active=True).all()
        return jsonify({
            'courses': [course.to_dict() for course in courses]
        }), 200
    
    # Subjects routes
    @app.route('/api/subjects', methods=['GET'])
    @jwt_required()
    def get_subjects():
        course_id = request.args.get('course_id', type=int)
        query = Subject.query.filter_by(is_active=True)
        
        if course_id:
            query = query.filter_by(course_id=course_id)
        
        subjects = query.all()
        return jsonify({
            'subjects': [subject.to_dict() for subject in subjects]
        }), 200
    
    # Classes routes
    @app.route('/api/classes', methods=['GET'])
    @jwt_required()
    def get_classes():
        classes = ClassGroup.query.all()
        return jsonify({
            'classes': [class_group.to_dict() for class_group in classes]
        }), 200
    
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
                return jsonify({'message': 'SGA Backend API', 'status': 'running'}), 200

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

