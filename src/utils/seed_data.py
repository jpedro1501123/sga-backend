from src.models import db
from src.models.user import User
from src.models.institution import Institution
from src.models.course import Course
from src.models.subject import Subject
from src.models.evaluation_type import EvaluationType

def create_default_data():
    """Create default data for the system"""
    
    # Check if admin user already exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        # Create default admin user
        admin_user = User(
            username='admin',
            email='admin@sga.com',
            password='admin123',
            first_name='Administrador',
            last_name='Sistema',
            role='admin'
        )
        db.session.add(admin_user)
    
    # Check if institution already exists
    institution = Institution.query.first()
    if not institution:
        # Create default institution
        institution = Institution(
            name='Universidade Exemplo',
            code='UE',
            address='Rua Exemplo, 123',
            phone='(11) 1234-5678',
            email='contato@universidadeexemplo.edu.br',
            website='https://www.universidadeexemplo.edu.br'
        )
        db.session.add(institution)
        db.session.flush()  # To get the ID
    
    # Check if evaluation types exist
    eval_types = EvaluationType.query.count()
    if eval_types == 0:
        # Create default evaluation types
        evaluation_types = [
            EvaluationType(name='Prova', description='Avaliação escrita', default_weight=3.0),
            EvaluationType(name='Trabalho', description='Trabalho individual ou em grupo', default_weight=2.0),
            EvaluationType(name='Seminário', description='Apresentação oral', default_weight=1.5),
            EvaluationType(name='Projeto', description='Projeto prático', default_weight=2.5),
            EvaluationType(name='Participação', description='Participação em aula', default_weight=1.0),
            EvaluationType(name='Exercício', description='Lista de exercícios', default_weight=1.0)
        ]
        
        for eval_type in evaluation_types:
            db.session.add(eval_type)
    
    # Check if courses exist
    courses = Course.query.count()
    if courses == 0 and institution:
        # Create sample courses
        sample_courses = [
            Course(
                institution_id=institution.id,
                name='Ciência da Computação',
                code='CC',
                description='Bacharelado em Ciência da Computação',
                duration_semesters=8,
                total_credits=240,
                degree_type='bachelor'
            ),
            Course(
                institution_id=institution.id,
                name='Engenharia de Software',
                code='ES',
                description='Bacharelado em Engenharia de Software',
                duration_semesters=8,
                total_credits=240,
                degree_type='bachelor'
            ),
            Course(
                institution_id=institution.id,
                name='Sistemas de Informação',
                code='SI',
                description='Bacharelado em Sistemas de Informação',
                duration_semesters=8,
                total_credits=240,
                degree_type='bachelor'
            )
        ]
        
        for course in sample_courses:
            db.session.add(course)
        
        db.session.flush()  # To get the IDs
        
        # Create sample subjects for Computer Science course
        cc_course = Course.query.filter_by(code='CC').first()
        if cc_course:
            sample_subjects = [
                Subject(
                    course_id=cc_course.id,
                    name='Algoritmos e Estruturas de Dados I',
                    code='AED1',
                    description='Introdução a algoritmos e estruturas de dados básicas',
                    credits=4,
                    workload_hours=60,
                    semester=1,
                    is_mandatory=True
                ),
                Subject(
                    course_id=cc_course.id,
                    name='Programação Orientada a Objetos',
                    code='POO',
                    description='Conceitos e práticas de programação orientada a objetos',
                    credits=4,
                    workload_hours=60,
                    semester=2,
                    is_mandatory=True
                ),
                Subject(
                    course_id=cc_course.id,
                    name='Banco de Dados',
                    code='BD',
                    description='Modelagem e implementação de bancos de dados',
                    credits=4,
                    workload_hours=60,
                    semester=3,
                    is_mandatory=True
                ),
                Subject(
                    course_id=cc_course.id,
                    name='Engenharia de Software',
                    code='ENGS',
                    description='Metodologias e práticas de engenharia de software',
                    credits=4,
                    workload_hours=60,
                    semester=4,
                    is_mandatory=True
                ),
                Subject(
                    course_id=cc_course.id,
                    name='Inteligência Artificial',
                    code='IA',
                    description='Fundamentos de inteligência artificial',
                    credits=4,
                    workload_hours=60,
                    semester=6,
                    is_mandatory=False
                )
            ]
            
            for subject in sample_subjects:
                db.session.add(subject)
    
    try:
        db.session.commit()
        print("Default data created successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default data: {e}")

