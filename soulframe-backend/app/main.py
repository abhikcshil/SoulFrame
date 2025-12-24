from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, devices, device_agent, media, playlists

app = FastAPI(
    title="Smart Frame API",
    description="Backend API for smart motion art frame",
    version="1.0.0"
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173", "http://127.0.0.1:5173"],
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


### data/media/.gitkeep

# This file ensures the media directory is created in git