import sys
import os
import random
import uuid
import json

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_root = os.path.join(project_root, "backend")
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.db.session import engine, SessionLocal, Base
from app.core.security import get_password_hash
from app.models.user import User, Coordinator
from app.models.student import Student
from app.models.company import Company, CompanyRequirements, CompanyAvailability, Shortlist
from app.models.resource import Room, Panel, InterviewSlot
from app.models.schedule import Schedule

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

def seed_database():
    print("[+] Initializing Database schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    random.seed(42)

    # Pre-hash passwords once for high performance
    admin_pwd_hash = get_password_hash("admin123")
    company_pwd_hash = get_password_hash("company123")
    student_pwd_hash = get_password_hash("student123")

    # 1. Create Default Schedule
    print("[*] Creating Schedule...")
    default_schedule = Schedule(
        id=str(uuid.uuid4()),
        name="University Placement Week 2026",
        academic_year="2025-2026",
        status="ACTIVE"
    )
    db.add(default_schedule)

    # 2. Create Coordinators
    print("[*] Creating Coordinator accounts...")
    coord_user = User(
        id=str(uuid.uuid4()),
        email="coordinator@university.edu",
        hashed_password=admin_pwd_hash,
        role="COORDINATOR",
        is_active=True
    )
    db.add(coord_user)
    db.flush()

    coordinator = Coordinator(
        id=str(uuid.uuid4()),
        user_id=coord_user.id,
        name="Prof. Sarah Jenkins",
        department="Central Placement & Career Cell",
        phone="+1-555-0199"
    )
    db.add(coordinator)

    # 3. Create 20 Interview Rooms
    print("[*] Creating 20 Campus Interview Rooms...")
    created_rooms = []
    for i in range(1, 21):
        room = Room(
            id=str(uuid.uuid4()),
            room_code=f"R{i:02d}",
            building="Placement Complex Block A" if i <= 10 else "Placement Complex Block B",
            floor=1 if i <= 10 else 2,
            capacity=6,
            has_video_conf=True,
            is_active=True
        )
        db.add(room)
        created_rooms.append(room)
    db.flush()

    # 4. Create Companies & Panels
    print(f"[*] Creating {len(COMPANY_DEFS)} Companies and Panels...")
    created_companies = []
    for c_def in COMPANY_DEFS:
        c_user = User(
            id=str(uuid.uuid4()),
            email=f"{c_def['code'].lower()}@placement.edu",
            hashed_password=company_pwd_hash,
            role="COMPANY",
            is_active=True
        )
        db.add(c_user)
        db.flush()

        comp = Company(
            id=str(uuid.uuid4()),
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

        # Requirements
        req = CompanyRequirements(
            id=str(uuid.uuid4()),
            company_id=comp.id,
            min_cgpa=c_def["cgpa"],
            eligible_branches=json.dumps(c_def["branches"]),
            rounds_count=1
        )
        db.add(req)

        # Availability
        avail = CompanyAvailability(
            id=str(uuid.uuid4()),
            company_id=comp.id,
            day_number=1,
            start_time_slot=0,
            end_time_slot=12,
            is_available=True
        )
        db.add(avail)

        # Panels
        for p_idx in range(1, c_def["panels"] + 1):
            panel = Panel(
                id=str(uuid.uuid4()),
                company_id=comp.id,
                panel_code=f"P{p_idx}",
                interviewer_names=f"{comp.name} Tech Panel {p_idx}",
                is_active=True
            )
            db.add(panel)

    db.flush()

    # 5. Create 800 Students
    print("[*] Creating 800 Students...")
    created_students = []
    
    # Specific demo student S0421
    demo_s_user = User(
        id=str(uuid.uuid4()),
        email="s0421@student.edu",
        hashed_password=student_pwd_hash,
        role="STUDENT",
        is_active=True
    )
    db.add(demo_s_user)
    db.flush()

    demo_student = Student(
        id=str(uuid.uuid4()),
        user_id=demo_s_user.id,
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
    created_students.append(demo_student)

    # Generate remaining 799 students
    first_names = ["Aarav", "Ananya", "Rohan", "Priya", "Rahul", "Neha", "Vikram", "Sneha", "Aditya", "Pooja", "Arjun", "Kavya", "Siddharth", "Divya", "Karan", "Tanvi", "Varun", "Meera", "Gaurav", "Isha"]
    last_names = ["Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Rao", "Gupta", "Singh", "Das", "Menon", "Joshi", "Kulkarni", "Deshmukh", "Mehta", "Bhat"]

    for i in range(1, 800):
        code = f"S{i:04d}"
        if code == "S0421":
            continue
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        name = f"{fname} {lname}"
        email = f"{code.lower()}@student.edu"
        branch = random.choice(BRANCHES)
        cgpa = round(random.gauss(7.8, 0.9), 2)
        cgpa = max(5.5, min(9.95, cgpa))
        skills = random.sample(SKILLS_POOL, k=random.randint(3, 6))

        s_user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=student_pwd_hash,
            role="STUDENT",
            is_active=True
        )
        db.add(s_user)
        db.flush()

        student = Student(
            id=str(uuid.uuid4()),
            user_id=s_user.id,
            student_code=code,
            name=name,
            email=email,
            branch=branch,
            cgpa=cgpa,
            graduation_year=2026,
            skills=json.dumps(skills),
            is_active=True,
            is_withdrawn=False
        )
        db.add(student)
        created_students.append(student)

    db.flush()

    # 6. Generate Shortlists
    print("[*] Generating Shortlist Relationships with Competition Pressure...")
    shortlist_count = 0

    # Ensure demo student S0421 is shortlisted by top recruiters
    top_comps = [c[0] for c in created_companies[:4]]
    for comp in top_comps:
        sh = Shortlist(
            id=str(uuid.uuid4()),
            company_id=comp.id,
            student_id=demo_student.id,
            preference_rank=1,
            status="SHORTLISTED"
        )
        db.add(sh)
        shortlist_count += 1

    for comp, c_def in created_companies:
        min_cgpa = c_def["cgpa"]
        branches = c_def["branches"]
        eligible = [s for s in created_students if s.cgpa >= min_cgpa and (not branches or s.branch in branches)]
        target_size = min(len(eligible), random.randint(15, 25))
        selected_students = random.sample(eligible, k=target_size)

        for s in selected_students:
            if s.id == demo_student.id and comp.id in [c.id for c in top_comps]:
                continue
            sh = Shortlist(
                id=str(uuid.uuid4()),
                company_id=comp.id,
                student_id=s.id,
                preference_rank=random.randint(1, 3),
                status="SHORTLISTED"
            )
            db.add(sh)
            shortlist_count += 1

    db.commit()

    # 7. Generate Initial Schedule Version with CP-SAT Solver
    print("[*] Generating Initial Schedule Version via Google OR-Tools CP-SAT...")
    try:
        from app.services.schedule_service import ScheduleService
        sched_res = ScheduleService.generate_initial_schedule(db, max_time_seconds=15)
        print(f"[+] Initial Schedule Version {sched_res.get('version_number')} Generated: {sched_res.get('metrics', {}).get('scheduled_interviews', 0)} interviews scheduled.")
    except Exception as e:
        print(f"[!] Warning: Initial schedule generation skipped: {e}")

    db.close()
    print(f"[+] Seeding Complete: 800 Students, {len(COMPANY_DEFS)} Companies, 20 Rooms, {shortlist_count} Shortlists generated.")
    print("\nDefault Credentials:")
    print("  - Coordinator: coordinator@university.edu / admin123")
    print("  - Company: technova@placement.edu / company123")
    print("  - Student: s0421@student.edu / student123")

if __name__ == "__main__":
    seed_database()
