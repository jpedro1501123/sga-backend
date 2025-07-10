from datetime import datetime, date
from src.models import db

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'), nullable=False)
    class_date = db.Column(db.Date, nullable=False)
    class_period = db.Column(db.Integer, nullable=False)  # 1, 2, 3, etc. (classes of the day)
    status = db.Column(db.Enum('present', 'absent', 'late', 'justified', name='attendance_status'), nullable=False)
    comments = db.Column(db.Text)
    recorded_by = db.Column(db.Integer, db.ForeignKey('teachers.id'))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    recorder = db.relationship('Teacher', foreign_keys=[recorded_by])
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('enrollment_id', 'class_date', 'class_period', name='_enrollment_date_period_uc'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'enrollment_id': self.enrollment_id,
            'class_date': self.class_date.isoformat() if self.class_date else None,
            'class_period': self.class_period,
            'status': self.status,
            'comments': self.comments,
            'recorded_by': self.recorded_by,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'enrollment': self.enrollment.to_dict() if self.enrollment else None,
            'recorder': self.recorder.to_dict() if self.recorder else None
        }
    
    def __repr__(self):
        return f'<Attendance {self.enrollment_id} - {self.class_date}: {self.status}>'

