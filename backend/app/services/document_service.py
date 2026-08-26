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
from app.models.user import User

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
    """
    Extracts a value from a row dictionary matching any of the provided field aliases,
    case-insensitively, ignoring spaces and underscores.
    """
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
            except Exception as e:
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
        rows: List[Dict[str, Any]]
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
                industry = get_field(row, "industry", "sector", "domain")
                email = get_field(row, "email", "contact_email", "hr_email", "email_address")
                interview_date = get_field(row, "interview_date", "date", "date_of_interview")
                available_from = get_field(row, "available_from", "start_time", "from_time")
                available_to = get_field(row, "available_to", "end_time", "to_time")
                duration = get_field(row, "interview_duration_minutes", "interview_duration_mins", "duration", "duration_mins")

                if not c_name:
                    row_errors.append({
                        "col": "company_name",
                        "type": "MISSING_VALUE",
                        "msg": "Company name is required",
                        "raw": ""
                    })

                if c_id:
                    if c_id in seen_keys:
                        row_errors.append({
                            "col": "company_id",
                            "type": "DUPLICATE",
                            "msg": f"Duplicate company identifier: '{c_id}'",
                            "raw": c_id
                        })
                    else:
                        seen_keys.add(c_id)

                if email:
                    if not email_regex.match(email):
                        row_errors.append({
                            "col": "email",
                            "type": "INVALID_EMAIL",
                            "msg": f"Invalid email format: '{email}'",
                            "raw": email
                        })

                if interview_date:
                    try:
                        datetime.strptime(interview_date, "%Y-%m-%d")
                    except ValueError:
                        row_errors.append({
                            "col": "interview_date",
                            "type": "INVALID_DATE_FORMAT",
                            "msg": f"Interview date must be in YYYY-MM-DD format, got '{interview_date}'",
                            "raw": interview_date
                        })

                if available_from:
                    try:
                        parts = available_from.split(":")
                        if len(parts) != 2 or not (0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
                            raise ValueError()
                    except Exception:
                        row_errors.append({
                            "col": "available_from",
                            "type": "INVALID_TIME_FORMAT",
                            "msg": f"Available from time must be in HH:MM format, got '{available_from}'",
                            "raw": available_from
                        })

                if available_to:
                    try:
                        parts = available_to.split(":")
                        if len(parts) != 2 or not (0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
                            raise ValueError()
                    except Exception:
                        row_errors.append({
                            "col": "available_to",
                            "type": "INVALID_TIME_FORMAT",
                            "msg": f"Available to time must be in HH:MM format, got '{available_to}'",
                            "raw": available_to
                        })

                if duration:
                    try:
                        dur_val = int(duration)
                        if dur_val <= 0:
                            raise ValueError()
                    except ValueError:
                        row_errors.append({
                            "col": "interview_duration_minutes",
                            "type": "INVALID_INTEGER",
                            "msg": f"Interview duration must be a positive integer, got '{duration}'",
                            "raw": duration
                        })

            elif document_type == "Students":
                name = get_field(row, "name", "student_name", "full_name")
                email = get_field(row, "email", "student_email", "email_address")
                branch = get_field(row, "branch", "department", "stream", "course")
                cgpa_str = get_field(row, "cgpa", "gpa", "score")
                code = get_field(row, "student_code", "student_id", "usn", "roll_no", "id", "code")

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
                        cap_val = int(capacity)
                        if cap_val <= 0:
                            raise ValueError()
                    except ValueError:
                        row_errors.append({"col": "capacity", "type": "INVALID_INTEGER", "msg": f"Capacity must be a positive integer, got '{capacity}'", "raw": capacity})

            elif document_type == "Panels":
                panel_code = get_field(row, "panel_code", "panel_id", "panel_name", "panel", "panel_no", "panel_num", "panel_number", "code", "id", "name")
                comp_code = get_field(row, "company_code", "company_id", "company_name", "company", "comp_code", "comp_id", "recruiter", "firm", "corporate")

                if not panel_code:
                    row_errors.append({"col": "panel_code", "type": "MISSING_VALUE", "msg": "Panel code is required", "raw": ""})

                panel_key = f"{comp_code}_{panel_code}" if comp_code else panel_code
                if panel_code:
                    if panel_key in seen_keys:
                        row_errors.append({"col": "panel_code", "type": "DUPLICATE", "msg": f"Duplicate panel '{panel_code}' for company '{comp_code or 'general'}'", "raw": panel_code})
                    else:
                        seen_keys.add(panel_key)

            elif document_type == "Company Availability":
                comp_code = get_field(row, "company_code", "company_id", "company_name", "company", "comp_code", "comp_id", "recruiter", "firm")
                if not comp_code:
                    row_errors.append({"col": "company_code", "type": "MISSING_VALUE", "msg": "Company code is required", "raw": ""})

            elif document_type == "Student Availability":
                stud_code = get_field(row, "student_code", "student_id", "usn", "roll_no", "student_name", "student", "code", "id")
                if not stud_code:
                    row_errors.append({"col": "student_code", "type": "MISSING_VALUE", "msg": "Student code is required", "raw": ""})

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
        rows: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        doc = db.query(Document).get(document_id)
        if not doc:
            return {"added": len(rows), "updated": 0, "removed": 0, "unchanged": 0}

        doc_type = doc.document_type
        added = 0
        updated = 0
        removed = 0
        unchanged = 0

        if doc_type == "Students":
            existing = {s.student_code: s for s in db.query(Student).all()}
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
            existing = {c.company_code: c for c in db.query(Company).all()}
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
            existing = {f"{p.company_id}_{p.panel_code}": p for p in db.query(Panel).all()}
            incoming_codes = set()
            for idx, r in enumerate(rows, start=1):
                p_code = get_field(r, "panel_code", "panel_id", "panel_name", "panel", "panel_no", "panel_num", "panel_number", "code", "id", "name") or f"P{idx}"
                c_code = get_field(r, "company_code", "company_id", "company_name", "company", "comp_code", "comp_id", "recruiter", "firm", "corporate") or ""
                key = f"{c_code}_{p_code}" if c_code else p_code
                incoming_codes.add(key)
                if key in existing or p_code in [p.panel_code for p in existing.values()]:
                    updated += 1
                else:
                    added += 1
            removed = len(set(existing.keys()) - incoming_codes)
            unchanged = max(0, len(existing) - updated - removed)

        elif doc_type == "Rooms":
            existing = {r.room_code: r for r in db.query(Room).all()}
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
    def persist_imported_data(db: Session, document_type: str, rows: List[Dict[str, Any]]) -> int:
        persisted_count = 0
        
        if document_type == "Panels":
            all_companies = db.query(Company).order_by(Company.company_code.asc()).all()
            uploaded_codes = set()
            for idx, r in enumerate(rows, start=1):
                p_code = get_field(r, "panel_code", "panel_id", "panel_name", "panel", "panel_no", "panel_num", "panel_number", "code", "id", "name") or f"P{idx:02d}"
                uploaded_codes.add(p_code)
                c_code = get_field(r, "company_code", "company_id", "company_name", "company", "comp_code", "comp_id", "recruiter", "firm", "corporate")
                interviewers = get_field(r, "interviewer_names", "interviewer_name", "interviewers", "interviewer", "members", "names", "panelists") or f"Panel {p_code}"
                
                comp = None
                if c_code:
                    comp = db.query(Company).filter((Company.company_code.ilike(c_code)) | (Company.id == c_code) | (Company.name.ilike(c_code))).first()
                if not comp and all_companies:
                    comp = all_companies[(idx - 1) % len(all_companies)]
                
                if comp:
                    panel = db.query(Panel).filter(Panel.panel_code == p_code).first()
                    if panel:
                        panel.interviewer_names = interviewers
                        panel.company_id = comp.id
                    else:
                        panel = Panel(
                            id=str(uuid.uuid4()),
                            company_id=comp.id,
                            panel_code=p_code,
                            interviewer_names=interviewers,
                            is_active=True
                        )
                        db.add(panel)
                    persisted_count += 1
            if uploaded_codes:
                db.query(Panel).filter(Panel.panel_code.notin_(uploaded_codes)).delete(synchronize_session=False)

        elif document_type == "Rooms":
            uploaded_codes = set()
            for idx, r in enumerate(rows, start=1):
                r_code = get_field(r, "room_code", "room_id", "room", "name", "room_name") or f"R{idx:02d}"
                uploaded_codes.add(r_code)
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

                room = db.query(Room).filter(Room.room_code == r_code).first()
                if room:
                    room.building = building
                    room.floor = floor_val
                    room.capacity = cap_val
                else:
                    room = Room(
                        id=str(uuid.uuid4()),
                        room_code=r_code,
                        building=building,
                        floor=floor_val,
                        capacity=cap_val,
                        is_active=True
                    )
                    db.add(room)
                persisted_count += 1
            if uploaded_codes:
                db.query(Room).filter(Room.room_code.notin_(uploaded_codes)).delete(synchronize_session=False)

        elif document_type == "Companies":
            uploaded_codes = set()
            for idx, r in enumerate(rows, start=1):
                c_code = get_field(r, "company_id", "company_code", "company_key", "id", "code") or f"C{idx:02d}"
                uploaded_codes.add(c_code)
                c_name = get_field(r, "company_name", "name", "title") or f"Company {c_code}"
                industry = get_field(r, "industry", "sector", "domain") or "Technology"
                email = get_field(r, "email", "contact_email", "hr_email", "email_address") or f"hr_{c_code.lower()}@example.com"
                
                comp = db.query(Company).filter((Company.company_code == c_code) | (Company.name == c_name)).first()
                if comp:
                    comp.name = c_name
                    comp.industry = industry
                else:
                    user = db.query(User).filter(User.email == email).first()
                    if not user:
                        user = User(
                            id=str(uuid.uuid4()),
                            email=email,
                            role="COMPANY",
                            hashed_password="hash"
                        )
                        db.add(user)
                        db.flush()
                    comp = Company(
                        id=str(uuid.uuid4()),
                        user_id=user.id,
                        company_code=c_code,
                        name=c_name,
                        industry=industry,
                        priority_tier=1
                    )
                    db.add(comp)
                persisted_count += 1
            if uploaded_codes:
                db.query(Company).filter(Company.company_code.notin_(uploaded_codes)).delete(synchronize_session=False)

        elif document_type == "Students":
            uploaded_codes = set()
            for idx, r in enumerate(rows, start=1):
                s_code = get_field(r, "student_code", "student_id", "usn", "roll_no", "id", "code") or f"S{idx:04d}"
                uploaded_codes.add(s_code)
                s_name = get_field(r, "name", "student_name", "full_name") or f"Student {s_code}"
                s_email = get_field(r, "email", "student_email", "email_address") or f"{s_code.lower()}@univ.edu"
                branch = get_field(r, "branch", "department", "stream", "course") or "CSE"
                cgpa_str = get_field(r, "cgpa", "gpa", "score") or "7.5"
                try:
                    cgpa_val = float(cgpa_str)
                except ValueError:
                    cgpa_val = 7.5

                stud = db.query(Student).filter((Student.student_code == s_code) | (Student.email == s_email)).first()
                if stud:
                    stud.name = s_name
                    stud.branch = branch
                    stud.cgpa = cgpa_val
                else:
                    user = db.query(User).filter(User.email == s_email).first()
                    if not user:
                        user = User(
                            id=str(uuid.uuid4()),
                            email=s_email,
                            role="STUDENT",
                            hashed_password="hash"
                        )
                        db.add(user)
                        db.flush()
                    stud = Student(
                        id=str(uuid.uuid4()),
                        user_id=user.id,
                        student_code=s_code,
                        name=s_name,
                        email=s_email,
                        branch=branch,
                        cgpa=cgpa_val
                    )
                    db.add(stud)
                persisted_count += 1
            if uploaded_codes:
                db.query(Student).filter(Student.student_code.notin_(uploaded_codes)).delete(synchronize_session=False)

        elif document_type == "Shortlists":
            for idx, r in enumerate(rows, start=1):
                c_code = get_field(r, "company_code", "company_id", "company", "comp_code", "comp_id")
                s_code = get_field(r, "student_code", "student_id", "student", "usn", "roll_no")
                rank_str = get_field(r, "preference_rank", "rank", "priority") or "1"
                try:
                    rank_val = int(rank_str)
                except ValueError:
                    rank_val = 1

                if c_code and s_code:
                    comp = db.query(Company).filter((Company.company_code == c_code) | (Company.id == c_code)).first()
                    stud = db.query(Student).filter((Student.student_code == s_code) | (Student.id == s_code)).first()
                    if comp and stud:
                        sh = db.query(Shortlist).filter(Shortlist.company_id == comp.id, Shortlist.student_id == stud.id).first()
                        if not sh:
                            sh = Shortlist(
                                id=str(uuid.uuid4()),
                                company_id=comp.id,
                                student_id=stud.id,
                                preference_rank=rank_val,
                                status="SHORTLISTED"
                            )
                            db.add(sh)
                            persisted_count += 1

        db.flush()
        return persisted_count
