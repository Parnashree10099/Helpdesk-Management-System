from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_home_page():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Helpdesk Management System API is working!"
    }
def test_get_tickets_without_login():
    response = client.get("/api/tickets/")

    assert response.status_code == 401
def test_normal_user_cannot_access_audit_logs():
    # Login as a normal user
    login_response = client.post(
        "/api/auth/login",
        data={
            "username": "demouser@example.com",
            "password": "TempReset2026!Secure"
        }
    )

    assert login_response.status_code == 200

    # Get the access token
    token = login_response.json()["access_token"]

    # Try accessing admin audit logs
    response = client.get(
        "/api/admin/audit-logs",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403

def test_admin_can_access_audit_logs():
    # Login as an admin
    login_response = client.post(
        "/api/auth/login",
        data={
            "username": "demouser2@example.com",
            "password": "DemoPass123!"
        }
    )

    assert login_response.status_code == 200

    # Get the admin's access token
    token = login_response.json()["access_token"]

    # Access the admin audit logs
    response = client.get(
        "/api/admin/audit-logs",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200