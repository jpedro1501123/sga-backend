from datetime import datetime
from src.models import db

class Grade(db.Model):
    __tablename__ = 'grades'
    
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'), nullable=False)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('evaluations.id'), nullable=False)
    score = db.Column(db.Numeric(5, 2))
    comments = db.Column(db.Text)
    graded_by = db.Column(db.Integer, db.ForeignKey('teachers.id'))
    graded_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    grader = db.relationship('Teacher', foreign_keys=[graded_by])
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('enrollment_id', 'evaluation_id', name='_enrollment_evaluation_uc'),)
    
    @property
    def percentage_score(self):
        """Calculate score as percentage of max_score"""
        if self.score is not None and self.evaluation and self.evaluation.max_score:
            return round((float(self.score) / float(self.evaluation.max_score)) * 100, 2)
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'enrollment_id': self.enrollment_id,
            'evaluation_id': self.evaluation_id,
            'score': float(self.score) if self.score else None,
            'percentage_score': self.percentage_score,
            'comments': self.comments,
            'graded_by': self.graded_by,
            'graded_at': self.graded_at.isoformat() if self.graded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'enrollment': self.enrollment.to_dict() if self.enrollment else None,
            'evaluation': self.evaluation.to_dict() if self.evaluation else None,
            'grader': self.grader.to_dict() if self.grader else None
        }
    
    def __repr__(self):
        return f'<Grade {self.enrollment_id} - {self.evaluation_id}: {self.score}>'

