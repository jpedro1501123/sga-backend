from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models import db
from src.models.course import Course
from src.models.institution import Institution
from src.utils.decorators import coordinator_or_admin_required

courses_bp = Blueprint('courses', __name__)

@courses_bp.route('', methods=['GET'])
@jwt_required()
def get_courses():
    """Get all courses with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        institution_id = request.args.get('institution_id', type=int)
        degree_type = request.args.get('degree_type')
        search = request.args.get('search')
        is_active = request.args.get('is_active', type=bool)
        
        query = Course.query
        
        # Apply filters
        if institution_id:
            query = query.filter(Course.institution_id == institution_id)
        
        if degree_type:
            query = query.filter(Course.degree_type == degree_type)
        
        if is_active is not None:
            query = query.filter(Course.is_active == is_active)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (Course.name.ilike(search_filter)) |
                (Course.code.ilike(search_filter)) |
                (Course.description.ilike(search_filter))
            )
        
        # Paginate results
        courses = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'courses': [course.to_dict() for course in courses.items],
            'total': courses.total,
            'pages': courses.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@courses_bp.route('/<int:course_id>', methods=['GET'])
@jwt_required()
def get_course(course_id):
    """Get specific course by ID"""
    try:
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        return jsonify({'course': course.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@courses_bp.route('', methods=['POST'])
@jwt_required()
@coordinator_or_admin_required
def create_course():
    """Create new course"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['institution_id', 'name', 'code', 'duration_semesters', 'degree_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if institution exists
        institution = Institution.query.get(data['institution_id'])
        if not institution:
            return jsonify({'error': 'Institution not found'}), 404
        
        # Check if course code already exists for this institution
        existing_course = Course.query.filter_by(
            institution_id=data['institution_id'],
            code=data['code']
        ).first()
        
        if existing_course:
            return jsonify({'error': 'Course code already exists for this institution'}), 400
        
        # Validate degree type
        valid_degrees = ['bachelor', 'master', 'doctorate', 'technical', 'other']
        if data['degree_type'] not in valid_degrees:
            return jsonify({'error': 'Invalid degree type'}), 400
        
        # Create course
        course = Course(
            institution_id=data['institution_id'],
            name=data['name'],
            code=data['code'],
            description=data.get('description'),
            duration_semesters=data['duration_semesters'],
            total_credits=data.get('total_credits'),
            degree_type=data['degree_type']
        )
        
        db.session.add(course)
        db.session.commit()
        
        return jsonify({
            'message': 'Course created successfully',
            'course': course.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@courses_bp.route('/<int:course_id>', methods=['PUT'])
@jwt_required()
@coordinator_or_admin_required
def update_course(course_id):
    """Update course information"""
    try:
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        data = request.get_json()
        
        # Update course information
        if 'name' in data:
            course.name = data['name']
        if 'description' in data:
            course.description = data['description']
        if 'duration_semesters' in data:
            course.duration_semesters = data['duration_semesters']
        if 'total_credits' in data:
            course.total_credits = data['total_credits']
        if 'degree_type' in data:
            valid_degrees = ['bachelor', 'master', 'doctorate', 'technical', 'other']
            if data['degree_type'] in valid_degrees:
                course.degree_type = data['degree_type']
        if 'is_active' in data:
            course.is_active = data['is_active']
        
        # Check if code is being updated
        if 'code' in data and data['code'] != course.code:
            # Check if new code already exists for this institution
            existing_course = Course.query.filter_by(
                institution_id=course.institution_id,
                code=data['code']
            ).first()
            
            if existing_course:
                return jsonify({'error': 'Course code already exists for this institution'}), 400
            
            course.code = data['code']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Course updated successfully',
            'course': course.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@courses_bp.route('/<int:course_id>', methods=['DELETE'])
@jwt_required()
@coordinator_or_admin_required
def delete_course(course_id):
    """Delete course (soft delete by setting is_active to False)"""
    try:
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if course has active students
        active_students_count = len([s for s in course.students if s.status == 'active'])
        if active_students_count > 0:
            return jsonify({
                'error': f'Cannot delete course with {active_students_count} active students'
            }), 400
        
        # Soft delete - set is_active to False
        course.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Course deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@courses_bp.route('/<int:course_id>/subjects', methods=['GET'])
@jwt_required()
def get_course_subjects(course_id):
    """Get subjects for a specific course"""
    try:
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        semester = request.args.get('semester', type=int)
        is_mandatory = request.args.get('is_mandatory', type=bool)
        
        query = course.subjects
        
        # Apply filters
        if semester is not None:
            query = [s for s in query if s.semester == semester]
        if is_mandatory is not None:
            query = [s for s in query if s.is_mandatory == is_mandatory]
        
        subjects = [subject.to_dict() for subject in query if subject.is_active]
        
        return jsonify({'subjects': subjects}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@courses_bp.route('/<int:course_id>/students', methods=['GET'])
@jwt_required()
def get_course_students(course_id):
    """Get students enrolled in a specific course"""
    try:
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        status = request.args.get('status', 'active')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Filter students by status
        students_query = [s for s in course.students if s.status == status]
        
        # Simple pagination for list
        start = (page - 1) * per_page
        end = start + per_page
        students_page = students_query[start:end]
        
        return jsonify({
            'students': [student.to_dict() for student in students_page],
            'total': len(students_query),
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@courses_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_course_stats():
    """Get course statistics"""
    try:
        stats = {
            'total_courses': Course.query.count(),
            'active_courses': Course.query.filter(Course.is_active == True).count(),
            'courses_by_degree_type': {},
            'courses_by_institution': {}
        }
        
        # Count courses by degree type
        degree_types = ['bachelor', 'master', 'doctorate', 'technical', 'other']
        for degree_type in degree_types:
            count = Course.query.filter(Course.degree_type == degree_type, Course.is_active == True).count()
            stats['courses_by_degree_type'][degree_type] = count
        
        # Count courses by institution
        institutions = Institution.query.filter(Institution.is_active == True).all()
        for institution in institutions:
            count = Course.query.filter(Course.institution_id == institution.id, Course.is_active == True).count()
            stats['courses_by_institution'][institution.name] = count
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

