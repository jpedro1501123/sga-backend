from datetime import datetime, date
from src.models import db

class ClassGroup(db.Model):
    __tablename__ = 'class_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    semester = db.Column(db.String(10), nullable=False)  # Ex: "2024.1", "2024.2"
    year = db.Column(db.Integer, nullable=False)
    class_code = db.Column(db.String(20), nullable=False)
    max_students = db.Column(db.Integer, default=50)
    schedule_info = db.Column(db.Text)  # JSON with class schedules
    classroom = db.Column(db.String(50))
    status = db.Column(db.Enum('planned', 'active', 'completed', 'cancelled', name='class_status'), default='planned')
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='class_group', lazy=True, cascade='all, delete-orphan')
    evaluations = db.relationship('Evaluation', backref='class_group', lazy=True, cascade='all, delete-orphan')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('subject_id', 'class_code', 'semester', 'year', name='_subject_class_semester_uc'),)
    
    @property
    def enrolled_students_count(self):
        return len([e for e in self.enrollments if e.status == 'enrolled'])
    
    def to_dict(self):
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'teacher_id': self.teacher_id,
            'semester': self.semester,
            'year': self.year,
            'class_code': self.class_code,
            'max_students': self.max_students,
            'schedule_info': self.schedule_info,
            'classroom': self.classroom,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'enrolled_students_count': self.enrolled_students_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'subject': self.subject.to_dict() if self.subject else None,
            'teacher': self.teacher.to_dict() if self.teacher else None
        }
    
    def __repr__(self):
        return f'<ClassGroup {self.class_code} - {self.semester}/{self.year}>'

