from datetime import datetime, date
from src.models import db

class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    employee_number = db.Column(db.String(20), unique=True, nullable=False)
    department = db.Column(db.String(100))
    specialization = db.Column(db.Text)
    academic_degree = db.Column(db.Enum('bachelor', 'master', 'doctorate', 'post_doctorate', name='academic_degrees'), nullable=False)
    hire_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.Enum('active', 'inactive', 'on_leave', name='teacher_status'), default='active')
    birth_date = db.Column(db.Date)
    gender = db.Column(db.Enum('M', 'F', 'other', name='gender_types'))
    document_type = db.Column(db.String(20))
    document_number = db.Column(db.String(50))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    photo_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    class_groups = db.relationship('ClassGroup', backref='teacher', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'employee_number': self.employee_number,
            'department': self.department,
            'specialization': self.specialization,
            'academic_degree': self.academic_degree,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'status': self.status,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'gender': self.gender,
            'document_type': self.document_type,
            'document_number': self.document_number,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'photo_url': self.photo_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user': self.user.to_dict() if self.user else None
        }
    
    def __repr__(self):
        return f'<Teacher {self.employee_number}>'

