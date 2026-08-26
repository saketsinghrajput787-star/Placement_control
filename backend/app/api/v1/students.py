import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.student import Student
from app.models.company import Shortlist, Company
from app.models.schedule import Interview, ScheduleVersion
from app.schemas.student import StudentOut, StudentWithShortlists, StudentUpdate
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/students", tags=["students"])

@router.get("", response_model=List[StudentWithShortlists])
def list_students(
    branch: Optional[str] = None,
    min_cgpa: Optional[float] = None,
    search: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Student).filter(Student.is_active == True)
    if branch:
        query = query.filter(Student.branch == branch)
    if min_cgpa:
        query = query.filter(Student.cgpa >= min_cgpa)
    if search:
        query = query.filter(
            (Student.name.ilike(f"%{search}%")) | (Student.student_code.ilike(f"%{search}%")) | (Student.email.ilike(f"%{search}%"))
        )

    students = query.order_by(Student.student_code).offset(offset).limit(limit).all()

    # Get latest version for interview counts
    latest_version = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
    version_id = latest_version.id if latest_version else None

    result = []
    for s in students:
        shortlists = db.query(Shortlist).filter(Shortlist.student_id == s.id).all()
        comp_ids = [sh.company_id for sh in shortlists]
        comps = db.query(Company).filter(Company.id.in_(comp_ids)).all() if comp_ids else []
        comp_names = [c.name for c in comps]

        interview_count = 0
        if version_id:
            interview_count = db.query(Interview).filter(
                Interview.schedule_version_id == version_id,
                Interview.student_id == s.id
            ).count()

        skills_list = json.loads(s.skills) if s.skills else []

        result.append(StudentWithShortlists(
            id=s.id,
            user_id=s.user_id,
            student_code=s.student_code,
            name=s.name,
            email=s.email,
            branch=s.branch,
            cgpa=s.cgpa,
            graduation_year=s.graduation_year,
            skills=skills_list,
            is_active=s.is_active,
            is_withdrawn=s.is_withdrawn,
            shortlisted_companies=comp_names,
            interview_count=interview_count
        ))

    return result

@router.get("/me/profile", response_model=StudentWithShortlists)
def get_student_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["STUDENT"]))
):
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    shortlists = db.query(Shortlist).filter(Shortlist.student_id == student.id).all()
    comp_ids = [sh.company_id for sh in shortlists]
    comps = db.query(Company).filter(Company.id.in_(comp_ids)).all() if comp_ids else []
    comp_names = [c.name for c in comps]

    latest_version = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
    interview_count = 0
    if latest_version:
        interview_count = db.query(Interview).filter(
            Interview.schedule_version_id == latest_version.id,
            Interview.student_id == student.id
        ).count()

    skills_list = json.loads(student.skills) if student.skills else []

    return StudentWithShortlists(
        id=student.id,
        user_id=student.user_id,
        student_code=student.student_code,
        name=student.name,
        email=student.email,
        branch=student.branch,
        cgpa=student.cgpa,
        graduation_year=student.graduation_year,
        skills=skills_list,
        is_active=student.is_active,
        is_withdrawn=student.is_withdrawn,
        shortlisted_companies=comp_names,
        interview_count=interview_count
    )

@router.get("/{student_id}", response_model=StudentWithShortlists)
def get_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    s = db.query(Student).get(student_id)
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")

    shortlists = db.query(Shortlist).filter(Shortlist.student_id == s.id).all()
    comp_ids = [sh.company_id for sh in shortlists]
    comps = db.query(Company).filter(Company.id.in_(comp_ids)).all() if comp_ids else []
    comp_names = [c.name for c in comps]

    latest_version = db.query(ScheduleVersion).order_by(ScheduleVersion.version_number.desc()).first()
    interview_count = 0
    if latest_version:
        interview_count = db.query(Interview).filter(
            Interview.schedule_version_id == latest_version.id,
            Interview.student_id == s.id
        ).count()

    skills_list = json.loads(s.skills) if s.skills else []

    return StudentWithShortlists(
        id=s.id,
        user_id=s.user_id,
        student_code=s.student_code,
        name=s.name,
        email=s.email,
        branch=s.branch,
        cgpa=s.cgpa,
        graduation_year=s.graduation_year,
        skills=skills_list,
        is_active=s.is_active,
        is_withdrawn=s.is_withdrawn,
        shortlisted_companies=comp_names,
        interview_count=interview_count
    )
