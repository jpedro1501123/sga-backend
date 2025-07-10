from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime
from src.models import db
from src.models.grade import Grade
from src.models.evaluation import Evaluation
from src.models.evaluation_type import EvaluationType
from src.models.enrollment import Enrollment
from src.models.class_group import ClassGroup
from src.models.teacher import Teacher
from src.models.student import Student
from src.utils.decorators import teacher_or_above_required, get_current_user

grades_bp = Blueprint('grades', __name__)

@grades_bp.route('', methods=['GET'])
@jwt_required()
def get_grades():
    """Get grades with pagination and filtering"""
    try:
        current_user = get_current_user()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        class_id = request.args.get('class_id', type=int)
        student_id = request.args.get('student_id', type=int)
        evaluation_id = request.args.get('evaluation_id', type=int)
        
        query = Grade.query.join(Enrollment).join(ClassGroup)
        
        # Apply role-based filtering
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if teacher:
                query = query.filter(ClassGroup.teacher_id == teacher.id)
        elif current_user.role == 'student':
            student = Student.query.filter_by(user_id=current_user.id).first()
            if student:
                query = query.filter(Enrollment.student_id == student.id)
        
        # Apply additional filters
        if class_id:
            query = query.filter(ClassGroup.id == class_id)
        
        if student_id and current_user.role in ['admin', 'coordinator', 'teacher']:
            query = query.filter(Enrollment.student_id == student_id)
        
        if evaluation_id:
            query = query.filter(Grade.evaluation_id == evaluation_id)
        
        # Paginate results
        grades = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'grades': [grade.to_dict() for grade in grades.items],
            'total': grades.total,
            'pages': grades.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@grades_bp.route('/<int:grade_id>', methods=['GET'])
@jwt_required()
def get_grade(grade_id):
    """Get specific grade by ID"""
    try:
        grade = Grade.query.get(grade_id)
        
        if not grade:
            return jsonify({'error': 'Grade not found'}), 404
        
        return jsonify({'grade': grade.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@grades_bp.route('', methods=['POST'])
@jwt_required()
@teacher_or_above_required
def create_grade():
    """Create or update a grade"""
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['enrollment_id', 'evaluation_id', 'score']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if enrollment exists
        enrollment = Enrollment.query.get(data['enrollment_id'])
        if not enrollment:
            return jsonify({'error': 'Enrollment not found'}), 404
        
        # Check if evaluation exists
        evaluation = Evaluation.query.get(data['evaluation_id'])
        if not evaluation:
            return jsonify({'error': 'Evaluation not found'}), 404
        
        # Check if teacher has permission to grade this class
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if not teacher or evaluation.class_group.teacher_id != teacher.id:
                return jsonify({'error': 'Permission denied'}), 403
        
        # Validate score
        if data['score'] is not None:
            if data['score'] < 0 or data['score'] > float(evaluation.max_score):
                return jsonify({'error': f'Score must be between 0 and {evaluation.max_score}'}), 400
        
        # Check if grade already exists
        existing_grade = Grade.query.filter_by(
            enrollment_id=data['enrollment_id'],
            evaluation_id=data['evaluation_id']
        ).first()
        
        if existing_grade:
            # Update existing grade
            existing_grade.score = data['score']
            existing_grade.comments = data.get('comments')
            if current_user.role == 'teacher':
                teacher = Teacher.query.filter_by(user_id=current_user.id).first()
                existing_grade.graded_by = teacher.id if teacher else None
            existing_grade.graded_at = datetime.utcnow()
            
            db.session.commit()
            
            # Update enrollment final grade
            enrollment.final_grade = enrollment.calculate_final_grade()
            db.session.commit()
            
            return jsonify({
                'message': 'Grade updated successfully',
                'grade': existing_grade.to_dict()
            }), 200
        else:
            # Create new grade
            grade = Grade(
                enrollment_id=data['enrollment_id'],
                evaluation_id=data['evaluation_id'],
                score=data['score'],
                comments=data.get('comments'),
                graded_at=datetime.utcnow()
            )
            
            if current_user.role == 'teacher':
                teacher = Teacher.query.filter_by(user_id=current_user.id).first()
                grade.graded_by = teacher.id if teacher else None
            
            db.session.add(grade)
            db.session.commit()
            
            # Update enrollment final grade
            enrollment.final_grade = enrollment.calculate_final_grade()
            db.session.commit()
            
            return jsonify({
                'message': 'Grade created successfully',
                'grade': grade.to_dict()
            }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@grades_bp.route('/batch', methods=['POST'])
@jwt_required()
@teacher_or_above_required
def create_grades_batch():
    """Create or update multiple grades at once"""
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        if not data.get('grades') or not isinstance(data['grades'], list):
            return jsonify({'error': 'grades array is required'}), 400
        
        teacher = None
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
        
        created_grades = []
        updated_grades = []
        errors = []
        
        for i, grade_data in enumerate(data['grades']):
            try:
                # Validate required fields
                required_fields = ['enrollment_id', 'evaluation_id', 'score']
                for field in required_fields:
                    if field not in grade_data:
                        errors.append(f'Grade {i+1}: {field} is required')
                        continue
                
                # Check if enrollment and evaluation exist
                enrollment = Enrollment.query.get(grade_data['enrollment_id'])
                evaluation = Evaluation.query.get(grade_data['evaluation_id'])
                
                if not enrollment:
                    errors.append(f'Grade {i+1}: Enrollment not found')
                    continue
                
                if not evaluation:
                    errors.append(f'Grade {i+1}: Evaluation not found')
                    continue
                
                # Check teacher permission
                if teacher and evaluation.class_group.teacher_id != teacher.id:
                    errors.append(f'Grade {i+1}: Permission denied')
                    continue
                
                # Validate score
                if grade_data['score'] is not None:
                    if grade_data['score'] < 0 or grade_data['score'] > float(evaluation.max_score):
                        errors.append(f'Grade {i+1}: Score must be between 0 and {evaluation.max_score}')
                        continue
                
                # Check if grade already exists
                existing_grade = Grade.query.filter_by(
                    enrollment_id=grade_data['enrollment_id'],
                    evaluation_id=grade_data['evaluation_id']
                ).first()
                
                if existing_grade:
                    # Update existing grade
                    existing_grade.score = grade_data['score']
                    existing_grade.comments = grade_data.get('comments')
                    existing_grade.graded_by = teacher.id if teacher else None
                    existing_grade.graded_at = datetime.utcnow()
                    updated_grades.append(existing_grade.to_dict())
                else:
                    # Create new grade
                    grade = Grade(
                        enrollment_id=grade_data['enrollment_id'],
                        evaluation_id=grade_data['evaluation_id'],
                        score=grade_data['score'],
                        comments=grade_data.get('comments'),
                        graded_by=teacher.id if teacher else None,
                        graded_at=datetime.utcnow()
                    )
                    
                    db.session.add(grade)
                    created_grades.append(grade_data)
                
                # Update enrollment final grade
                enrollment.final_grade = enrollment.calculate_final_grade()
                
            except Exception as e:
                errors.append(f'Grade {i+1}: {str(e)}')
        
        if errors:
            db.session.rollback()
            return jsonify({'errors': errors}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': 'Grades processed successfully',
            'created': len(created_grades),
            'updated': len(updated_grades),
            'errors': len(errors)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@grades_bp.route('/<int:grade_id>', methods=['PUT'])
@jwt_required()
@teacher_or_above_required
def update_grade(grade_id):
    """Update a specific grade"""
    try:
        current_user = get_current_user()
        grade = Grade.query.get(grade_id)
        
        if not grade:
            return jsonify({'error': 'Grade not found'}), 404
        
        # Check teacher permission
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if not teacher or grade.evaluation.class_group.teacher_id != teacher.id:
                return jsonify({'error': 'Permission denied'}), 403
        
        data = request.get_json()
        
        # Update grade information
        if 'score' in data:
            if data['score'] is not None:
                if data['score'] < 0 or data['score'] > float(grade.evaluation.max_score):
                    return jsonify({'error': f'Score must be between 0 and {grade.evaluation.max_score}'}), 400
            grade.score = data['score']
        
        if 'comments' in data:
            grade.comments = data['comments']
        
        grade.graded_at = datetime.utcnow()
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            grade.graded_by = teacher.id if teacher else None
        
        db.session.commit()
        
        # Update enrollment final grade
        grade.enrollment.final_grade = grade.enrollment.calculate_final_grade()
        db.session.commit()
        
        return jsonify({
            'message': 'Grade updated successfully',
            'grade': grade.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@grades_bp.route('/<int:grade_id>', methods=['DELETE'])
@jwt_required()
@teacher_or_above_required
def delete_grade(grade_id):
    """Delete a grade"""
    try:
        current_user = get_current_user()
        grade = Grade.query.get(grade_id)
        
        if not grade:
            return jsonify({'error': 'Grade not found'}), 404
        
        # Check teacher permission
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if not teacher or grade.evaluation.class_group.teacher_id != teacher.id:
                return jsonify({'error': 'Permission denied'}), 403
        
        enrollment = grade.enrollment
        db.session.delete(grade)
        db.session.commit()
        
        # Update enrollment final grade
        enrollment.final_grade = enrollment.calculate_final_grade()
        db.session.commit()
        
        return jsonify({'message': 'Grade deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@grades_bp.route('/evaluations', methods=['GET'])
@jwt_required()
def get_evaluations():
    """Get evaluations with filtering"""
    try:
        current_user = get_current_user()
        class_id = request.args.get('class_id', type=int)
        evaluation_type_id = request.args.get('evaluation_type_id', type=int)
        
        query = Evaluation.query.join(ClassGroup)
        
        # Apply role-based filtering
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if teacher:
                query = query.filter(ClassGroup.teacher_id == teacher.id)
        
        # Apply additional filters
        if class_id:
            query = query.filter(Evaluation.class_group_id == class_id)
        
        if evaluation_type_id:
            query = query.filter(Evaluation.evaluation_type_id == evaluation_type_id)
        
        evaluations = query.all()
        
        return jsonify({
            'evaluations': [evaluation.to_dict() for evaluation in evaluations]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@grades_bp.route('/evaluations', methods=['POST'])
@jwt_required()
@teacher_or_above_required
def create_evaluation():
    """Create new evaluation"""
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['class_group_id', 'evaluation_type_id', 'name', 'weight', 'max_score']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if class group exists
        class_group = ClassGroup.query.get(data['class_group_id'])
        if not class_group:
            return jsonify({'error': 'Class group not found'}), 404
        
        # Check teacher permission
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if not teacher or class_group.teacher_id != teacher.id:
                return jsonify({'error': 'Permission denied'}), 403
        
        # Check if evaluation type exists
        evaluation_type = EvaluationType.query.get(data['evaluation_type_id'])
        if not evaluation_type:
            return jsonify({'error': 'Evaluation type not found'}), 404
        
        # Create evaluation
        evaluation = Evaluation(
            class_group_id=data['class_group_id'],
            evaluation_type_id=data['evaluation_type_id'],
            name=data['name'],
            description=data.get('description'),
            weight=data['weight'],
            max_score=data['max_score'],
            evaluation_date=data.get('evaluation_date'),
            due_date=data.get('due_date')
        )
        
        db.session.add(evaluation)
        db.session.commit()
        
        return jsonify({
            'message': 'Evaluation created successfully',
            'evaluation': evaluation.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@grades_bp.route('/evaluation-types', methods=['GET'])
@jwt_required()
def get_evaluation_types():
    """Get all evaluation types"""
    try:
        evaluation_types = EvaluationType.query.filter_by(is_active=True).all()
        
        return jsonify({
            'evaluation_types': [et.to_dict() for et in evaluation_types]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@grades_bp.route('/class/<int:class_id>/gradebook', methods=['GET'])
@jwt_required()
@teacher_or_above_required
def get_class_gradebook(class_id):
    """Get complete gradebook for a class"""
    try:
        current_user = get_current_user()
        class_group = ClassGroup.query.get(class_id)
        
        if not class_group:
            return jsonify({'error': 'Class not found'}), 404
        
        # Check teacher permission
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if not teacher or class_group.teacher_id != teacher.id:
                return jsonify({'error': 'Permission denied'}), 403
        
        # Get all evaluations for this class
        evaluations = Evaluation.query.filter_by(class_group_id=class_id).all()
        
        # Get all enrollments for this class
        enrollments = Enrollment.query.filter_by(class_group_id=class_id, status='enrolled').all()
        
        # Build gradebook data
        gradebook = {
            'class': class_group.to_dict(),
            'evaluations': [eval.to_dict() for eval in evaluations],
            'students': []
        }
        
        for enrollment in enrollments:
            student_data = {
                'student': enrollment.student.to_dict(),
                'enrollment': {
                    'id': enrollment.id,
                    'final_grade': float(enrollment.final_grade) if enrollment.final_grade else None,
                    'final_status': enrollment.final_status,
                    'attendance_percentage': enrollment.attendance_percentage
                },
                'grades': {}
            }
            
            # Get grades for each evaluation
            for evaluation in evaluations:
                grade = Grade.query.filter_by(
                    enrollment_id=enrollment.id,
                    evaluation_id=evaluation.id
                ).first()
                
                student_data['grades'][evaluation.id] = {
                    'score': float(grade.score) if grade and grade.score else None,
                    'comments': grade.comments if grade else None,
                    'graded_at': grade.graded_at.isoformat() if grade and grade.graded_at else None
                }
            
            gradebook['students'].append(student_data)
        
        return jsonify(gradebook), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

