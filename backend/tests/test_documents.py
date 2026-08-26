import pytest
import io
from app.services.document_service import DocumentService

def test_document_parsing_and_category_detection():
    csv_content = b"Name,Email,Branch,CGPA\nAarav,aarav@univ.edu,CSE,8.72\nRiya,riya@univ.edu,ECE,9.01\n"
    cols, rows = DocumentService.parse_file_content("students_2026.csv", csv_content)
    
    assert cols == ["Name", "Email", "Branch", "CGPA"]
    assert len(rows) == 2
    assert rows[0]["Name"] == "Aarav"

    cat, conf = DocumentService.detect_category(cols, "students_2026.csv")
    assert cat == "Students"
    assert conf >= 0.70

def test_companies_csv_validation_success(db_session):
    """
    Validates the exact 4 company records from the user prompt:
    C001 TechNova software tech.hr@example.com 2026-08-26 09:00
    C002 DataSphere data_ai data.hr@example.com 2026-08-26 09:00
    C003 CloudPeak cloud cloud.hr@example.com 2026-08-26 10:00
    C004 FinEdge fintech finance.hr@example.com 2026-08-26 09:00
    """
    csv_content = (
        "company_id,company_name,industry,email,interview_date,available_from\n"
        "C001,TechNova,software,tech.hr@example.com,2026-08-26,09:00\n"
        "C002,DataSphere,data_ai,data.hr@example.com,2026-08-26,09:00\n"
        "C003,CloudPeak,cloud,cloud.hr@example.com,2026-08-26,10:00\n"
        "C004,FinEdge,fintech,finance.hr@example.com,2026-08-26,09:00\n"
    ).encode("utf-8")

    cols, rows = DocumentService.parse_file_content("companies.csv", csv_content)
    cat, conf = DocumentService.detect_category(cols, "companies.csv")
    assert cat == "Companies"
    assert conf >= 0.70

    res = DocumentService.validate_document_data(db_session, cat, cols, rows)
    assert res["total_rows"] == 4
    assert res["valid_count"] == 4
    assert res["warning_count"] == 0
    assert res["error_count"] == 0
    assert len(res["errors"]) == 0

def test_panels_csv_multi_company_validation(db_session):
    """
    Verifies that panels.csv with multiple companies sharing panel codes (P1, P2...) is valid.
    """
    csv_content = (
        "panel_code,company_code,interviewer_names\n"
        "P1,C001,Dr. Alice\n"
        "P2,C001,Dr. Bob\n"
        "P1,C002,Prof. Charlie\n"
        "P2,C002,Prof. David\n"
    ).encode("utf-8")

    cols, rows = DocumentService.parse_file_content("panels.csv", csv_content)
    cat, conf = DocumentService.detect_category(cols, "panels.csv")
    assert cat == "Panels"

    res = DocumentService.validate_document_data(db_session, cat, cols, rows)
    assert res["total_rows"] == 4
    assert res["valid_count"] == 4
    assert res["error_count"] == 0

def test_all_dataset_schemas_validation(db_session):
    # 1. Students
    stud_csv = b"student_code,name,email,branch,cgpa\nS001,Alice,alice@univ.edu,CSE,9.1\nS002,Bob,bob@univ.edu,ECE,8.5\n"
    cols, rows = DocumentService.parse_file_content("students.csv", stud_csv)
    res = DocumentService.validate_document_data(db_session, "Students", cols, rows)
    assert res["total_rows"] == 2
    assert res["valid_count"] == 2
    assert res["error_count"] == 0

    # 2. Shortlists
    short_csv = b"company_code,student_code,preference_rank\nC001,S001,1\nC002,S002,2\n"
    cols, rows = DocumentService.parse_file_content("shortlists.csv", short_csv)
    res = DocumentService.validate_document_data(db_session, "Shortlists", cols, rows)
    assert res["total_rows"] == 2
    assert res["valid_count"] == 2
    assert res["error_count"] == 0

    # 3. Rooms
    rooms_csv = b"room_code,building,floor,capacity\nR101,Block A,1,30\nR102,Block B,2,40\n"
    cols, rows = DocumentService.parse_file_content("rooms.csv", rooms_csv)
    res = DocumentService.validate_document_data(db_session, "Rooms", cols, rows)
    assert res["total_rows"] == 2
    assert res["valid_count"] == 2
    assert res["error_count"] == 0

    # 4. Panels
    panels_csv = b"panel_code,company_code,interviewer_names\nP01,C001,John Doe\nP02,C002,Jane Smith\n"
    cols, rows = DocumentService.parse_file_content("panels.csv", panels_csv)
    res = DocumentService.validate_document_data(db_session, "Panels", cols, rows)
    assert res["total_rows"] == 2
    assert res["valid_count"] == 2
    assert res["error_count"] == 0

    # 5. Company Availability
    comp_avail_csv = b"company_code,available_from,available_to\nC001,09:00,17:00\n"
    cols, rows = DocumentService.parse_file_content("company_availability.csv", comp_avail_csv)
    res = DocumentService.validate_document_data(db_session, "Company Availability", cols, rows)
    assert res["total_rows"] == 1
    assert res["valid_count"] == 1
    assert res["error_count"] == 0

    # 6. Student Availability
    stud_avail_csv = b"student_code,available_from,available_to\nS001,09:00,12:00\n"
    cols, rows = DocumentService.parse_file_content("student_availability.csv", stud_avail_csv)
    res = DocumentService.validate_document_data(db_session, "Student Availability", cols, rows)
    assert res["total_rows"] == 1
    assert res["valid_count"] == 1
    assert res["error_count"] == 0

def test_company_validation_error_reporting(db_session):
    bad_csv = (
        "company_id,company_name,email,interview_date,available_from,interview_duration_minutes\n"
        ",,invalid-email,2026/08/26,25:00,-10\n"
    ).encode("utf-8")
    cols, rows = DocumentService.parse_file_content("companies.csv", bad_csv)
    res = DocumentService.validate_document_data(db_session, "Companies", cols, rows)
    
    assert res["total_rows"] == 1
    assert res["error_count"] == 1
    assert len(res["errors"]) >= 4
