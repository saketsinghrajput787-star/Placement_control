import pytest
from fastapi.testclient import TestClient

def test_login_success_coordinator(client: TestClient, sample_data):
    res = client.post("/api/auth/login", json={
        "email": "test_coord@university.edu",
        "password": "admin123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "COORDINATOR"

def test_login_invalid_password(client: TestClient, sample_data):
    res = client.post("/api/auth/login", json={
        "email": "test_coord@university.edu",
        "password": "wrongpassword"
    })
    assert res.status_code == 401

def test_me_endpoint(client: TestClient, sample_data):
    login_res = client.post("/api/auth/login", json={
        "email": "test_coord@university.edu",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]
    
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "test_coord@university.edu"
    assert me_res.json()["role"] == "COORDINATOR"
