from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models import db
from src.models.user import User
from src.models.student import Student
from src.models.course import Course
from src.utils.decorators import coordinator_or_admin_required, get_current_user

students_bp = Blueprint('students', __name__)

@students_bp.route('', methods=['GET'])
@jwt_required()
def get_students():
    """Get all students with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        course_id = request.args.get('course_id', type=int)
        status = request.args.get('status')
        search = request.args.get('search')
        
        query = Student.query.join(User)
        
        # Apply filters
        if course_id:
            query = query.filter(Student.course_id == course_id)
        
        if status:
            query = query.filter(Student.status == status)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (User.first_name.ilike(search_filter)) |
                (User.last_name.ilike(search_filter)) |
                (User.email.ilike(search_filter)) |
                (Student.student_number.ilike(search_filter))
            )
        
        # Paginate results
        students = query.paginate(
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
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@students_bp.route('/<int:student_id>', methods=['GET'])
@jwt_required()
def get_student(student_id):
    """Get specific student by ID"""
    try:
        student = Student.query.get(student_id)
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        return jsonify({'student': student.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@students_bp.route('', methods=['POST'])
@jwt_required()
@coordinator_or_admin_required
def create_student():
    """Create new student"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 
                          'student_number', 'course_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if username, email or student_number already exists
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        
        if existing_user:
            return jsonify({'error': 'Username or email already exists'}), 400
        
        existing_student = Student.query.filter_by(student_number=data['student_number']).first()
        if existing_student:
            return jsonify({'error': 'Student number already exists'}), 400
        
        # Check if course exists
        course = Course.query.get(data['course_id'])
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Create user first
        user = User(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role='student',
            phone=data.get('phone')
        )
        
        db.session.add(user)
        db.session.flush()  # To get user ID
        
        # Create student
        student = Student(
            user_id=user.id,
            student_number=data['student_number'],
            course_id=data['course_id'],
            enrollment_date=data.get('enrollment_date'),
            birth_date=data.get('birth_date'),
            gender=data.get('gender'),
            document_type=data.get('document_type'),
            document_number=data.get('document_number'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code'),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_phone=data.get('emergency_contact_phone')
        )
        
        db.session.add(student)
        db.session.commit()
        
        return jsonify({
            'message': 'Student created successfully',
            'student': student.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@students_bp.route('/<int:student_id>', methods=['PUT'])
@jwt_required()
def update_student(student_id):
    """Update student information"""
    try:
        current_user = get_current_user()
        student = Student.query.get(student_id)
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Check permissions
        if (current_user.role == 'student' and student.user_id != current_user.id) or \
           (current_user.role not in ['admin', 'coordinator', 'student']):
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.get_json()
        
        # Update user information
        user = student.user
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'email' in data and current_user.role in ['admin', 'coordinator']:
            # Check if email is already taken
            existing_user = User.query.filter(
                User.email == data['email'], User.id != user.id
            ).first()
            if existing_user:
                return jsonify({'error': 'Email already exists'}), 400
            user.email = data['email']
        
        # Update student information
        if 'birth_date' in data:
            student.birth_date = data['birth_date']
        if 'gender' in data:
            student.gender = data['gender']
        if 'address' in data:
            student.address = data['address']
        if 'city' in data:
            student.city = data['city']
        if 'state' in data:
            student.state = data['state']
        if 'zip_code' in data:
            student.zip_code = data['zip_code']
        if 'emergency_contact_name' in data:
            student.emergency_contact_name = data['emergency_contact_name']
        if 'emergency_contact_phone' in data:
            student.emergency_contact_phone = data['emergency_contact_phone']
        
        # Only admin/coordinator can update these fields
        if current_user.role in ['admin', 'coordinator']:
            if 'student_number' in data:
                # Check if student number is already taken
                existing_student = Student.query.filter(
                    Student.student_number == data['student_number'], 
                    Student.id != student_id
                ).first()
                if existing_student:
                    return jsonify({'error': 'Student number already exists'}), 400
                student.student_number = data['student_number']
            
            if 'course_id' in data:
                course = Course.query.get(data['course_id'])
                if not course:
                    return jsonify({'error': 'Course not found'}), 404
                student.course_id = data['course_id']
            
            if 'status' in data:
                valid_statuses = ['active', 'inactive', 'graduated', 'dropped', 'suspended']
                if data['status'] in valid_statuses:
                    student.status = data['status']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Student updated successfully',
            'student': student.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@students_bp.route('/<int:student_id>', methods=['DELETE'])
@jwt_required()
@coordinator_or_admin_required
def delete_student(student_id):
    """Delete student (soft delete by setting status to inactive)"""
    try:
        student = Student.query.get(student_id)
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Soft delete - set status to inactive
        student.status = 'inactive'
        student.user.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Student deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@students_bp.route('/<int:student_id>/enrollments', methods=['GET'])
@jwt_required()
def get_student_enrollments(student_id):
    """Get student's enrollments"""
    try:
        current_user = get_current_user()
        student = Student.query.get(student_id)
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Check permissions
        if (current_user.role == 'student' and student.user_id != current_user.id) or \
           (current_user.role not in ['admin', 'coordinator', 'teacher', 'student']):
            return jsonify({'error': 'Permission denied'}), 403
        
        enrollments = [enrollment.to_dict() for enrollment in student.enrollments]
        
        return jsonify({'enrollments': enrollments}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@students_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_student_stats():
    """Get student statistics"""
    try:
        stats = {
            'total_students': Student.query.count(),
            'active_students': Student.query.filter(Student.status == 'active').count(),
            'students_by_status': {},
            'students_by_course': {}
        }
        
        # Count students by status
        statuses = ['active', 'inactive', 'graduated', 'dropped', 'suspended']
        for status in statuses:
            count = Student.query.filter(Student.status == status).count()
            stats['students_by_status'][status] = count
        
        # Count students by course
        courses = Course.query.all()
        for course in courses:
            count = Student.query.filter(Student.course_id == course.id, Student.status == 'active').count()
            stats['students_by_course'][course.name] = count
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

