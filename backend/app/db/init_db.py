import uuid
import json
import random
import logging
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.user import User, Coordinator
from app.models.student import Student
from app.models.company import Company, CompanyRequirements, CompanyAvailability, Shortlist
from app.models.resource import Room, Panel
from app.models.schedule import Schedule
from app.models.placement_session import PlacementSession

logger = logging.getLogger("placement_control_tower.init_db")

DEFAULT_SESSION_ID = "default-placement-session-2026"

BRANCHES = ["CSE", "ISE", "ECE", "EEE", "MECH", "CIVIL", "AI_ML"]
SKILLS_POOL = [
    "Python", "Java", "C++", "FastAPI", "React", "TypeScript", "SQL", "Docker",
    "Kubernetes", "AWS", "Machine Learning", "Data Structures", "System Design",
    "Distributed Systems", "PostgreSQL", "Cybersecurity", "Embedded C"
]

COMPANY_DEFS = [
    {"code": "TECHNOVA", "name": "TechNova Systems", "industry": "Enterprise Software", "tier": 1, "cgpa": 7.5, "branches": ["CSE", "ISE", "ECE", "AI_ML"], "panels": 4},
    {"code": "DATACORE", "name": "DataCore Analytics", "industry": "Big Data & AI", "tier": 1, "cgpa": 8.0, "branches": ["CSE", "ISE", "AI_ML"], "panels": 3},
    {"code": "FINEDGE", "name": "FinEdge Quant Capital", "industry": "FinTech", "tier": 1, "cgpa": 8.5, "branches": ["CSE", "ISE", "ECE", "EEE"], "panels": 3},
    {"code": "CYBERNET", "name": "CyberNet Security", "industry": "Cybersecurity", "tier": 1, "cgpa": 7.8, "branches": ["CSE", "ISE"], "panels": 2},
    {"code": "NEXUSAI", "name": "NexusAI Labs", "industry": "Artificial Intelligence", "tier": 1, "cgpa": 8.2, "branches": ["CSE", "AI_ML", "ISE"], "panels": 3},
    {"code": "CLOUDSCALE", "name": "CloudScale Networks", "industry": "Cloud Infrastructure", "tier": 1, "cgpa": 7.5, "branches": ["CSE", "ISE", "ECE"], "panels": 3},
    {"code": "AUTODRIVE", "name": "AutoDrive Robotics", "industry": "Automotive / AI", "tier": 2, "cgpa": 7.2, "branches": ["CSE", "ECE", "EEE", "MECH"], "panels": 2},
    {"code": "MEDITECH", "name": "MediTech Health AI", "industry": "HealthTech", "tier": 2, "cgpa": 7.0, "branches": ["CSE", "ISE", "ECE", "AI_ML"], "panels": 2},
    {"code": "LOGIXFLOW", "name": "LogixFlow Supply Chain", "industry": "Logistics Software", "tier": 2, "cgpa": 6.8, "branches": ["CSE", "ISE", "MECH"], "panels": 2},
    {"code": "QUANTUMLEAP", "name": "QuantumLeap Semiconductors", "industry": "Semiconductors", "tier": 2, "cgpa": 7.5, "branches": ["ECE", "EEE", "CSE"], "panels": 3},
    {"code": "ENERGYGRID", "name": "EnergyGrid Renewables", "industry": "Clean Energy", "tier": 2, "cgpa": 6.5, "branches": ["EEE", "MECH", "CIVIL"], "panels": 2},
    {"code": "URBANSYNC", "name": "UrbanSync Smart Cities", "industry": "IoT / Infrastructure", "tier": 2, "cgpa": 6.8, "branches": ["CIVIL", "ECE", "CSE"], "panels": 2},
    {"code": "PAYMATRIX", "name": "PayMatrix Global", "industry": "Payments", "tier": 2, "cgpa": 7.0, "branches": ["CSE", "ISE"], "panels": 2},
    {"code": "AEROSPHERE", "name": "AeroSphere Dynamics", "industry": "Aerospace", "tier": 3, "cgpa": 7.0, "branches": ["MECH", "ECE", "EEE"], "panels": 2},
    {"code": "STREAMLINE", "name": "StreamLine Media", "industry": "MediaTech", "tier": 3, "cgpa": 6.5, "branches": ["CSE", "ISE"], "panels": 2},
    {"code": "INFRATRUST", "name": "InfraTrust Constructions", "industry": "Civil Engineering", "tier": 3, "cgpa": 6.0, "branches": ["CIVIL"], "panels": 2},
    {"code": "ROBOPRO", "name": "RoboPro Automation", "industry": "Industrial Robotics", "tier": 3, "cgpa": 6.8, "branches": ["MECH", "EEE", "ECE"], "panels": 2},
    {"code": "BIOWORLD", "name": "BioWorld Therapeutics", "industry": "Bioinformatics", "tier": 3, "cgpa": 7.0, "branches": ["CSE", "AI_ML"], "panels": 2},
    {"code": "RETAILHUB", "name": "RetailHub Solutions", "industry": "E-Commerce", "tier": 3, "cgpa": 6.2, "branches": ["CSE", "ISE", "ECE"], "panels": 2},
    {"code": "TELELINK", "name": "TeleLink Networks", "industry": "Telecommunications", "tier": 3, "cgpa": 6.5, "branches": ["ECE", "EEE"], "panels": 2}
]

def init_db(engine_instance=None):
    """
    Production-safe database initializer:
    1. Creates all tables if missing.
    2. Ensures active PlacementSession exists.
    3. Ensures essential Coordinator, Company, and Student demo accounts exist with secure password hashes.
    4. If the database is completely empty (0 companies and 0 students), populates initial operational data.
    5. NEVER drops tables or overwrites existing user-uploaded datasets.
    """
    eng = engine_instance or engine
    Base.metadata.create_all(bind=eng)

    db: Session = SessionLocal()
    try:
        # 1. Ensure Active PlacementSession
        active_session = db.query(PlacementSession).filter(PlacementSession.status == "ACTIVE").first()
        if not active_session:
            active_session = PlacementSession(
                id=DEFAULT_SESSION_ID,
                name="University Placement Week 2026",
                college_name="University Placement Office",
                academic_year="2025-2026",
                status="ACTIVE"
            )
            db.add(active_session)
            db.commit()
            db.refresh(active_session)
        session_id = active_session.id

        admin_pwd_hash = get_password_hash("admin123")
        company_pwd_hash = get_password_hash("company123")
        student_pwd_hash = get_password_hash("student123")

        # 2. Ensure Coordinator Account
        coord_user = db.query(User).filter(User.email == "coordinator@university.edu").first()
        if not coord_user:
            coord_user = User(
                id=str(uuid.uuid4()),
                email="coordinator@university.edu",
                hashed_password=admin_pwd_hash,
                role="COORDINATOR",
                is_active=True
            )
            db.add(coord_user)
            db.flush()

        coord_profile = db.query(Coordinator).filter(Coordinator.user_id == coord_user.id).first()
        if not coord_profile:
            coord_profile = Coordinator(
                id=str(uuid.uuid4()),
                user_id=coord_user.id,
                name="Prof. Sarah Jenkins",
                department="Central Placement & Career Cell",
                phone="+1-555-0199"
            )
            db.add(coord_profile)

        # 3. Ensure Demo Company User
        technova_user = db.query(User).filter(User.email == "technova@placement.edu").first()
        if not technova_user:
            technova_user = User(
                id=str(uuid.uuid4()),
                email="technova@placement.edu",
                hashed_password=company_pwd_hash,
                role="COMPANY",
                is_active=True
            )
            db.add(technova_user)
            db.flush()

        # 4. Ensure Demo Student User
        student_demo_user = db.query(User).filter(User.email == "s0421@student.edu").first()
        if not student_demo_user:
            student_demo_user = User(
                id=str(uuid.uuid4()),
                email="s0421@student.edu",
                hashed_password=student_pwd_hash,
                role="STUDENT",
                is_active=True
            )
            db.add(student_demo_user)
            db.flush()

        db.commit()

        # 5. Populate initial dataset ONLY IF database is empty
        company_count = db.query(Company).count()
        student_count = db.query(Student).count()

        if company_count == 0 and student_count == 0:
            logger.info("Initializing baseline placement data for fresh deployment...")
            random.seed(42)

            # Create Schedule
            default_schedule = db.query(Schedule).filter(Schedule.placement_session_id == session_id).first()
            if not default_schedule:
                default_schedule = Schedule(
                    id=str(uuid.uuid4()),
                    placement_session_id=session_id,
                    name="University Placement Week 2026",
                    academic_year="2025-2026",
                    status="ACTIVE"
                )
                db.add(default_schedule)

            # Create 20 Campus Interview Rooms
            for i in range(1, 21):
                room = Room(
                    id=str(uuid.uuid4()),
                    placement_session_id=session_id,
                    room_code=f"R{i:02d}",
                    building="Placement Complex Block A" if i <= 10 else "Placement Complex Block B",
                    floor=1 if i <= 10 else 2,
                    capacity=6,
                    has_video_conf=True,
                    is_active=True
                )
                db.add(room)

            # Create Companies & Panels
            created_companies = []
            for c_def in COMPANY_DEFS:
                c_email = f"{c_def['code'].lower()}@placement.edu"
                c_user = db.query(User).filter(User.email == c_email).first()
                if not c_user:
                    c_user = User(
                        id=str(uuid.uuid4()),
                        email=c_email,
                        hashed_password=company_pwd_hash,
                        role="COMPANY",
                        is_active=True
                    )
                    db.add(c_user)
                    db.flush()

                comp = Company(
                    id=str(uuid.uuid4()),
                    placement_session_id=session_id,
                    user_id=c_user.id,
                    company_code=c_def["code"],
                    name=c_def["name"],
                    industry=c_def["industry"],
                    priority_tier=c_def["tier"],
                    interview_duration_mins=45,
                    max_panels=c_def["panels"],
                    is_active=True
                )
                db.add(comp)
                db.flush()
                created_companies.append((comp, c_def))

                req = CompanyRequirements(
                    id=str(uuid.uuid4()),
                    placement_session_id=session_id,
                    company_id=comp.id,
                    min_cgpa=c_def["cgpa"],
                    eligible_branches=json.dumps(c_def["branches"]),
                    rounds_count=1
                )
                db.add(req)

                avail = CompanyAvailability(
                    id=str(uuid.uuid4()),
                    placement_session_id=session_id,
                    company_id=comp.id,
                    day_number=1,
                    start_time_slot=0,
                    end_time_slot=12,
                    is_available=True
                )
                db.add(avail)

                for p_idx in range(1, c_def["panels"] + 1):
                    panel = Panel(
                        id=str(uuid.uuid4()),
                        placement_session_id=session_id,
                        company_id=comp.id,
                        panel_code=f"P{p_idx}",
                        interviewer_names=f"{comp.name} Tech Panel {p_idx}",
                        is_active=True
                    )
                    db.add(panel)

            # Create Demo Student S0421
            demo_student = db.query(Student).filter(Student.student_code == "S0421").first()
            if not demo_student:
                demo_student = Student(
                    id=str(uuid.uuid4()),
                    placement_session_id=session_id,
                    user_id=student_demo_user.id,
                    student_code="S0421",
                    name="Alex Mercer",
                    email="s0421@student.edu",
                    branch="ISE",
                    cgpa=8.62,
                    graduation_year=2026,
                    skills=json.dumps(["Distributed Systems", "Python", "FastAPI", "React"]),
                    is_active=True,
                    is_withdrawn=False
                )
                db.add(demo_student)

            # Create remaining students
            created_students = [demo_student]
            first_names = ["Aarav", "Ananya", "Rohan", "Priya", "Rahul", "Neha", "Vikram", "Sneha", "Aditya", "Pooja", "Arjun", "Kavya", "Siddharth", "Divya", "Karan", "Tanvi", "Varun", "Meera", "Gaurav", "Isha"]
            last_names = ["Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Rao", "Gupta", "Singh", "Das", "Menon", "Joshi", "Kulkarni", "Deshmukh", "Mehta", "Bhat"]

            for i in range(1, 100):
                code = f"S{i:04d}"
                if code == "S0421":
                    continue
                s_email = f"{code.lower()}@student.edu"
                s_user = db.query(User).filter(User.email == s_email).first()
                if not s_user:
                    s_user = User(
                        id=str(uuid.uuid4()),
                        email=s_email,
                        hashed_password=student_pwd_hash,
                        role="STUDENT",
                        is_active=True
                    )
                    db.add(s_user)
                    db.flush()

                fname = random.choice(first_names)
                lname = random.choice(last_names)
                st = Student(
                    id=str(uuid.uuid4()),
                    placement_session_id=session_id,
                    user_id=s_user.id,
                    student_code=code,
                    name=f"{fname} {lname}",
                    email=s_email,
                    branch=random.choice(BRANCHES),
                    cgpa=round(random.uniform(6.5, 9.8), 2),
                    graduation_year=2026,
                    skills=json.dumps(random.sample(SKILLS_POOL, k=random.randint(3, 5))),
                    is_active=True,
                    is_withdrawn=False
                )
                db.add(st)
                created_students.append(st)

            db.flush()

            # Shortlists
            top_comps = [c[0] for c in created_companies[:4]]
            for comp in top_comps:
                sh = Shortlist(
                    id=str(uuid.uuid4()),
                    placement_session_id=session_id,
                    company_id=comp.id,
                    student_id=demo_student.id,
                    preference_rank=1,
                    status="SHORTLISTED"
                )
                db.add(sh)

            for comp, c_def in created_companies:
                min_cgpa = c_def["cgpa"]
                branches = c_def["branches"]
                eligible = [s for s in created_students if s.cgpa >= min_cgpa and (not branches or s.branch in branches)]
                target_size = min(len(eligible), random.randint(10, 18))
                selected_students = random.sample(eligible, k=target_size)

                for s in selected_students:
                    if s.id == demo_student.id and comp.id in [c.id for c in top_comps]:
                        continue
                    sh = Shortlist(
                        id=str(uuid.uuid4()),
                        placement_session_id=session_id,
                        company_id=comp.id,
                        student_id=s.id,
                        preference_rank=random.randint(1, 3),
                        status="SHORTLISTED"
                    )
                    db.add(sh)

            db.commit()

        logger.info("Database initialization verified successfully.")

    except Exception as e:
        db.rollback()
        logger.error(f"Database initialization error: {e}", exc_info=True)
    finally:
        db.close()
