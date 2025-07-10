from datetime import datetime, date
from src.models import db

class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    
    id = db.Column(db.Integer, primary_key=True)
    class_group_id = db.Column(db.Integer, db.ForeignKey('class_groups.id'), nullable=False)
    evaluation_type_id = db.Column(db.Integer, db.ForeignKey('evaluation_types.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    weight = db.Column(db.Numeric(3, 2), nullable=False, default=1.0)
    max_score = db.Column(db.Numeric(5, 2), nullable=False, default=10.0)
    evaluation_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    grades = db.relationship('Grade', backref='evaluation', lazy=True, cascade='all, delete-orphan')
    
    @property
    def grades_count(self):
        return len(self.grades)
    
    @property
    def average_score(self):
        if not self.grades:
            return None
        
        valid_scores = [float(g.score) for g in self.grades if g.score is not None]
        return round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None
    
    def to_dict(self):
        return {
            'id': self.id,
            'class_group_id': self.class_group_id,
            'evaluation_type_id': self.evaluation_type_id,
            'name': self.name,
            'description': self.description,
            'weight': float(self.weight) if self.weight else None,
            'max_score': float(self.max_score) if self.max_score else None,
            'evaluation_date': self.evaluation_date.isoformat() if self.evaluation_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'is_published': self.is_published,
            'grades_count': self.grades_count,
            'average_score': self.average_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'class_group': self.class_group.to_dict() if self.class_group else None,
            'evaluation_type': self.evaluation_type.to_dict() if self.evaluation_type else None
        }
    
    def __repr__(self):
        return f'<Evaluation {self.name}>'

