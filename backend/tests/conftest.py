import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
from app.core.security import get_password_hash
from app.models.user import User, Coordinator
from app.models.student import Student
from app.models.company import Company, CompanyRequirements, CompanyAvailability, Shortlist
from app.models.resource import Room, Panel
import json
import uuid

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_placement_tower.db"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("test_placement_tower.db"):
        try:
            os.remove("test_placement_tower.db")
        except Exception:
            pass

@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def sample_data(db_session):
    # Coordinator
    c_user = User(id=str(uuid.uuid4()), email="test_coord@university.edu", hashed_password=get_password_hash("admin123"), role="COORDINATOR")
    db_session.add(c_user)
    coord = Coordinator(id=str(uuid.uuid4()), user_id=c_user.id, name="Test Coordinator")
    db_session.add(coord)

    # Student
    s_user = User(id=str(uuid.uuid4()), email="test_s01@student.edu", hashed_password=get_password_hash("student123"), role="STUDENT")
    db_session.add(s_user)
    student = Student(id=str(uuid.uuid4()), user_id=s_user.id, student_code="S0001", name="Alice Smith", email="test_s01@student.edu", branch="CSE", cgpa=8.5, skills="[]")
    db_session.add(student)

    # Company
    comp_user = User(id=str(uuid.uuid4()), email="test_comp@placement.edu", hashed_password=get_password_hash("company123"), role="COMPANY")
    db_session.add(comp_user)
    comp = Company(id=str(uuid.uuid4()), user_id=comp_user.id, company_code="TESTCO", name="TestCorp", priority_tier=1, max_panels=2)
    db_session.add(comp)
    req = CompanyRequirements(id=str(uuid.uuid4()), company_id=comp.id, min_cgpa=7.0, eligible_branches='["CSE","ISE"]')
    db_session.add(req)
    avail = CompanyAvailability(id=str(uuid.uuid4()), company_id=comp.id, start_time_slot=0, end_time_slot=12)
    db_session.add(avail)

    # Room & Panel
    room = Room(id=str(uuid.uuid4()), room_code="R01", building="Block A")
    db_session.add(room)
    panel = Panel(id=str(uuid.uuid4()), company_id=comp.id, panel_code="P1")
    db_session.add(panel)

    # Shortlist
    sh = Shortlist(id=str(uuid.uuid4()), company_id=comp.id, student_id=student.id, status="SHORTLISTED")
    db_session.add(sh)

    db_session.commit()

    return {
        "coordinator_user": c_user,
        "student_user": s_user,
        "student": student,
        "company_user": comp_user,
        "company": comp,
        "room": room,
        "panel": panel,
        "shortlist": sh
    }
