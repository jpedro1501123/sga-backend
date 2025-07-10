from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # admin, coordinator, teacher, student
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'role': self.role,
            'phone': self.phone,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Institution(db.Model):
    __tablename__ = 'institutions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    duration_semesters = db.Column(db.Integer, nullable=False)
    total_credits = db.Column(db.Integer)
    degree_type = db.Column(db.String(50), nullable=False)  # bachelor, master, doctorate, technical, other
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_number = db.Column(db.String(50), unique=True, nullable=False)
    enrollment_date = db.Column(db.Date)
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(10))
    document_type = db.Column(db.String(20))  # cpf, rg, passport, etc.
    document_number = db.Column(db.String(50))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    emergency_contact_name = db.Column(db.String(200))
    emergency_contact_phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='active')  # active, inactive, graduated, dropped, suspended
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        user = User.query.get(self.user_id)
        course = Course.query.get(self.course_id)
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user': user.to_dict() if user else None,
            'course_id': self.course_id,
            'course': course.to_dict() if course else None,
            'student_number': self.student_number,
            'enrollment_date': self.enrollment_date.isoformat() if self.enrollment_date else None,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'gender': self.gender,
            'document_type': self.document_type,
            'document_number': self.document_number,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_phone': self.emergency_contact_phone,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employee_number = db.Column(db.String(50), unique=True, nullable=False)
    department = db.Column(db.String(100))
    specialization = db.Column(db.String(200))
    academic_degree = db.Column(db.String(50), nullable=False)  # bachelor, master, doctorate, post_doctorate
    hire_date = db.Column(db.Date)
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(10))
    document_type = db.Column(db.String(20))
    document_number = db.Column(db.String(50))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    status = db.Column(db.String(20), default='active')  # active, inactive, on_leave
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        user = User.query.get(self.user_id)
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user': user.to_dict() if user else None,
            'employee_number': self.employee_number,
            'department': self.department,
            'specialization': self.specialization,
            'academic_degree': self.academic_degree,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'gender': self.gender,
            'document_type': self.document_type,
            'document_number': self.document_number,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Subject(db.Model):
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    credits = db.Column(db.Integer, nullable=False)
    workload_hours = db.Column(db.Integer, nullable=False)
    semester = db.Column(db.Integer)  # Which semester this subject is typically taken
    is_mandatory = db.Column(db.Boolean, default=True)
    prerequisites = db.Column(db.Text)  # JSON string of prerequisite subject IDs
    syllabus = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        course = Course.query.get(self.course_id)
        return {
            'id': self.id,
            'course_id': self.course_id,
            'course': course.to_dict() if course else None,
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
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ClassGroup(db.Model):
    __tablename__ = 'class_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    semester = db.Column(db.String(10), nullable=False)  # e.g., "2024.1", "2024.2"
    year = db.Column(db.Integer, nullable=False)
    class_code = db.Column(db.String(20), nullable=False)
    max_students = db.Column(db.Integer, default=50)
    schedule_info = db.Column(db.Text)  # JSON string with schedule information
    classroom = db.Column(db.String(50))
    status = db.Column(db.String(20), default='planned')  # planned, active, completed, cancelled
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        subject = Subject.query.get(self.subject_id)
        teacher = Teacher.query.get(self.teacher_id)
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'subject': subject.to_dict() if subject else None,
            'teacher_id': self.teacher_id,
            'teacher': teacher.to_dict() if teacher else None,
            'semester': self.semester,
            'year': self.year,
            'class_code': self.class_code,
            'max_students': self.max_students,
            'schedule_info': self.schedule_info,
            'classroom': self.classroom,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

def create_default_data():
    """Create default data for the system"""
    # Check if admin user already exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        # Create default admin user
        admin_user = User(
            username='admin',
            email='admin@sga.com',
            first_name='Administrador',
            last_name='Sistema',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        
        # Create default institution
        institution = Institution(
            name='Universidade Exemplo',
            code='UE',
            address='Rua Exemplo, 123',
            city='São Paulo',
            state='SP',
            zip_code='01234-567',
            phone='(11) 1234-5678',
            email='contato@universidadeexemplo.edu.br'
        )
        db.session.add(institution)
        
        db.session.commit()
        
        # Create default course
        course = Course(
            institution_id=institution.id,
            name='Ciência da Computação',
            code='CC',
            description='Curso de Bacharelado em Ciência da Computação',
            duration_semesters=8,
            total_credits=240,
            degree_type='bachelor'
        )
        db.session.add(course)
        db.session.commit()
        
        print("Dados padrão criados com sucesso!")
        print("Usuário admin criado - Login: admin, Senha: admin123")

