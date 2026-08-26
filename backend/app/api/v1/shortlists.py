from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.company import Company, Shortlist
from app.models.student import Student
from app.schemas.company import ShortlistOut, ShortlistCreate, ShortlistBatchCreate
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/shortlists", tags=["shortlists"])

@router.get("/company/{company_id}", response_model=List[ShortlistOut])
def get_company_shortlists(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shortlists = db.query(Shortlist).filter(
        Shortlist.company_id == company_id,
        Shortlist.status != "WITHDRAWN"
    ).all()

    student_ids = [sh.student_id for sh in shortlists]
    students = {s.id: s for s in db.query(Student).filter(Student.id.in_(student_ids)).all()}

    result = []
    for sh in shortlists:
        s = students.get(sh.student_id)
        if s:
            result.append(ShortlistOut(
                id=sh.id,
                company_id=sh.company_id,
                student_id=sh.student_id,
                student_code=s.student_code,
                student_name=s.name,
                student_branch=s.branch,
                student_cgpa=s.cgpa,
                preference_rank=sh.preference_rank,
                status=sh.status
            ))
    return result

@router.post("", response_model=ShortlistOut)
def add_shortlist_entry(
    sh_in: ShortlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["COORDINATOR", "COMPANY"]))
):
    existing = db.query(Shortlist).filter(
        Shortlist.company_id == sh_in.company_id,
        Shortlist.student_id == sh_in.student_id
    ).first()

    if existing:
        existing.status = "SHORTLISTED"
        db.commit()
        db.refresh(existing)
        sh = existing
    else:
        sh = Shortlist(**sh_in.dict())
        db.add(sh)
        db.commit()
        db.refresh(sh)

    s = db.query(Student).get(sh.student_id)
    return ShortlistOut(
        id=sh.id,
        company_id=sh.company_id,
        student_id=sh.student_id,
        student_code=s.student_code if s else "",
        student_name=s.name if s else "",
        student_branch=s.branch if s else "",
        student_cgpa=s.cgpa if s else 0.0,
        preference_rank=sh.preference_rank,
        status=sh.status
    )
