import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.company import Company, CompanyRequirements, CompanyAvailability, Shortlist
from app.models.resource import Panel
from app.schemas.company import (
    CompanyOut, CompanyCreate, CompanyUpdate,
    CompanyRequirementSchema, CompanyAvailabilitySchema
)
from app.api.deps import get_current_user, require_role, get_current_session_id
from app.services.disruption_service import DisruptionService
from app.services.event_service import EventService

router = APIRouter(prefix="/companies", tags=["companies"])

@router.get("", response_model=List[CompanyOut])
def list_companies(
    tier: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Company).filter(
        Company.placement_session_id == session_id,
        Company.is_active == True
    )
    if tier:
        query = query.filter(Company.priority_tier == tier)
    if search:
        query = query.filter(Company.name.ilike(f"%{search}%") | Company.company_code.ilike(f"%{search}%"))

    companies = query.order_by(Company.priority_tier, Company.name).all()

    result = []
    for c in companies:
        req = db.query(CompanyRequirements).filter(
            CompanyRequirements.placement_session_id == session_id,
            CompanyRequirements.company_id == c.id
        ).first()
        req_schema = None
        if req:
            req_schema = CompanyRequirementSchema(
                min_cgpa=req.min_cgpa,
                eligible_branches=json.loads(req.eligible_branches) if req.eligible_branches else ["CSE"],
                rounds_count=req.rounds_count
            )

        avails = db.query(CompanyAvailability).filter(
            CompanyAvailability.placement_session_id == session_id,
            CompanyAvailability.company_id == c.id
        ).all()
        avail_schemas = [
            CompanyAvailabilitySchema(
                day_number=a.day_number,
                start_time_slot=a.start_time_slot,
                end_time_slot=a.end_time_slot,
                is_available=a.is_available
            )
            for a in avails
        ]

        panels_count = db.query(Panel).filter(
            Panel.placement_session_id == session_id,
            Panel.company_id == c.id,
            Panel.is_active == True
        ).count()
        shortlists_count = db.query(Shortlist).filter(
            Shortlist.placement_session_id == session_id,
            Shortlist.company_id == c.id,
            Shortlist.status != "WITHDRAWN"
        ).count()

        result.append(CompanyOut(
            id=c.id,
            user_id=c.user_id,
            company_code=c.company_code,
            name=c.name,
            industry=c.industry,
            priority_tier=c.priority_tier,
            interview_duration_mins=c.interview_duration_mins,
            max_panels=c.max_panels,
            is_active=c.is_active,
            requirements=req_schema,
            availability=avail_schemas,
            panels_count=panels_count,
            shortlisted_count=shortlists_count
        ))

    return result

@router.get("/me/profile", response_model=CompanyOut)
def get_company_profile(
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(require_role(["COMPANY"]))
):
    comp = db.query(Company).filter(
        Company.placement_session_id == session_id,
        (Company.user_id == current_user.id) | (Company.company_code.ilike(f"%{current_user.id[:4]}%"))
    ).first()
    if not comp:
        comp = db.query(Company).filter(Company.placement_session_id == session_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Company profile not found")

    req = db.query(CompanyRequirements).filter(
        CompanyRequirements.placement_session_id == session_id,
        CompanyRequirements.company_id == comp.id
    ).first()
    req_schema = None
    if req:
        req_schema = CompanyRequirementSchema(
            min_cgpa=req.min_cgpa,
            eligible_branches=json.loads(req.eligible_branches) if req.eligible_branches else ["CSE"],
            rounds_count=req.rounds_count
        )

    avails = db.query(CompanyAvailability).filter(
        CompanyAvailability.placement_session_id == session_id,
        CompanyAvailability.company_id == comp.id
    ).all()
    avail_schemas = [
        CompanyAvailabilitySchema(
            day_number=a.day_number,
            start_time_slot=a.start_time_slot,
            end_time_slot=a.end_time_slot,
            is_available=a.is_available
        )
        for a in avails
    ]

    panels_count = db.query(Panel).filter(
        Panel.placement_session_id == session_id,
        Panel.company_id == comp.id,
        Panel.is_active == True
    ).count()
    shortlists_count = db.query(Shortlist).filter(
        Shortlist.placement_session_id == session_id,
        Shortlist.company_id == comp.id,
        Shortlist.status != "WITHDRAWN"
    ).count()

    return CompanyOut(
        id=comp.id,
        user_id=comp.user_id,
        company_code=comp.company_code,
        name=comp.name,
        industry=comp.industry,
        priority_tier=comp.priority_tier,
        interview_duration_mins=comp.interview_duration_mins,
        max_panels=comp.max_panels,
        is_active=comp.is_active,
        requirements=req_schema,
        availability=avail_schemas,
        panels_count=panels_count,
        shortlisted_count=shortlists_count
    )

@router.put("/me/requirements", response_model=CompanyRequirementSchema)
def update_company_requirements(
    req_update: CompanyRequirementSchema,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(require_role(["COMPANY"]))
):
    comp = db.query(Company).filter(
        Company.placement_session_id == session_id,
        Company.user_id == current_user.id
    ).first()
    if not comp:
        comp = db.query(Company).filter(Company.placement_session_id == session_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Company profile not found")

    req = db.query(CompanyRequirements).filter(
        CompanyRequirements.placement_session_id == session_id,
        CompanyRequirements.company_id == comp.id
    ).first()
    if not req:
        req = CompanyRequirements(
            placement_session_id=session_id,
            company_id=comp.id
        )
        db.add(req)

    req.min_cgpa = req_update.min_cgpa
    req.eligible_branches = json.dumps(req_update.eligible_branches)
    req.rounds_count = req_update.rounds_count
    db.commit()
    return req_update

@router.post("/{id}/delay")
def report_company_delay(
    id: str,
    delay_hours: float = Body(..., embed=True),
    reason: str = Body("Travel delay", embed=True),
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == id,
        Company.placement_session_id == session_id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    delay_slots = int(round(delay_hours / 0.75))

    res = DisruptionService.simulate_disruption(
        db=db,
        placement_session_id=session_id,
        event_type="COMPANY_DELAY",
        target_entity_type="company",
        target_entity_id=company.id,
        delay_slots=delay_slots,
        reason=reason
    )

    EventService.create_audit_log(
        db,
        action="COMPANY_DELAY_REPORTED",
        entity_type="COMPANY",
        entity_id=company.id,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        reason=reason,
        details={"delay_hours": delay_hours, "delay_slots": delay_slots}
    )

    return res

@router.post("/{id}/cancel")
async def cancel_company_drive(
    id: str,
    reason: str = Body("Placement drive cancelled", embed=True),
    db: Session = Depends(get_db),
    session_id: str = Depends(get_current_session_id),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == id,
        Company.placement_session_id == session_id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    res = DisruptionService.simulate_disruption(
        db=db,
        placement_session_id=session_id,
        event_type="COMPANY_CANCELLATION",
        target_entity_type="company",
        target_entity_id=company.id,
        reason=reason
    )

    EventService.create_audit_log(
        db,
        action="COMPANY_DRIVE_CANCELLED",
        entity_type="COMPANY",
        entity_id=company.id,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        reason=reason
    )

    await EventService.broadcast_live_event({
        "type": "COMPANY_CANCELLED",
        "placement_session_id": session_id,
        "company_id": company.id,
        "company_name": company.name,
        "message": f"{company.name} placement drive cancelled."
    })

    return res
