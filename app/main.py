from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import auth, chat, documents, tickets
from app.database.database import engine, Base
from app.utils.logger import logger
from contextlib import asynccontextmanager

# Define lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Secure IT Helpdesk AI...")
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down Secure IT Helpdesk AI...")
    await engine.dispose()

app = FastAPI(
    title="Secure IT Helpdesk AI",
    description="AI-powered IT helpdesk with RAG capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - HARDCODED for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])

@app.get("/")
async def root():
    return {
        "message": "Secure IT Helpdesk AI API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}