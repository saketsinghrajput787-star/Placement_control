import pytest
import io
from app.models.placement_session import PlacementSession
from app.models.student import Student
from app.models.company import Company
from app.models.resource import Room, Panel
from app.models.schedule import Schedule, ScheduleVersion, Interview
from app.core.security import create_access_token

def get_auth_headers(user, session_id=None):
    token = create_access_token(user.id, role=user.role)
    h = {"Authorization": f"Bearer {token}"}
    if session_id:
        h["X-Placement-Session-ID"] = session_id
    return h

def test_mandatory_prevalidation_blocking_empty_pools(client, db_session, sample_data):
    """TEST 1: Blocking CP-SAT if required pools (students, companies, shortlists, rooms, panels) are empty."""
    sess = PlacementSession(id="empty-session-1", name="Empty Session 1")
    db_session.add(sess)
    db_session.commit()

    headers = get_auth_headers(sample_data["coordinator_user"], session_id=sess.id)
    res = client.post("/api/schedule/generate", headers=headers, json={"max_solve_time_seconds": 5})
    
    assert res.status_code == 400
    data = res.json()
    assert "detail" in data
    err_detail = str(data["detail"])
    assert "Cannot generate schedule" in err_detail or "empty" in err_detail.lower() or "requires" in err_detail.lower() or "BLOCKED" in err_detail

def test_session_isolation_data_leakage(client, db_session, sample_data):
    """TEST 2: Verify data in Session A is not visible in Session B."""
    sess_a = sample_data["session"]
    
    sess_b = PlacementSession(id="session-b-id", name="Session B")
    db_session.add(sess_b)
    db_session.commit()

    headers_a = get_auth_headers(sample_data["coordinator_user"], session_id=sess_a.id)
    headers_b = get_auth_headers(sample_data["coordinator_user"], session_id=sess_b.id)

    res_a = client.get("/api/students", headers=headers_a)
    assert res_a.status_code == 200
    students_a = res_a.json()
    assert len(students_a) >= 1

    res_b = client.get("/api/students", headers=headers_b)
    assert res_b.status_code == 200
    students_b = res_b.json()
    assert len(students_b) == 0

def test_ai_copilot_empty_session_grounding(client, db_session, sample_data):
    """TEST 5: AI Copilot returns 'No placement data has been imported yet.' on empty session."""
    sess = PlacementSession(id="ai-empty-session", name="AI Empty Session")
    db_session.add(sess)
    db_session.commit()

    headers = get_auth_headers(sample_data["coordinator_user"], session_id=sess.id)
    res = client.post("/api/ai/copilot/query", headers=headers, json={"query": "How many interviews are scheduled?"})
    
    assert res.status_code == 200
    data = res.json()
    assert "No placement data has been imported yet" in data["answer"]

def test_dataset_a_to_b_replacement_acceptance_test(client, db_session, sample_data):
    """TEST 3: Dataset A -> Dataset B replacement test (zero data leakage & baseline invalidation)."""
    sess = PlacementSession(id="replace-test-session", name="Replace Test Session")
    db_session.add(sess)
    db_session.commit()

    headers = get_auth_headers(sample_data["coordinator_user"], session_id=sess.id)

    csv_a = "student_code,name,email,branch,cgpa\nSA001,Alice A,alice@a.com,CSE,9.0\nSA002,Bob A,bob@a.com,ECE,8.5"
    file_a = ("students_a.csv", csv_a.encode('utf-8'), "text/csv")
    
    upload_res_a = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": file_a},
        data={"document_type": "Students", "uploaded_by": "Coordinator"}
    )
    assert upload_res_a.status_code == 200
    doc_id_a = upload_res_a.json()["document_id"]

    import_res_a = client.post(f"/api/documents/{doc_id_a}/import?import_mode=REPLACE", headers=headers)
    assert import_res_a.status_code == 200

    students_in_a = db_session.query(Student).filter(Student.placement_session_id == sess.id).all()
    assert len(students_in_a) == 2
    assert {s.student_code for s in students_in_a} == {"SA001", "SA002"}

    csv_b = "student_code,name,email,branch,cgpa\nSB001,Charlie B,charlie@b.com,ME,8.0\nSB002,David B,david@b.com,EEE,7.5\nSB003,Eve B,eve@b.com,CSE,9.2"
    file_b = ("students_b.csv", csv_b.encode('utf-8'), "text/csv")

    upload_res_b = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": file_b},
        data={"document_type": "Students", "uploaded_by": "Coordinator"}
    )
    assert upload_res_b.status_code == 200
    doc_id_b = upload_res_b.json()["document_id"]

    import_res_b = client.post(f"/api/documents/{doc_id_b}/import?import_mode=REPLACE", headers=headers)
    assert import_res_b.status_code == 200

    students_in_b = db_session.query(Student).filter(Student.placement_session_id == sess.id).all()
    assert len(students_in_b) == 3
    assert {s.student_code for s in students_in_b} == {"SB001", "SB002", "SB003"}
    assert not any(s.student_code.startswith("SA") for s in students_in_b)

def test_append_import_mode(client, db_session, sample_data):
    """TEST 4: APPEND import mode retains existing data and adds new data."""
    sess = PlacementSession(id="append-test-session", name="Append Test Session")
    db_session.add(sess)
    db_session.commit()

    headers = get_auth_headers(sample_data["coordinator_user"], session_id=sess.id)

    csv_1 = "student_code,name,email,branch,cgpa\nS101,Student 1,s1@test.com,CSE,8.0"
    file_1 = ("s1.csv", csv_1.encode('utf-8'), "text/csv")
    up1 = client.post("/api/documents/upload", headers=headers, files={"file": file_1}, data={"document_type": "Students"})
    client.post(f"/api/documents/{up1.json()['document_id']}/import?import_mode=REPLACE", headers=headers)

    csv_2 = "student_code,name,email,branch,cgpa\nS102,Student 2,s2@test.com,ECE,8.5"
    file_2 = ("s2.csv", csv_2.encode('utf-8'), "text/csv")
    up2 = client.post("/api/documents/upload", headers=headers, files={"file": file_2}, data={"document_type": "Students"})
    client.post(f"/api/documents/{up2.json()['document_id']}/import?import_mode=APPEND", headers=headers)

    students = db_session.query(Student).filter(Student.placement_session_id == sess.id).all()
    assert len(students) == 2
    assert {s.student_code for s in students} == {"S101", "S102"}
