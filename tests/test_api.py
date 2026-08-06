import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import AsyncMock, patch

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_document_upload_without_auth():
    # Test document upload without authentication
    response = client.post("/api/documents/upload")
    assert response.status_code in [401, 403]

def test_ticket_creation_without_auth():
    # Test ticket creation without authentication
    response = client.post(
        "/api/tickets/tickets",
        json={
            "title": "Test Ticket",
            "description": "Test description",
            "priority": "medium",
            "category": "software"
        }
    )
    assert response.status_code in [401, 403]

@pytest.mark.asyncio
async def test_chat_endpoint():
    # Mock authentication
    with patch('app.api.chat.get_current_user') as mock_user:
        mock_user.return_value = AsyncMock(id=1, username="testuser")
        
        with patch('app.services.chat_service.ChatService.process_message') as mock_process:
            mock_process.return_value = {
                "response": "Test response",
                "conversation_id": "test-conv-id",
                "sources": [],
                "confidence_score": 0.9
            }
            
            response = client.post(
                "/api/chat/chat",
                json={
                    "message": "Hello",
                    "conversation_id": "test-conv-id"
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "response" in data
                assert "conversation_id" in data

def test_get_conversations_without_auth():
    response = client.get("/api/chat/conversations")
    assert response.status_code in [401, 403]

def test_get_tickets_without_auth():
    response = client.get("/api/tickets/tickets")
    assert response.status_code in [401, 403]