from datetime import datetime
from src.models import db

class EvaluationType(db.Model):
    __tablename__ = 'evaluation_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    default_weight = db.Column(db.Numeric(3, 2), default=1.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    evaluations = db.relationship('Evaluation', backref='evaluation_type', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'default_weight': float(self.default_weight) if self.default_weight else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<EvaluationType {self.name}>'

