from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func, and_
from src.models import db
from src.models.student import Student
from src.models.teacher import Teacher
from src.models.course import Course
from src.models.subject import Subject
from src.models.class_group import ClassGroup
from src.models.enrollment import Enrollment
from src.models.grade import Grade
from src.models.evaluation import Evaluation
from src.models.attendance import Attendance
from src.utils.decorators import teacher_or_above_required, get_current_user

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        current_user = get_current_user()
        
        # Base statistics
        stats = {
            'total_students': Student.query.filter_by(status='active').count(),
            'total_teachers': Teacher.query.filter_by(status='active').count(),
            'total_courses': Course.query.filter_by(is_active=True).count(),
            'total_subjects': Subject.query.filter_by(is_active=True).count(),
            'active_classes': ClassGroup.query.filter_by(status='active').count(),
            'pending_grades': 0,
            'recent_enrollments': 0
        }
        
        # Role-specific filtering
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if teacher:
                # Filter stats for this teacher's classes
                teacher_classes = ClassGroup.query.filter_by(teacher_id=teacher.id, status='active').all()
                stats['active_classes'] = len(teacher_classes)
                
                # Count pending grades for teacher's classes
                pending_grades = 0
                for class_group in teacher_classes:
                    evaluations = Evaluation.query.filter_by(class_group_id=class_group.id).all()
                    enrollments = Enrollment.query.filter_by(class_group_id=class_group.id, status='enrolled').all()
                    
                    for evaluation in evaluations:
                        for enrollment in enrollments:
                            grade = Grade.query.filter_by(
                                enrollment_id=enrollment.id,
                                evaluation_id=evaluation.id
                            ).first()
                            if not grade:
                                pending_grades += 1
                
                stats['pending_grades'] = pending_grades
        
        elif current_user.role == 'student':
            student = Student.query.filter_by(user_id=current_user.id).first()
            if student:
                # Filter stats for this student
                student_enrollments = Enrollment.query.filter_by(student_id=student.id, status='enrolled').all()
                stats['active_classes'] = len(student_enrollments)
                stats['total_students'] = 1  # Just this student
        
        else:
            # Admin/Coordinator - calculate pending grades across all classes
            total_pending = 0
            all_evaluations = Evaluation.query.all()
            
            for evaluation in all_evaluations:
                enrollments = Enrollment.query.filter_by(
                    class_group_id=evaluation.class_group_id, 
                    status='enrolled'
                ).all()
                
                for enrollment in enrollments:
                    grade = Grade.query.filter_by(
                        enrollment_id=enrollment.id,
                        evaluation_id=evaluation.id
                    ).first()
                    if not grade:
                        total_pending += 1
            
            stats['pending_grades'] = total_pending
        
        # Recent enrollments (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        stats['recent_enrollments'] = Enrollment.query.filter(
            Enrollment.enrollment_date >= thirty_days_ago.date()
        ).count()
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/academic-performance', methods=['GET'])
@jwt_required()
@teacher_or_above_required
def get_academic_performance():
    """Get academic performance report"""
    try:
        current_user = get_current_user()
        course_id = request.args.get('course_id', type=int)
        semester = request.args.get('semester')
        year = request.args.get('year', type=int)
        
        # Base query for enrollments
        query = db.session.query(
            Enrollment.final_grade,
            Enrollment.final_status,
            Student.id.label('student_id'),
            ClassGroup.semester,
            ClassGroup.year,
            Subject.name.label('subject_name'),
            Course.name.label('course_name')
        ).join(Student).join(ClassGroup).join(Subject).join(Course)
        
        # Apply role-based filtering
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if teacher:
                query = query.filter(ClassGroup.teacher_id == teacher.id)
        
        # Apply filters
        if course_id:
            query = query.filter(Course.id == course_id)
        
        if semester:
            query = query.filter(ClassGroup.semester == semester)
        
        if year:
            query = query.filter(ClassGroup.year == year)
        
        # Only completed enrollments with grades
        query = query.filter(
            Enrollment.final_grade.isnot(None),
            Enrollment.final_status.in_(['approved', 'failed'])
        )
        
        results = query.all()
        
        # Calculate statistics
        if results:
            grades = [float(r.final_grade) for r in results if r.final_grade]
            
            performance_stats = {
                'total_enrollments': len(results),
                'average_grade': round(sum(grades) / len(grades), 2) if grades else 0,
                'highest_grade': max(grades) if grades else 0,
                'lowest_grade': min(grades) if grades else 0,
                'approval_rate': 0,
                'grade_distribution': {
                    '9.0-10.0': 0,
                    '8.0-8.9': 0,
                    '7.0-7.9': 0,
                    '6.0-6.9': 0,
                    '5.0-5.9': 0,
                    '0.0-4.9': 0
                },
                'status_distribution': {
                    'approved': 0,
                    'failed': 0
                }
            }
            
            # Calculate approval rate
            approved_count = len([r for r in results if r.final_status == 'approved'])
            performance_stats['approval_rate'] = round((approved_count / len(results)) * 100, 2)
            
            # Calculate grade distribution
            for grade in grades:
                if grade >= 9.0:
                    performance_stats['grade_distribution']['9.0-10.0'] += 1
                elif grade >= 8.0:
                    performance_stats['grade_distribution']['8.0-8.9'] += 1
                elif grade >= 7.0:
                    performance_stats['grade_distribution']['7.0-7.9'] += 1
                elif grade >= 6.0:
                    performance_stats['grade_distribution']['6.0-6.9'] += 1
                elif grade >= 5.0:
                    performance_stats['grade_distribution']['5.0-5.9'] += 1
                else:
                    performance_stats['grade_distribution']['0.0-4.9'] += 1
            
            # Calculate status distribution
            for result in results:
                performance_stats['status_distribution'][result.final_status] += 1
        
        else:
            performance_stats = {
                'total_enrollments': 0,
                'average_grade': 0,
                'highest_grade': 0,
                'lowest_grade': 0,
                'approval_rate': 0,
                'grade_distribution': {},
                'status_distribution': {}
            }
        
        return jsonify(performance_stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/attendance', methods=['GET'])
@jwt_required()
@teacher_or_above_required
def get_attendance_report():
    """Get attendance report"""
    try:
        current_user = get_current_user()
        class_id = request.args.get('class_id', type=int)
        student_id = request.args.get('student_id', type=int)
        
        # Base query for attendance
        query = db.session.query(
            Attendance.status,
            Enrollment.id.label('enrollment_id'),
            Student.id.label('student_id'),
            ClassGroup.id.label('class_id'),
            Subject.name.label('subject_name')
        ).join(Enrollment).join(Student).join(ClassGroup).join(Subject)
        
        # Apply role-based filtering
        if current_user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=current_user.id).first()
            if teacher:
                query = query.filter(ClassGroup.teacher_id == teacher.id)
        elif current_user.role == 'student':
            student = Student.query.filter_by(user_id=current_user.id).first()
            if student:
                query = query.filter(Student.id == student.id)
        
        # Apply filters
        if class_id:
            query = query.filter(ClassGroup.id == class_id)
        
        if student_id and current_user.role in ['admin', 'coordinator', 'teacher']:
            query = query.filter(Student.id == student_id)
        
        results = query.all()
        
        # Calculate attendance statistics
        if results:
            total_records = len(results)
            present_count = len([r for r in results if r.status in ['present', 'late']])
            absent_count = len([r for r in results if r.status == 'absent'])
            justified_count = len([r for r in results if r.status == 'justified'])
            
            attendance_stats = {
                'total_records': total_records,
                'present_count': present_count,
                'absent_count': absent_count,
                'justified_count': justified_count,
                'attendance_rate': round((present_count / total_records) * 100, 2) if total_records > 0 else 0,
                'absence_rate': round((absent_count / total_records) * 100, 2) if total_records > 0 else 0,
                'status_distribution': {
                    'present': len([r for r in results if r.status == 'present']),
                    'absent': absent_count,
                    'late': len([r for r in results if r.status == 'late']),
                    'justified': justified_count
                }
            }
        else:
            attendance_stats = {
                'total_records': 0,
                'present_count': 0,
                'absent_count': 0,
                'justified_count': 0,
                'attendance_rate': 0,
                'absence_rate': 0,
                'status_distribution': {}
            }
        
        return jsonify(attendance_stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/class-summary/<int:class_id>', methods=['GET'])
@jwt_required()
@teacher_or_above_required
def get_class_summary(class_id):
    """Get detailed summary for a specific class"""
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
        
        # Get enrollments
        enrollments = Enrollment.query.filter_by(class_group_id=class_id).all()
        
        # Get evaluations
        evaluations = Evaluation.query.filter_by(class_group_id=class_id).all()
        
        # Calculate class statistics
        enrolled_students = [e for e in enrollments if e.status == 'enrolled']
        completed_students = [e for e in enrollments if e.final_status in ['approved', 'failed']]
        
        class_summary = {
            'class': class_group.to_dict(),
            'enrollment_stats': {
                'total_enrolled': len(enrolled_students),
                'max_capacity': class_group.max_students,
                'capacity_percentage': round((len(enrolled_students) / class_group.max_students) * 100, 2) if class_group.max_students > 0 else 0,
                'completed_students': len(completed_students)
            },
            'evaluation_stats': {
                'total_evaluations': len(evaluations),
                'published_evaluations': len([e for e in evaluations if e.is_published]),
                'average_score': 0,
                'evaluations_by_type': {}
            },
            'grade_distribution': {
                'approved': 0,
                'failed': 0,
                'in_progress': 0
            },
            'attendance_summary': {
                'average_attendance_rate': 0
            }
        }
        
        # Calculate evaluation statistics
        if evaluations:
            all_grades = []
            for evaluation in evaluations:
                grades = Grade.query.filter_by(evaluation_id=evaluation.id).all()
                valid_scores = [float(g.score) for g in grades if g.score is not None]
                all_grades.extend(valid_scores)
                
                # Count by evaluation type
                eval_type = evaluation.evaluation_type.name if evaluation.evaluation_type else 'Unknown'
                if eval_type not in class_summary['evaluation_stats']['evaluations_by_type']:
                    class_summary['evaluation_stats']['evaluations_by_type'][eval_type] = 0
                class_summary['evaluation_stats']['evaluations_by_type'][eval_type] += 1
            
            if all_grades:
                class_summary['evaluation_stats']['average_score'] = round(sum(all_grades) / len(all_grades), 2)
        
        # Calculate grade distribution
        for enrollment in enrollments:
            if enrollment.final_status:
                class_summary['grade_distribution'][enrollment.final_status] += 1
            else:
                class_summary['grade_distribution']['in_progress'] += 1
        
        # Calculate attendance summary
        if enrolled_students:
            total_attendance_rate = sum(e.attendance_percentage for e in enrolled_students)
            class_summary['attendance_summary']['average_attendance_rate'] = round(
                total_attendance_rate / len(enrolled_students), 2
            )
        
        return jsonify(class_summary), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/student-transcript/<int:student_id>', methods=['GET'])
@jwt_required()
def get_student_transcript(student_id):
    """Get academic transcript for a student"""
    try:
        current_user = get_current_user()
        student = Student.query.get(student_id)
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Check permissions
        if current_user.role == 'student' and student.user_id != current_user.id:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Get all enrollments for the student
        enrollments = Enrollment.query.filter_by(student_id=student_id).all()
        
        # Organize by semester/year
        transcript_data = {
            'student': student.to_dict(),
            'course': student.course.to_dict() if student.course else None,
            'semesters': {},
            'summary': {
                'total_credits_attempted': 0,
                'total_credits_earned': 0,
                'gpa': 0,
                'total_subjects': len(enrollments),
                'approved_subjects': 0,
                'failed_subjects': 0
            }
        }
        
        total_grade_points = 0
        total_credits_for_gpa = 0
        
        for enrollment in enrollments:
            class_group = enrollment.class_group
            subject = class_group.subject
            semester_key = f"{class_group.year}.{class_group.semester}"
            
            if semester_key not in transcript_data['semesters']:
                transcript_data['semesters'][semester_key] = []
            
            # Calculate grade points for GPA
            if enrollment.final_grade and subject.credits:
                total_grade_points += float(enrollment.final_grade) * subject.credits
                total_credits_for_gpa += subject.credits
            
            # Count credits
            transcript_data['summary']['total_credits_attempted'] += subject.credits
            if enrollment.final_status == 'approved':
                transcript_data['summary']['total_credits_earned'] += subject.credits
                transcript_data['summary']['approved_subjects'] += 1
            elif enrollment.final_status == 'failed':
                transcript_data['summary']['failed_subjects'] += 1
            
            # Add to semester data
            transcript_data['semesters'][semester_key].append({
                'subject': subject.to_dict(),
                'class_code': class_group.class_code,
                'teacher': class_group.teacher.user.full_name if class_group.teacher else 'N/A',
                'final_grade': float(enrollment.final_grade) if enrollment.final_grade else None,
                'final_status': enrollment.final_status,
                'credits': subject.credits
            })
        
        # Calculate GPA
        if total_credits_for_gpa > 0:
            transcript_data['summary']['gpa'] = round(total_grade_points / total_credits_for_gpa, 2)
        
        return jsonify(transcript_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/teacher-workload/<int:teacher_id>', methods=['GET'])
@jwt_required()
@teacher_or_above_required
def get_teacher_workload(teacher_id):
    """Get workload report for a teacher"""
    try:
        current_user = get_current_user()
        teacher = Teacher.query.get(teacher_id)
        
        if not teacher:
            return jsonify({'error': 'Teacher not found'}), 404
        
        # Check permissions
        if current_user.role == 'teacher' and teacher.user_id != current_user.id:
            return jsonify({'error': 'Permission denied'}), 403
        
        semester = request.args.get('semester')
        year = request.args.get('year', type=int)
        
        # Get teacher's classes
        query = ClassGroup.query.filter_by(teacher_id=teacher_id)
        
        if semester:
            query = query.filter(ClassGroup.semester == semester)
        if year:
            query = query.filter(ClassGroup.year == year)
        
        classes = query.all()
        
        workload_data = {
            'teacher': teacher.to_dict(),
            'period': {
                'semester': semester,
                'year': year
            },
            'summary': {
                'total_classes': len(classes),
                'total_students': 0,
                'total_credits': 0,
                'total_evaluations': 0,
                'pending_grades': 0
            },
            'classes': []
        }
        
        for class_group in classes:
            enrolled_students = len([e for e in class_group.enrollments if e.status == 'enrolled'])
            evaluations = Evaluation.query.filter_by(class_group_id=class_group.id).all()
            
            # Count pending grades
            pending_grades = 0
            for evaluation in evaluations:
                for enrollment in class_group.enrollments:
                    if enrollment.status == 'enrolled':
                        grade = Grade.query.filter_by(
                            enrollment_id=enrollment.id,
                            evaluation_id=evaluation.id
                        ).first()
                        if not grade:
                            pending_grades += 1
            
            class_data = {
                'class': class_group.to_dict(),
                'enrolled_students': enrolled_students,
                'total_evaluations': len(evaluations),
                'pending_grades': pending_grades,
                'subject_credits': class_group.subject.credits
            }
            
            workload_data['classes'].append(class_data)
            
            # Update summary
            workload_data['summary']['total_students'] += enrolled_students
            workload_data['summary']['total_credits'] += class_group.subject.credits
            workload_data['summary']['total_evaluations'] += len(evaluations)
            workload_data['summary']['pending_grades'] += pending_grades
        
        return jsonify(workload_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

