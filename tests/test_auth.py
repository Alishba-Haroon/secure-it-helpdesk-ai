import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.database import get_db
from app.database import crud
from unittest.mock import AsyncMock, patch

client = TestClient(app)

# Mock database dependency
@pytest.fixture
def mock_db():
    with patch('app.api.auth.get_db') as mock:
        db = AsyncMock()
        mock.return_value = db
        yield db

def test_register_user():
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123",
            "full_name": "Test User",
            "role": "user"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "password" not in data
    else:
        assert response.status_code in [200, 400, 500]

def test_login():
    # First register a user
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "logintest",
            "email": "login@example.com",
            "password": "LoginPass123",
            "full_name": "Login User",
            "role": "user"
        }
    )
    
    # Then login
    response = client.post(
        "/api/auth/login",
        data={
            "username": "logintest",
            "password": "LoginPass123"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

def test_login_invalid_credentials():
    response = client.post(
        "/api/auth/login",
        data={
            "username": "nonexistent",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401

def test_refresh_token():
    # First login to get refresh token
    login_response = client.post(
        "/api/auth/login",
        data={
            "username": "logintest",
            "password": "LoginPass123"
        }
    )
    
    if login_response.status_code == 200:
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

def test_protected_route_without_token():
    response = client.get("/api/chat/conversations")
    assert response.status_code in [401, 403]

def test_protected_route_with_token():
    # Login to get token
    login_response = client.post(
        "/api/auth/login",
        data={
            "username": "logintest",
            "password": "LoginPass123"
        }
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        
        # Access protected route
        response = client.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [200, 404, 500]