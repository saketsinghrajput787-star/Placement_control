import io
import json
import csv
import hashlib
import uuid
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentVersion, DocumentImport, DocumentImportError
from app.models.student import Student
from app.models.company import Company, CompanyRequirements, CompanyAvailability, Shortlist
from app.models.resource import Room, Panel
from app.models.schedule import Schedule, ScheduleVersion, Interview
from app.models.user import User
from app.core.security import get_password_hash

CATEGORIES = [
    "Students",
    "Companies",
    "Shortlists",
    "Rooms",
    "Panels",
    "Company Availability",
    "Student Availability",
    "Interview Requirements",
    "Placement Rules",
    "Other"
]

COLUMN_KEYWORDS = {
    "Students": {"name", "email", "branch", "cgpa", "student_code", "student_id", "graduation_year", "skills", "usn", "roll_no"},
    "Companies": {"company_code", "company_id", "company_name", "name", "industry", "email", "contact_email", "interview_date", "available_from", "available_to", "interview_duration_minutes", "interview_duration_mins", "priority_tier", "max_panels", "tier"},
    "Shortlists": {"company_code", "student_code", "company_id", "student_id", "preference_rank", "rank", "shortlist"},
    "Rooms": {"room_code", "room_id", "building", "floor", "capacity", "room"},
    "Panels": {"panel_code", "panel_id", "panel_name", "company_code", "company_id", "interviewer_names", "interviewer", "lead", "specialization", "panel", "panel_no", "panel_num", "status"},
    "Company Availability": {"company_code", "company_id", "day_number", "start_time_slot", "end_time_slot", "available_from", "available_to", "availability"},
    "Student Availability": {"student_code", "student_id", "available_from", "available_to", "time_slot"},
    "Interview Requirements": {"company_code", "company_id", "min_cgpa", "eligible_branches", "rounds_count"},
    "Placement Rules": {"rule_name", "rule_value", "max_interviews_per_day", "slot_duration"}
}

def get_field(row: Dict[str, Any], *aliases: str) -> Optional[str]:
    normalized_row = {
        k.strip().lower().replace(" ", "_"): (str(v).strip() if v is not None else "")
        for k, v in row.items() if k
    }
    for alias in aliases:
        norm_alias = alias.strip().lower().replace(" ", "_")
        if norm_alias in normalized_row:
            val = normalized_row[norm_alias]
            if val != "":
                return val
    return None

class DocumentService:
    @staticmethod
    def parse_file_content(filename: str, content: bytes) -> Tuple[List[str], List[Dict[str, Any]]]:
        ext = filename.split(".")[-1].lower()
        columns: List[str] = []
        rows: List[Dict[str, Any]] = []

        if ext == "csv":
            text = content.decode("utf-8-sig", errors="ignore")
            reader = csv.DictReader(io.StringIO(text))
            columns = [c.strip() for c in (reader.fieldnames or [])]
            for row in reader:
                clean_row = {k.strip(): (v.strip() if v else "") for k, v in row.items() if k}
                rows.append(clean_row)
        elif ext in ["xlsx", "xls"]:
            try:
                import pandas as pd
                df = pd.read_excel(io.BytesIO(content))
                df = df.fillna("")
                columns = [str(c).strip() for c in df.columns]
                for _, row in df.iterrows():
                    clean_row = {str(k).strip(): str(v).strip() for k, v in row.items()}
                    rows.append(clean_row)
            except Exception:
                text = content.decode("utf-8", errors="ignore")
                lines = [l for l in text.splitlines() if l.strip()]
                if lines:
                    columns = [c.strip() for c in lines[0].split(",")]
                    for line in lines[1:]:
                        vals = [v.strip() for v in line.split(",")]
                        row = {columns[i]: vals[i] if i < len(vals) else "" for i in range(len(columns))}
                        rows.append(row)
        else:
            text = content.decode("utf-8", errors="ignore")
            lines = [l for l in text.splitlines() if l.strip()]
            if lines:
                columns = ["content"]
                rows = [{"content": line} for line in lines]

        return columns, rows

    @staticmethod
    def detect_category(columns: List[str], filename: str) -> Tuple[str, float]:
        col_set = {c.lower().replace(" ", "_") for c in columns}
        filename_clean = filename.lower().replace("_", " ")

        scores: Dict[str, float] = {}
        for category, keywords in COLUMN_KEYWORDS.items():
            match_count = len(col_set.intersection(keywords))
            score = match_count / max(1, len(keywords))
            cat_clean = category.lower().replace("_", " ")
            if cat_clean in filename_clean or cat_clean[:-1] in filename_clean:
                score += 0.5
            scores[category] = score

        best_category = max(scores, key=scores.get) if scores else "Other"
        best_score = scores.get(best_category, 0.0)

        confidence = min(0.99, round(max(0.60, best_score * 0.8 + 0.35), 2))
        return best_category, confidence

    @staticmethod
    def validate_document_data(
        db: Session,
        document_type: str,
        columns: List[str],
        rows: List[Dict[str, Any]],
        placement_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        errors: List[Dict[str, Any]] = []
        valid_count = 0
        warning_count = 0
        error_count = 0

        seen_keys = set()
        email_regex = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

        for idx, row in enumerate(rows, start=1):
            row_errors = []

            if document_type == "Companies":
                c_id = get_field(row, "company_id", "company_code", "company_key", "id", "code")
                c_name = get_field(row, "company_name", "name", "title")
                email = get_field(row, "email", "contact_email", "hr_email", "email_address")
                duration = get_field(row, "interview_duration_minutes", "interview_duration_mins", "duration", "duration_mins")

                if not c_name:
                    row_errors.append({"col": "company_name", "type": "MISSING_VALUE", "msg": "Company name is required", "raw": ""})

                if c_id:
                    if c_id in seen_keys:
                        row_errors.append({"col": "company_id", "type": "DUPLICATE", "msg": f"Duplicate company identifier: '{c_id}'", "raw": c_id})
                    else:
                        seen_keys.add(c_id)

                if email and not email_regex.match(email):
                    row_errors.append({"col": "email", "type": "INVALID_EMAIL", "msg": f"Invalid email format: '{email}'", "raw": email})

                if duration:
                    try:
                        if int(duration) <= 0:
                            raise ValueError()
                    except ValueError:
                        row_errors.append({"col": "interview_duration_minutes", "type": "INVALID_INTEGER", "msg": f"Interview duration must be a positive integer, got '{duration}'", "raw": duration})

            elif document_type == "Students":
                name = get_field(row, "name", "student_name", "full_name")
                email = get_field(row, "email", "student_email", "email_address")
                branch = get_field(row, "branch", "department", "stream", "course")
                cgpa_str = get_field(row, "cgpa", "gpa", "score")

                if not name:
                    row_errors.append({"col": "name", "type": "MISSING_VALUE", "msg": "Student name is required", "raw": ""})

                if not email:
                    row_errors.append({"col": "email", "type": "MISSING_VALUE", "msg": "Student email is required", "raw": ""})
                elif not email_regex.match(email):
                    row_errors.append({"col": "email", "type": "INVALID_EMAIL", "msg": f"Invalid email format: '{email}'", "raw": email})
                elif email in seen_keys:
                    row_errors.append({"col": "email", "type": "DUPLICATE", "msg": f"Duplicate student email: '{email}'", "raw": email})
                else:
                    seen_keys.add(email)

                if not branch:
                    row_errors.append({"col": "branch", "type": "MISSING_VALUE", "msg": "Branch is required", "raw": ""})

                if cgpa_str is not None:
                    try:
                        cgpa_val = float(cgpa_str)
                        if cgpa_val < 0.0 or cgpa_val > 10.0:
                            row_errors.append({"col": "cgpa", "type": "INVALID_CGPA", "msg": f"CGPA must be between 0.0 and 10.0, got '{cgpa_str}'", "raw": cgpa_str})
                    except ValueError:
                        row_errors.append({"col": "cgpa", "type": "INVALID_FORMAT", "msg": f"CGPA must be a valid number, got '{cgpa_str}'", "raw": cgpa_str})
                else:
                    row_errors.append({"col": "cgpa", "type": "MISSING_VALUE", "msg": "CGPA is required", "raw": ""})

            elif document_type == "Shortlists":
                comp_code = get_field(row, "company_code", "company_id", "company", "comp_code", "comp_id")
                stud_code = get_field(row, "student_code", "student_id", "student", "usn", "roll_no")

                if not comp_code:
                    row_errors.append({"col": "company_code", "type": "MISSING_VALUE", "msg": "Company code is required", "raw": ""})
                if not stud_code:
                    row_errors.append({"col": "student_code", "type": "MISSING_VALUE", "msg": "Student code is required", "raw": ""})

                if comp_code and stud_code:
                    pair = f"{comp_code}_{stud_code}"
                    if pair in seen_keys:
                        row_errors.append({"col": "shortlist", "type": "DUPLICATE_SHORTLIST", "msg": f"Duplicate shortlist entry for {stud_code} and {comp_code}", "raw": pair})
                    else:
                        seen_keys.add(pair)

            elif document_type == "Rooms":
                room_code = get_field(row, "room_code", "room_id", "room", "name", "room_name")
                capacity = get_field(row, "capacity", "seats", "size")

                if not room_code:
                    row_errors.append({"col": "room_code", "type": "MISSING_VALUE", "msg": "Room code is required", "raw": ""})
                elif room_code in seen_keys:
                    row_errors.append({"col": "room_code", "type": "DUPLICATE", "msg": f"Duplicate room code: '{room_code}'", "raw": room_code})
                else:
                    seen_keys.add(room_code)

                if capacity:
                    try:
                        if int(capacity) <= 0:
                            raise ValueError()
                    except ValueError:
                        row_errors.append({"col": "capacity", "type": "INVALID_INTEGER", "msg": f"Capacity must be a positive integer, got '{capacity}'", "raw": capacity})

            elif document_type == "Panels":
                panel_code = get_field(row, "panel_code", "panel_id", "panel_name", "panel", "panel_no", "panel_num", "code", "id", "name")
                comp_code = get_field(row, "company_code", "company_id", "company_name", "company", "comp_code", "comp_id")

                if not panel_code:
                    row_errors.append({"col": "panel_code", "type": "MISSING_VALUE", "msg": "Panel code is required", "raw": ""})

                panel_key = f"{comp_code}_{panel_code}" if comp_code else panel_code
                if panel_code:
                    if panel_key in seen_keys:
                        row_errors.append({"col": "panel_code", "type": "DUPLICATE", "msg": f"Duplicate panel '{panel_code}' for company '{comp_code or 'general'}'", "raw": panel_code})
                    else:
                        seen_keys.add(panel_key)

            if row_errors:
                error_count += 1
                for err in row_errors:
                    errors.append({
                        "row_number": idx,
                        "column_name": err["col"],
                        "error_type": err["type"],
                        "error_message": err["msg"],
                        "raw_value": err.get("raw", ""),
                        "raw_row_data": json.dumps(row)
                    })
            else:
                valid_count += 1

        return {
            "total_rows": len(rows),
            "valid_count": valid_count,
            "warning_count": warning_count,
            "error_count": error_count,
            "errors": errors
        }

    @staticmethod
    def compare_and_diff(
        db: Session,
        document_id: str,
        rows: List[Dict[str, Any]],
        placement_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        doc = db.query(Document).get(document_id)
        doc_type = doc.document_type if doc else "Other"
        sess_id = placement_session_id or (doc.placement_session_id if doc else None)

        added, updated, removed, unchanged = 0, 0, 0, 0

        if doc_type == "Students":
            q = db.query(Student)
            if sess_id:
                q = q.filter(Student.placement_session_id == sess_id)
            existing = {s.student_code: s for s in q.all()}
            incoming_codes = set()
            for idx, r in enumerate(rows, start=1):
                code = get_field(r, "student_code", "student_id", "usn", "roll_no", "id", "code") or f"S{idx:04d}"
                incoming_codes.add(code)
                if code in existing:
                    updated += 1
                else:
                    added += 1
            removed = len(set(existing.keys()) - incoming_codes)
            unchanged = max(0, len(existing) - updated - removed)

        elif doc_type == "Companies":
            q = db.query(Company)
            if sess_id:
                q = q.filter(Company.placement_session_id == sess_id)
            existing = {c.company_code: c for c in q.all()}
            incoming_codes = set()
            for idx, r in enumerate(rows, start=1):
                code = get_field(r, "company_id", "company_code", "company_key", "id", "code") or f"C{idx:02d}"
                incoming_codes.add(code)
                if code in existing:
                    updated += 1
                else:
                    added += 1
            removed = len(set(existing.keys()) - incoming_codes)
            unchanged = max(0, len(existing) - updated - removed)

        elif doc_type == "Panels":
            q = db.query(Panel)
            if sess_id:
                q = q.filter(Panel.placement_session_id == sess_id)
            existing = {p.panel_code: p for p in q.all()}
            incoming_codes = set()
            for idx, r in enumerate(rows, start=1):
                p_code = get_field(r, "panel_id", "panel_code", "panel_name", "panel", "panel_no", "panel_num", "code", "id") or f"P{idx:02d}"
                incoming_codes.add(p_code)
                if p_code in existing:
                    updated += 1
                else:
                    added += 1
            removed = len(set(existing.keys()) - incoming_codes)
            unchanged = max(0, len(existing) - updated - removed)

        elif doc_type == "Rooms":
            q = db.query(Room)
            if sess_id:
                q = q.filter(Room.placement_session_id == sess_id)
            existing = {r.room_code: r for r in q.all()}
            incoming_codes = set()
            for idx, r in enumerate(rows, start=1):
                code = get_field(r, "room_code", "room_id", "room", "name", "room_name") or f"R{idx:02d}"
                incoming_codes.add(code)
                if code in existing:
                    updated += 1
                else:
                    added += 1
            removed = len(set(existing.keys()) - incoming_codes)
            unchanged = max(0, len(existing) - updated - removed)

        else:
            added = len(rows)

        return {
            "added": added,
            "updated": updated,
            "removed": removed,
            "unchanged": max(0, unchanged)
        }

    @staticmethod
    def time_str_to_slot(time_str: Optional[str]) -> int:
        if not time_str:
            return 0
        try:
            parts = str(time_str).strip().split(":")
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            mins_from_9 = (h - 9) * 60 + m
            return max(0, min(12, int(mins_from_9 // 45)))
        except Exception:
            return 0

    @staticmethod
    def parse_tier(tier_str: Optional[str]) -> int:
        if not tier_str:
            return 1
        ts = str(tier_str).strip().lower()
        if "1" in ts or "mass" in ts or "tier 1" in ts or "tier-1" in ts:
            return 1
        if "2" in ts or "tier 2" in ts or "tier-2" in ts:
            return 2
        if "3" in ts or "tier 3" in ts or "tier-3" in ts:
            return 3
        try:
            val = int(ts)
            return max(1, min(3, val))
        except ValueError:
            return 1

    @staticmethod
    def clear_existing_schedules_for_session(db: Session, placement_session_id: str):
        """Purges any existing schedules for a session when a dataset is replaced."""
        scheds = db.query(Schedule).filter(Schedule.placement_session_id == placement_session_id).all()
        for s in scheds:
            versions = db.query(ScheduleVersion).filter(ScheduleVersion.schedule_id == s.id).all()
            for v in versions:
                db.query(Interview).filter(Interview.schedule_version_id == v.id).delete(synchronize_session=False)
            db.query(ScheduleVersion).filter(ScheduleVersion.schedule_id == s.id).delete(synchronize_session=False)
        db.query(Schedule).filter(Schedule.placement_session_id == placement_session_id).delete(synchronize_session=False)
        db.flush()

    @staticmethod
    def persist_imported_data(
        db: Session,
        document_type: str,
        rows: List[Dict[str, Any]],
        placement_session_id: str,
        import_mode: str = "REPLACE" # REPLACE, APPEND, UPDATE
    ) -> int:
        persisted_count = 0
        mode = (import_mode or "REPLACE").upper()

        if mode == "REPLACE":
            DocumentService.clear_existing_schedules_for_session(db, placement_session_id)

            if document_type == "Students":
                db.query(Student).filter(Student.placement_session_id == placement_session_id).delete(synchronize_session=False)
            elif document_type == "Companies":
                db.query(CompanyRequirements).filter(CompanyRequirements.placement_session_id == placement_session_id).delete(synchronize_session=False)
                db.query(CompanyAvailability).filter(CompanyAvailability.placement_session_id == placement_session_id).delete(synchronize_session=False)
                db.query(Company).filter(Company.placement_session_id == placement_session_id).delete(synchronize_session=False)
            elif document_type == "Rooms":
                db.query(Room).filter(Room.placement_session_id == placement_session_id).delete(synchronize_session=False)
            elif document_type == "Panels":
                db.query(Panel).filter(Panel.placement_session_id == placement_session_id).delete(synchronize_session=False)
            elif document_type == "Shortlists":
                db.query(Shortlist).filter(Shortlist.placement_session_id == placement_session_id).delete(synchronize_session=False)
            db.flush()

        if document_type == "Companies":
            company_pwd_hash = get_password_hash("company123")
            for idx, r in enumerate(rows, start=1):
                c_code = get_field(r, "company_id", "company_code", "company_key", "id", "code") or f"C{idx:02d}"
                c_name = get_field(r, "company_name", "name", "title") or f"Company {c_code}"
                industry = get_field(r, "industry", "sector", "domain") or "Technology"
                email = get_field(r, "email", "contact_email", "hr_email", "email_address") or f"{c_code.lower()}@placement.edu"
                
                tier_raw = get_field(r, "tier", "priority_tier", "priority")
                priority_tier = DocumentService.parse_tier(tier_raw)

                duration_raw = get_field(r, "interview_duration_minutes", "interview_duration_mins", "duration", "duration_mins")
                duration_mins = int(duration_raw) if duration_raw and duration_raw.isdigit() else 45

                panel_count_raw = get_field(r, "panel_count", "max_panels", "panels")
                max_panels = int(panel_count_raw) if panel_count_raw and panel_count_raw.isdigit() else 4

                min_cgpa_raw = get_field(r, "min_cgpa", "cgpa_cutoff", "cutoff_cgpa", "cgpa")
                min_cgpa = float(min_cgpa_raw) if min_cgpa_raw else 6.0

                c_user = db.query(User).filter(User.email == email).first()
                if not c_user:
                    c_user = User(
                        id=str(uuid.uuid4()),
                        email=email,
                        hashed_password=company_pwd_hash,
                        role="COMPANY",
                        is_active=True
                    )
                    db.add(c_user)
                    db.flush()

                comp = None
                if mode != "REPLACE":
                    comp = db.query(Company).filter(
                        Company.placement_session_id == placement_session_id,
                        (Company.company_code == c_code) | (Company.name == c_name)
                    ).first()

                if comp:
                    comp.company_code = c_code
                    comp.name = c_name
                    comp.industry = industry
                    comp.priority_tier = priority_tier
                    comp.interview_duration_mins = duration_mins
                    comp.max_panels = max_panels
                    comp.user_id = c_user.id
                else:
                    comp = Company(
                        id=str(uuid.uuid4()),
                        placement_session_id=placement_session_id,
                        user_id=c_user.id,
                        company_code=c_code,
                        name=c_name,
                        industry=industry,
                        priority_tier=priority_tier,
                        interview_duration_mins=duration_mins,
                        max_panels=max_panels
                    )
                    db.add(comp)
                    db.flush()

                # CompanyRequirements
                req = db.query(CompanyRequirements).filter(
                    CompanyRequirements.placement_session_id == placement_session_id,
                    CompanyRequirements.company_id == comp.id
                ).first()
                if not req:
                    req = CompanyRequirements(
                        id=str(uuid.uuid4()),
                        placement_session_id=placement_session_id,
                        company_id=comp.id,
                        min_cgpa=min_cgpa,
                        eligible_branches=json.dumps([]),
                        rounds_count=1
                    )
                    db.add(req)
                else:
                    req.min_cgpa = min_cgpa

                persisted_count += 1

        elif document_type == "Company Availability":
            for idx, r in enumerate(rows, start=1):
                c_code = get_field(r, "company_id", "company_code", "company_name", "company", "comp_code", "comp_id")
                if not c_code:
                    continue
                comp = db.query(Company).filter(
                    Company.placement_session_id == placement_session_id,
                    (Company.company_code == c_code) | (Company.id == c_code) | (Company.name.ilike(c_code))
                ).first()
                if not comp:
                    continue
                
                start_str = get_field(r, "available_from", "start_time", "from_time") or "09:00"
                end_str = get_field(r, "available_to", "end_time", "to_time") or "18:00"
                
                start_slot = DocumentService.time_str_to_slot(start_str)
                end_slot = DocumentService.time_str_to_slot(end_str)
                if end_slot <= start_slot:
                    end_slot = min(12, start_slot + 4)

                avail = db.query(CompanyAvailability).filter(
                    CompanyAvailability.placement_session_id == placement_session_id,
                    CompanyAvailability.company_id == comp.id
                ).first()
                if avail:
                    avail.start_time_slot = start_slot
                    avail.end_time_slot = end_slot
                    avail.is_available = True
                else:
                    avail = CompanyAvailability(
                        id=str(uuid.uuid4()),
                        placement_session_id=placement_session_id,
                        company_id=comp.id,
                        day_number=1,
                        start_time_slot=start_slot,
                        end_time_slot=end_slot,
                        is_available=True
                    )
                    db.add(avail)
                persisted_count += 1

        elif document_type == "Panels":
            all_companies = db.query(Company).filter(Company.placement_session_id == placement_session_id).order_by(Company.company_code.asc()).all()
            for idx, r in enumerate(rows, start=1):
                p_code = get_field(r, "panel_id", "panel_code", "panel_name", "panel", "panel_no", "panel_num", "code", "id") or f"P{idx:02d}"
                c_code = get_field(r, "company_code", "company_id", "company_name", "company", "comp_code", "comp_id")
                interviewers = get_field(r, "interviewer_names", "interviewer_name", "interviewers", "interviewer", "lead", "panel_name", "specialization", "names") or f"Panel {p_code}"
                
                comp = None
                if c_code:
                    comp = db.query(Company).filter(
                        Company.placement_session_id == placement_session_id,
                        (Company.company_code.ilike(c_code)) | (Company.id == c_code) | (Company.name.ilike(c_code))
                    ).first()
                if not comp and all_companies:
                    comp = all_companies[(idx - 1) % len(all_companies)]

                if comp:
                    panel = None
                    if mode != "REPLACE":
                        panel = db.query(Panel).filter(
                            Panel.placement_session_id == placement_session_id,
                            Panel.panel_code == p_code
                        ).first()

                    if panel:
                        panel.interviewer_names = interviewers
                        panel.company_id = comp.id
                    else:
                        panel = Panel(
                            id=str(uuid.uuid4()),
                            placement_session_id=placement_session_id,
                            company_id=comp.id,
                            panel_code=p_code,
                            interviewer_names=interviewers,
                            is_active=True
                        )
                        db.add(panel)
                    persisted_count += 1

        elif document_type == "Rooms":
            for idx, r in enumerate(rows, start=1):
                r_code = get_field(r, "room_id", "room_code", "room", "name", "room_name") or f"R{idx:02d}"
                building = get_field(r, "building", "block", "location") or "Placement Complex"
                floor_str = get_field(r, "floor", "level") or "1"
                cap_str = get_field(r, "capacity", "seats", "size") or "10"
                
                try:
                    floor_val = int(floor_str)
                except ValueError:
                    floor_val = 1
                try:
                    cap_val = int(cap_str)
                except ValueError:
                    cap_val = 10

                room = None
                if mode != "REPLACE":
                    room = db.query(Room).filter(
                        Room.placement_session_id == placement_session_id,
                        Room.room_code == r_code
                    ).first()

                if room:
                    room.building = building
                    room.floor = floor_val
                    room.capacity = cap_val
                else:
                    room = Room(
                        id=str(uuid.uuid4()),
                        placement_session_id=placement_session_id,
                        room_code=r_code,
                        building=building,
                        floor=floor_val,
                        capacity=cap_val,
                        is_active=True
                    )
                    db.add(room)
                persisted_count += 1

        elif document_type == "Students":
            student_pwd_hash = get_password_hash("student123")
            for idx, r in enumerate(rows, start=1):
                s_code = get_field(r, "student_id", "student_code", "usn", "roll_no", "id", "code") or f"S{idx:04d}"
                s_name = get_field(r, "name", "student_name", "full_name") or f"Student {s_code}"
                s_email = get_field(r, "email", "student_email", "email_address") or f"{s_code.lower()}@student.edu"
                branch = get_field(r, "branch", "department", "stream", "course") or "CSE"
                cgpa_str = get_field(r, "cgpa", "gpa", "score") or "7.5"
                try:
                    cgpa_val = float(cgpa_str)
                except ValueError:
                    cgpa_val = 7.5

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

                stud = None
                if mode != "REPLACE":
                    stud = db.query(Student).filter(
                        Student.placement_session_id == placement_session_id,
                        (Student.student_code == s_code) | (Student.email == s_email)
                    ).first()

                if stud:
                    stud.name = s_name
                    stud.student_code = s_code
                    stud.email = s_email
                    stud.branch = branch
                    stud.cgpa = cgpa_val
                    stud.user_id = s_user.id
                else:
                    stud = Student(
                        id=str(uuid.uuid4()),
                        placement_session_id=placement_session_id,
                        user_id=s_user.id,
                        student_code=s_code,
                        name=s_name,
                        email=s_email,
                        branch=branch,
                        cgpa=cgpa_val
                    )
                    db.add(stud)
                persisted_count += 1

        elif document_type == "Shortlists":
            for idx, r in enumerate(rows, start=1):
                c_code = get_field(r, "company_code", "company_id", "company", "comp_code", "comp_id", "company_name")
                s_code = get_field(r, "student_code", "student_id", "student", "usn", "roll_no", "student_name", "email")
                rank_str = get_field(r, "preference_rank", "rank", "priority") or "1"
                try:
                    rank_val = int(rank_str)
                except ValueError:
                    rank_val = 1

                if c_code and s_code:
                    comp = db.query(Company).filter(
                        Company.placement_session_id == placement_session_id,
                        (Company.company_code.ilike(c_code)) | (Company.id == c_code) | (Company.name.ilike(c_code))
                    ).first()
                    if not comp:
                        comp = db.query(Company).filter(
                            Company.placement_session_id == placement_session_id,
                            Company.company_code.ilike(f"%{c_code}%")
                        ).first()

                    stud = db.query(Student).filter(
                        Student.placement_session_id == placement_session_id,
                        (Student.student_code.ilike(s_code)) | (Student.id == s_code) | (Student.email.ilike(s_code)) | (Student.name.ilike(s_code))
                    ).first()
                    if not stud:
                        stud = db.query(Student).filter(
                            Student.placement_session_id == placement_session_id,
                            Student.student_code.ilike(f"%{s_code}%")
                        ).first()

                    if comp and stud:
                        sh = None
                        if mode != "REPLACE":
                            sh = db.query(Shortlist).filter(
                                Shortlist.placement_session_id == placement_session_id,
                                Shortlist.company_id == comp.id,
                                Shortlist.student_id == stud.id
                            ).first()

                        if sh:
                            sh.preference_rank = rank_val
                        else:
                            sh = Shortlist(
                                id=str(uuid.uuid4()),
                                placement_session_id=placement_session_id,
                                company_id=comp.id,
                                student_id=stud.id,
                                preference_rank=rank_val,
                                status="SHORTLISTED"
                            )
                            db.add(sh)
                        persisted_count += 1

        db.flush()
        return persisted_count
