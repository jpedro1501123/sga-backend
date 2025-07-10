from datetime import datetime
from src.models import db

class Subject(db.Model):
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    credits = db.Column(db.Integer, nullable=False)
    workload_hours = db.Column(db.Integer, nullable=False)
    semester = db.Column(db.Integer)
    is_mandatory = db.Column(db.Boolean, default=True)
    prerequisites = db.Column(db.Text)  # JSON array with prerequisite subject IDs
    syllabus = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    class_groups = db.relationship('ClassGroup', backref='subject', lazy=True, cascade='all, delete-orphan')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('course_id', 'code', name='_course_subject_code_uc'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'credits': self.credits,
            'workload_hours': self.workload_hours,
            'semester': self.semester,
            'is_mandatory': self.is_mandatory,
            'prerequisites': self.prerequisites,
            'syllabus': self.syllabus,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'course': self.course.to_dict() if self.course else None
        }
    
    def __repr__(self):
        return f'<Subject {self.name}>'

