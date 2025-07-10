from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models import db
from src.models.subject import Subject
from src.models.course import Course
from src.utils.decorators import coordinator_or_admin_required

subjects_bp = Blueprint('subjects', __name__)

@subjects_bp.route('', methods=['GET'])
@jwt_required()
def get_subjects():
    """Get all subjects with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        course_id = request.args.get('course_id', type=int)
        semester = request.args.get('semester', type=int)
        is_mandatory = request.args.get('is_mandatory', type=bool)
        search = request.args.get('search')
        is_active = request.args.get('is_active', type=bool)
        
        query = Subject.query
        
        # Apply filters
        if course_id:
            query = query.filter(Subject.course_id == course_id)
        
        if semester is not None:
            query = query.filter(Subject.semester == semester)
        
        if is_mandatory is not None:
            query = query.filter(Subject.is_mandatory == is_mandatory)
        
        if is_active is not None:
            query = query.filter(Subject.is_active == is_active)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (Subject.name.ilike(search_filter)) |
                (Subject.code.ilike(search_filter)) |
                (Subject.description.ilike(search_filter))
            )
        
        # Paginate results
        subjects = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'subjects': [subject.to_dict() for subject in subjects.items],
            'total': subjects.total,
            'pages': subjects.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subjects_bp.route('/<int:subject_id>', methods=['GET'])
@jwt_required()
def get_subject(subject_id):
    """Get specific subject by ID"""
    try:
        subject = Subject.query.get(subject_id)
        
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404
        
        return jsonify({'subject': subject.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subjects_bp.route('', methods=['POST'])
@jwt_required()
@coordinator_or_admin_required
def create_subject():
    """Create new subject"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['course_id', 'name', 'code', 'credits', 'workload_hours']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if course exists
        course = Course.query.get(data['course_id'])
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Check if subject code already exists for this course
        existing_subject = Subject.query.filter_by(
            course_id=data['course_id'],
            code=data['code']
        ).first()
        
        if existing_subject:
            return jsonify({'error': 'Subject code already exists for this course'}), 400
        
        # Create subject
        subject = Subject(
            course_id=data['course_id'],
            name=data['name'],
            code=data['code'],
            description=data.get('description'),
            credits=data['credits'],
            workload_hours=data['workload_hours'],
            semester=data.get('semester'),
            is_mandatory=data.get('is_mandatory', True),
            prerequisites=data.get('prerequisites'),
            syllabus=data.get('syllabus')
        )
        
        db.session.add(subject)
        db.session.commit()
        
        return jsonify({
            'message': 'Subject created successfully',
            'subject': subject.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@subjects_bp.route('/<int:subject_id>', methods=['PUT'])
@jwt_required()
@coordinator_or_admin_required
def update_subject(subject_id):
    """Update subject information"""
    try:
        subject = Subject.query.get(subject_id)
        
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404
        
        data = request.get_json()
        
        # Update subject information
        if 'name' in data:
            subject.name = data['name']
        if 'description' in data:
            subject.description = data['description']
        if 'credits' in data:
            subject.credits = data['credits']
        if 'workload_hours' in data:
            subject.workload_hours = data['workload_hours']
        if 'semester' in data:
            subject.semester = data['semester']
        if 'is_mandatory' in data:
            subject.is_mandatory = data['is_mandatory']
        if 'prerequisites' in data:
            subject.prerequisites = data['prerequisites']
        if 'syllabus' in data:
            subject.syllabus = data['syllabus']
        if 'is_active' in data:
            subject.is_active = data['is_active']
        
        # Check if code is being updated
        if 'code' in data and data['code'] != subject.code:
            # Check if new code already exists for this course
            existing_subject = Subject.query.filter_by(
                course_id=subject.course_id,
                code=data['code']
            ).first()
            
            if existing_subject:
                return jsonify({'error': 'Subject code already exists for this course'}), 400
            
            subject.code = data['code']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Subject updated successfully',
            'subject': subject.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@subjects_bp.route('/<int:subject_id>', methods=['DELETE'])
@jwt_required()
@coordinator_or_admin_required
def delete_subject(subject_id):
    """Delete subject (soft delete by setting is_active to False)"""
    try:
        subject = Subject.query.get(subject_id)
        
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404
        
        # Check if subject has active class groups
        active_classes_count = len([cg for cg in subject.class_groups if cg.status in ['planned', 'active']])
        if active_classes_count > 0:
            return jsonify({
                'error': f'Cannot delete subject with {active_classes_count} active class groups'
            }), 400
        
        # Soft delete - set is_active to False
        subject.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Subject deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@subjects_bp.route('/<int:subject_id>/classes', methods=['GET'])
@jwt_required()
def get_subject_classes(subject_id):
    """Get class groups for a specific subject"""
    try:
        subject = Subject.query.get(subject_id)
        
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404
        
        semester = request.args.get('semester')
        year = request.args.get('year', type=int)
        status = request.args.get('status')
        
        query = subject.class_groups
        
        # Apply filters
        if semester:
            query = [cg for cg in query if cg.semester == semester]
        if year:
            query = [cg for cg in query if cg.year == year]
        if status:
            query = [cg for cg in query if cg.status == status]
        
        classes = [class_group.to_dict() for class_group in query]
        
        return jsonify({'classes': classes}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subjects_bp.route('/by-course/<int:course_id>', methods=['GET'])
@jwt_required()
def get_subjects_by_course(course_id):
    """Get all subjects for a specific course organized by semester"""
    try:
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        subjects = Subject.query.filter_by(course_id=course_id, is_active=True).all()
        
        # Organize subjects by semester
        subjects_by_semester = {}
        for subject in subjects:
            semester = subject.semester or 0  # Use 0 for subjects without defined semester
            if semester not in subjects_by_semester:
                subjects_by_semester[semester] = []
            subjects_by_semester[semester].append(subject.to_dict())
        
        return jsonify({
            'course': course.to_dict(),
            'subjects_by_semester': subjects_by_semester
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subjects_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_subject_stats():
    """Get subject statistics"""
    try:
        stats = {
            'total_subjects': Subject.query.count(),
            'active_subjects': Subject.query.filter(Subject.is_active == True).count(),
            'mandatory_subjects': Subject.query.filter(Subject.is_mandatory == True, Subject.is_active == True).count(),
            'elective_subjects': Subject.query.filter(Subject.is_mandatory == False, Subject.is_active == True).count(),
            'subjects_by_course': {},
            'average_credits': 0,
            'average_workload': 0
        }
        
        # Count subjects by course
        courses = Course.query.filter(Course.is_active == True).all()
        for course in courses:
            count = Subject.query.filter(Subject.course_id == course.id, Subject.is_active == True).count()
            stats['subjects_by_course'][course.name] = count
        
        # Calculate averages
        active_subjects = Subject.query.filter(Subject.is_active == True).all()
        if active_subjects:
            total_credits = sum(s.credits for s in active_subjects)
            total_workload = sum(s.workload_hours for s in active_subjects)
            stats['average_credits'] = round(total_credits / len(active_subjects), 2)
            stats['average_workload'] = round(total_workload / len(active_subjects), 2)
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

