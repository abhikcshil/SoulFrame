from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.models import models  # noqa: F401
from app.routers import auth, devices, device_agent, media, playlists

app = FastAPI(
    title="Smart Frame API",
    description="Backend API for smart motion art frame",
    version="1.0.0"
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(device_agent.router)
app.include_router(media.router)
app.include_router(playlists.router)


@app.get("/")
async def root():
    return {"message": "Smart Frame API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
