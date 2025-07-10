from datetime import datetime
from src.models import db

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    duration_semesters = db.Column(db.Integer, nullable=False)
    total_credits = db.Column(db.Integer)
    degree_type = db.Column(db.Enum('bachelor', 'master', 'doctorate', 'technical', 'other', name='degree_types'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subjects = db.relationship('Subject', backref='course', lazy=True, cascade='all, delete-orphan')
    students = db.relationship('Student', backref='course', lazy=True)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('institution_id', 'code', name='_institution_course_code_uc'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'institution_id': self.institution_id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'duration_semesters': self.duration_semesters,
            'total_credits': self.total_credits,
            'degree_type': self.degree_type,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'institution': self.institution.to_dict() if self.institution else None
        }
    
    def __repr__(self):
        return f'<Course {self.name}>'

