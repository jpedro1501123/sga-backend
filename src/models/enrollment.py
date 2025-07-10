from datetime import datetime, date
from src.models import db

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    class_group_id = db.Column(db.Integer, db.ForeignKey('class_groups.id'), nullable=False)
    enrollment_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.Enum('enrolled', 'dropped', 'completed', 'failed', name='enrollment_status'), default='enrolled')
    final_grade = db.Column(db.Numeric(4, 2))
    final_status = db.Column(db.Enum('approved', 'failed', 'incomplete', 'in_progress', name='final_status'), default='in_progress')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    grades = db.relationship('Grade', backref='enrollment', lazy=True, cascade='all, delete-orphan')
    attendance_records = db.relationship('Attendance', backref='enrollment', lazy=True, cascade='all, delete-orphan')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('student_id', 'class_group_id', name='_student_class_uc'),)
    
    @property
    def attendance_percentage(self):
        """Calculate attendance percentage"""
        if not self.attendance_records:
            return 0
        
        total_classes = len(self.attendance_records)
        present_classes = len([a for a in self.attendance_records if a.status in ['present', 'late']])
        
        return round((present_classes / total_classes) * 100, 2) if total_classes > 0 else 0
    
    def calculate_final_grade(self):
        """Calculate final grade based on evaluations and their weights"""
        if not self.grades:
            return None
        
        total_weighted_score = 0
        total_weight = 0
        
        for grade in self.grades:
            if grade.score is not None and grade.evaluation:
                total_weighted_score += float(grade.score) * float(grade.evaluation.weight)
                total_weight += float(grade.evaluation.weight)
        
        if total_weight > 0:
            return round(total_weighted_score / total_weight, 2)
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'class_group_id': self.class_group_id,
            'enrollment_date': self.enrollment_date.isoformat() if self.enrollment_date else None,
            'status': self.status,
            'final_grade': float(self.final_grade) if self.final_grade else None,
            'final_status': self.final_status,
            'attendance_percentage': self.attendance_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'student': self.student.to_dict() if self.student else None,
            'class_group': self.class_group.to_dict() if self.class_group else None
        }
    
    def __repr__(self):
        return f'<Enrollment {self.student_id} - {self.class_group_id}>'

