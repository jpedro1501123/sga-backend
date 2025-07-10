from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models import db
from src.models.user import User
from src.models.teacher import Teacher
from src.utils.decorators import coordinator_or_admin_required, get_current_user

teachers_bp = Blueprint('teachers', __name__)

@teachers_bp.route('', methods=['GET'])
@jwt_required()
def get_teachers():
    """Get all teachers with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        department = request.args.get('department')
        status = request.args.get('status')
        search = request.args.get('search')
        
        query = Teacher.query.join(User)
        
        # Apply filters
        if department:
            query = query.filter(Teacher.department.ilike(f"%{department}%"))
        
        if status:
            query = query.filter(Teacher.status == status)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (User.first_name.ilike(search_filter)) |
                (User.last_name.ilike(search_filter)) |
                (User.email.ilike(search_filter)) |
                (Teacher.employee_number.ilike(search_filter))
            )
        
        # Paginate results
        teachers = query.paginate(
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
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@teachers_bp.route('/<int:teacher_id>', methods=['GET'])
@jwt_required()
def get_teacher(teacher_id):
    """Get specific teacher by ID"""
    try:
        teacher = Teacher.query.get(teacher_id)
        
        if not teacher:
            return jsonify({'error': 'Teacher not found'}), 404
        
        return jsonify({'teacher': teacher.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@teachers_bp.route('', methods=['POST'])
@jwt_required()
@coordinator_or_admin_required
def create_teacher():
    """Create new teacher"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 
                          'employee_number', 'academic_degree']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if username, email or employee_number already exists
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        
        if existing_user:
            return jsonify({'error': 'Username or email already exists'}), 400
        
        existing_teacher = Teacher.query.filter_by(employee_number=data['employee_number']).first()
        if existing_teacher:
            return jsonify({'error': 'Employee number already exists'}), 400
        
        # Validate academic degree
        valid_degrees = ['bachelor', 'master', 'doctorate', 'post_doctorate']
        if data['academic_degree'] not in valid_degrees:
            return jsonify({'error': 'Invalid academic degree'}), 400
        
        # Create user first
        user = User(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role='teacher',
            phone=data.get('phone')
        )
        
        db.session.add(user)
        db.session.flush()  # To get user ID
        
        # Create teacher
        teacher = Teacher(
            user_id=user.id,
            employee_number=data['employee_number'],
            department=data.get('department'),
            specialization=data.get('specialization'),
            academic_degree=data['academic_degree'],
            hire_date=data.get('hire_date'),
            birth_date=data.get('birth_date'),
            gender=data.get('gender'),
            document_type=data.get('document_type'),
            document_number=data.get('document_number'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code')
        )
        
        db.session.add(teacher)
        db.session.commit()
        
        return jsonify({
            'message': 'Teacher created successfully',
            'teacher': teacher.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@teachers_bp.route('/<int:teacher_id>', methods=['PUT'])
@jwt_required()
def update_teacher(teacher_id):
    """Update teacher information"""
    try:
        current_user = get_current_user()
        teacher = Teacher.query.get(teacher_id)
        
        if not teacher:
            return jsonify({'error': 'Teacher not found'}), 404
        
        # Check permissions
        if (current_user.role == 'teacher' and teacher.user_id != current_user.id) or \
           (current_user.role not in ['admin', 'coordinator', 'teacher']):
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.get_json()
        
        # Update user information
        user = teacher.user
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
        
        # Update teacher information
        if 'specialization' in data:
            teacher.specialization = data['specialization']
        if 'birth_date' in data:
            teacher.birth_date = data['birth_date']
        if 'gender' in data:
            teacher.gender = data['gender']
        if 'address' in data:
            teacher.address = data['address']
        if 'city' in data:
            teacher.city = data['city']
        if 'state' in data:
            teacher.state = data['state']
        if 'zip_code' in data:
            teacher.zip_code = data['zip_code']
        
        # Only admin/coordinator can update these fields
        if current_user.role in ['admin', 'coordinator']:
            if 'employee_number' in data:
                # Check if employee number is already taken
                existing_teacher = Teacher.query.filter(
                    Teacher.employee_number == data['employee_number'], 
                    Teacher.id != teacher_id
                ).first()
                if existing_teacher:
                    return jsonify({'error': 'Employee number already exists'}), 400
                teacher.employee_number = data['employee_number']
            
            if 'department' in data:
                teacher.department = data['department']
            
            if 'academic_degree' in data:
                valid_degrees = ['bachelor', 'master', 'doctorate', 'post_doctorate']
                if data['academic_degree'] in valid_degrees:
                    teacher.academic_degree = data['academic_degree']
            
            if 'status' in data:
                valid_statuses = ['active', 'inactive', 'on_leave']
                if data['status'] in valid_statuses:
                    teacher.status = data['status']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Teacher updated successfully',
            'teacher': teacher.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@teachers_bp.route('/<int:teacher_id>', methods=['DELETE'])
@jwt_required()
@coordinator_or_admin_required
def delete_teacher(teacher_id):
    """Delete teacher (soft delete by setting status to inactive)"""
    try:
        teacher = Teacher.query.get(teacher_id)
        
        if not teacher:
            return jsonify({'error': 'Teacher not found'}), 404
        
        # Soft delete - set status to inactive
        teacher.status = 'inactive'
        teacher.user.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Teacher deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@teachers_bp.route('/<int:teacher_id>/classes', methods=['GET'])
@jwt_required()
def get_teacher_classes(teacher_id):
    """Get teacher's classes"""
    try:
        current_user = get_current_user()
        teacher = Teacher.query.get(teacher_id)
        
        if not teacher:
            return jsonify({'error': 'Teacher not found'}), 404
        
        # Check permissions
        if (current_user.role == 'teacher' and teacher.user_id != current_user.id) or \
           (current_user.role not in ['admin', 'coordinator', 'teacher']):
            return jsonify({'error': 'Permission denied'}), 403
        
        semester = request.args.get('semester')
        year = request.args.get('year', type=int)
        
        query = teacher.class_groups
        if semester:
            query = [cg for cg in query if cg.semester == semester]
        if year:
            query = [cg for cg in query if cg.year == year]
        
        classes = [class_group.to_dict() for class_group in query]
        
        return jsonify({'classes': classes}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@teachers_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_teacher_stats():
    """Get teacher statistics"""
    try:
        stats = {
            'total_teachers': Teacher.query.count(),
            'active_teachers': Teacher.query.filter(Teacher.status == 'active').count(),
            'teachers_by_status': {},
            'teachers_by_department': {},
            'teachers_by_degree': {}
        }
        
        # Count teachers by status
        statuses = ['active', 'inactive', 'on_leave']
        for status in statuses:
            count = Teacher.query.filter(Teacher.status == status).count()
            stats['teachers_by_status'][status] = count
        
        # Count teachers by department
        departments = db.session.query(Teacher.department).distinct().all()
        for (dept,) in departments:
            if dept:
                count = Teacher.query.filter(Teacher.department == dept, Teacher.status == 'active').count()
                stats['teachers_by_department'][dept] = count
        
        # Count teachers by academic degree
        degrees = ['bachelor', 'master', 'doctorate', 'post_doctorate']
        for degree in degrees:
            count = Teacher.query.filter(Teacher.academic_degree == degree, Teacher.status == 'active').count()
            stats['teachers_by_degree'][degree] = count
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

