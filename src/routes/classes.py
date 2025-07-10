from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models import db
from src.models.class_group import ClassGroup
from src.models.subject import Subject
from src.models.teacher import Teacher
from src.models.student import Student
from src.models.enrollment import Enrollment
from src.utils.decorators import coordinator_or_admin_required, teacher_or_above_required, get_current_user

classes_bp = Blueprint('classes', __name__)

@classes_bp.route('', methods=['GET'])
@jwt_required()
def get_classes():
    """Get all class groups with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        subject_id = request.args.get('subject_id', type=int)
        teacher_id = request.args.get('teacher_id', type=int)
        semester = request.args.get('semester')
        year = request.args.get('year', type=int)
        status = request.args.get('status')
        search = request.args.get('search')
        
        query = ClassGroup.query
        
        # Apply filters
        if subject_id:
            query = query.filter(ClassGroup.subject_id == subject_id)
        
        if teacher_id:
            query = query.filter(ClassGroup.teacher_id == teacher_id)
        
        if semester:
            query = query.filter(ClassGroup.semester == semester)
        
        if year:
            query = query.filter(ClassGroup.year == year)
        
        if status:
            query = query.filter(ClassGroup.status == status)
        
        if search:
            search_filter = f"%{search}%"
            query = query.join(Subject).filter(
                (ClassGroup.class_code.ilike(search_filter)) |
                (Subject.name.ilike(search_filter)) |
                (Subject.code.ilike(search_filter))
            )
        
        # Paginate results
        classes = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'classes': [class_group.to_dict() for class_group in classes.items],
            'total': classes.total,
            'pages': classes.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@classes_bp.route('/<int:class_id>', methods=['GET'])
@jwt_required()
def get_class(class_id):
    """Get specific class group by ID"""
    try:
        class_group = ClassGroup.query.get(class_id)
        
        if not class_group:
            return jsonify({'error': 'Class not found'}), 404
        
        return jsonify({'class': class_group.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@classes_bp.route('', methods=['POST'])
@jwt_required()
@coordinator_or_admin_required
def create_class():
    """Create new class group"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['subject_id', 'teacher_id', 'semester', 'year', 'class_code']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if subject exists
        subject = Subject.query.get(data['subject_id'])
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404
        
        # Check if teacher exists
        teacher = Teacher.query.get(data['teacher_id'])
        if not teacher:
            return jsonify({'error': 'Teacher not found'}), 404
        
        # Check if class code already exists for this subject/semester/year
        existing_class = ClassGroup.query.filter_by(
            subject_id=data['subject_id'],
            class_code=data['class_code'],
            semester=data['semester'],
            year=data['year']
        ).first()
        
        if existing_class:
            return jsonify({'error': 'Class code already exists for this subject/semester/year'}), 400
        
        # Create class group
        class_group = ClassGroup(
            subject_id=data['subject_id'],
            teacher_id=data['teacher_id'],
            semester=data['semester'],
            year=data['year'],
            class_code=data['class_code'],
            max_students=data.get('max_students', 50),
            schedule_info=data.get('schedule_info'),
            classroom=data.get('classroom'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date')
        )
        
        db.session.add(class_group)
        db.session.commit()
        
        return jsonify({
            'message': 'Class created successfully',
            'class': class_group.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@classes_bp.route('/<int:class_id>', methods=['PUT'])
@jwt_required()
@coordinator_or_admin_required
def update_class(class_id):
    """Update class group information"""
    try:
        class_group = ClassGroup.query.get(class_id)
        
        if not class_group:
            return jsonify({'error': 'Class not found'}), 404
        
        data = request.get_json()
        
        # Update class group information
        if 'teacher_id' in data:
            teacher = Teacher.query.get(data['teacher_id'])
            if not teacher:
                return jsonify({'error': 'Teacher not found'}), 404
            class_group.teacher_id = data['teacher_id']
        
        if 'max_students' in data:
            class_group.max_students = data['max_students']
        if 'schedule_info' in data:
            class_group.schedule_info = data['schedule_info']
        if 'classroom' in data:
            class_group.classroom = data['classroom']
        if 'status' in data:
            valid_statuses = ['planned', 'active', 'completed', 'cancelled']
            if data['status'] in valid_statuses:
                class_group.status = data['status']
        if 'start_date' in data:
            class_group.start_date = data['start_date']
        if 'end_date' in data:
            class_group.end_date = data['end_date']
        
        # Check if class code is being updated
        if 'class_code' in data and data['class_code'] != class_group.class_code:
            # Check if new code already exists for this subject/semester/year
            existing_class = ClassGroup.query.filter_by(
                subject_id=class_group.subject_id,
                class_code=data['class_code'],
                semester=class_group.semester,
                year=class_group.year
            ).first()
            
            if existing_class:
                return jsonify({'error': 'Class code already exists for this subject/semester/year'}), 400
            
            class_group.class_code = data['class_code']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Class updated successfully',
            'class': class_group.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@classes_bp.route('/<int:class_id>', methods=['DELETE'])
@jwt_required()
@coordinator_or_admin_required
def delete_class(class_id):
    """Delete class group (soft delete by setting status to cancelled)"""
    try:
        class_group = ClassGroup.query.get(class_id)
        
        if not class_group:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check if class has enrolled students
        enrolled_students_count = class_group.enrolled_students_count
        if enrolled_students_count > 0:
            return jsonify({
                'error': f'Cannot delete class with {enrolled_students_count} enrolled students'
            }), 400
        
        # Soft delete - set status to cancelled
        class_group.status = 'cancelled'
        db.session.commit()
        
        return jsonify({'message': 'Class deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@classes_bp.route('/<int:class_id>/students', methods=['GET'])
@jwt_required()
def get_class_students(class_id):
    """Get students enrolled in a specific class"""
    try:
        class_group = ClassGroup.query.get(class_id)
        
        if not class_group:
            return jsonify({'error': 'Class not found'}), 404
        
        status = request.args.get('status', 'enrolled')
        
        # Filter enrollments by status
        enrollments = [e for e in class_group.enrollments if e.status == status]
        
        students_data = []
        for enrollment in enrollments:
            student_data = enrollment.student.to_dict()
            student_data['enrollment'] = {
                'id': enrollment.id,
                'enrollment_date': enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
                'status': enrollment.status,
                'final_grade': float(enrollment.final_grade) if enrollment.final_grade else None,
                'final_status': enrollment.final_status,
                'attendance_percentage': enrollment.attendance_percentage
            }
            students_data.append(student_data)
        
        return jsonify({
            'class': class_group.to_dict(),
            'students': students_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@classes_bp.route('/<int:class_id>/students', methods=['POST'])
@jwt_required()
@coordinator_or_admin_required
def enroll_student(class_id):
    """Enroll a student in a class"""
    try:
        class_group = ClassGroup.query.get(class_id)
        
        if not class_group:
            return jsonify({'error': 'Class not found'}), 404
        
        data = request.get_json()
        
        if not data.get('student_id'):
            return jsonify({'error': 'student_id is required'}), 400
        
        student = Student.query.get(data['student_id'])
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Check if student is already enrolled
        existing_enrollment = Enrollment.query.filter_by(
            student_id=data['student_id'],
            class_group_id=class_id
        ).first()
        
        if existing_enrollment:
            return jsonify({'error': 'Student is already enrolled in this class'}), 400
        
        # Check if class is full
        if class_group.enrolled_students_count >= class_group.max_students:
            return jsonify({'error': 'Class is full'}), 400
        
        # Create enrollment
        enrollment = Enrollment(
            student_id=data['student_id'],
            class_group_id=class_id,
            enrollment_date=data.get('enrollment_date')
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        return jsonify({
            'message': 'Student enrolled successfully',
            'enrollment': enrollment.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@classes_bp.route('/<int:class_id>/students/<int:student_id>', methods=['DELETE'])
@jwt_required()
@coordinator_or_admin_required
def unenroll_student(class_id, student_id):
    """Unenroll a student from a class"""
    try:
        enrollment = Enrollment.query.filter_by(
            student_id=student_id,
            class_group_id=class_id
        ).first()
        
        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404
        
        # Set enrollment status to dropped
        enrollment.status = 'dropped'
        db.session.commit()
        
        return jsonify({'message': 'Student unenrolled successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@classes_bp.route('/my-classes', methods=['GET'])
@jwt_required()
def get_my_classes():
    """Get classes for the current user (teacher or student)"""
    try:
        current_user = get_current_user()
        
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if not teacher:
                return jsonify({'error': 'Teacher profile not found'}), 404
            
            semester = request.args.get('semester')
            year = request.args.get('year', type=int)
            
            query = teacher.class_groups
            if semester:
                query = [cg for cg in query if cg.semester == semester]
            if year:
                query = [cg for cg in query if cg.year == year]
            
            classes = [class_group.to_dict() for class_group in query]
            
        elif current_user.role == 'student':
            student = Student.query.filter_by(user_id=current_user.id).first()
            if not student:
                return jsonify({'error': 'Student profile not found'}), 404
            
            semester = request.args.get('semester')
            year = request.args.get('year', type=int)
            status = request.args.get('status', 'enrolled')
            
            enrollments = [e for e in student.enrollments if e.status == status]
            
            if semester:
                enrollments = [e for e in enrollments if e.class_group.semester == semester]
            if year:
                enrollments = [e for e in enrollments if e.class_group.year == year]
            
            classes = []
            for enrollment in enrollments:
                class_data = enrollment.class_group.to_dict()
                class_data['enrollment'] = {
                    'id': enrollment.id,
                    'enrollment_date': enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
                    'status': enrollment.status,
                    'final_grade': float(enrollment.final_grade) if enrollment.final_grade else None,
                    'final_status': enrollment.final_status,
                    'attendance_percentage': enrollment.attendance_percentage
                }
                classes.append(class_data)
        
        else:
            return jsonify({'error': 'Only teachers and students can access this endpoint'}), 403
        
        return jsonify({'classes': classes}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@classes_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_class_stats():
    """Get class statistics"""
    try:
        stats = {
            'total_classes': ClassGroup.query.count(),
            'active_classes': ClassGroup.query.filter(ClassGroup.status == 'active').count(),
            'classes_by_status': {},
            'classes_by_semester': {},
            'average_enrollment': 0
        }
        
        # Count classes by status
        statuses = ['planned', 'active', 'completed', 'cancelled']
        for status in statuses:
            count = ClassGroup.query.filter(ClassGroup.status == status).count()
            stats['classes_by_status'][status] = count
        
        # Count classes by current semester/year
        from datetime import datetime
        current_year = datetime.now().year
        current_month = datetime.now().month
        current_semester = f"{current_year}.1" if current_month <= 6 else f"{current_year}.2"
        
        semester_classes = ClassGroup.query.filter(ClassGroup.semester == current_semester).all()
        for class_group in semester_classes:
            semester_key = f"{class_group.semester}"
            if semester_key not in stats['classes_by_semester']:
                stats['classes_by_semester'][semester_key] = 0
            stats['classes_by_semester'][semester_key] += 1
        
        # Calculate average enrollment
        active_classes = ClassGroup.query.filter(ClassGroup.status.in_(['active', 'planned'])).all()
        if active_classes:
            total_enrollment = sum(cg.enrolled_students_count for cg in active_classes)
            stats['average_enrollment'] = round(total_enrollment / len(active_classes), 2)
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

