from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./local_test.db"
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # App
    WEB_BASE_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://localhost:3001"
    CORS_ORIGIN_REGEX: str = (
        r"^https?://("
        r"localhost|"
        r"127\.0\.0\.1|"
        r"0\.0\.0\.0|"
        r"\[::1\]|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
        r")(:\d+)?$"
    )
    MEDIA_STORAGE_PATH: str = "./data/media"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_MIME_TYPES: str = "image/jpeg,image/png,image/gif,image/webp,video/mp4,video/quicktime"
    
    # Pairing
    PAIRING_CODE_LENGTH: int = 8
    PAIRING_CODE_EXPIRY_MINUTES: int = 10

    # Device runtime defaults (MVP polling contract)
    DEVICE_OFFLINE_THRESHOLD_SECONDS: int = 120
    DEVICE_DEFAULT_POLL_INTERVAL_SECONDS: int = 15
    DEVICE_DEFAULT_SYNC_INTERVAL_SECONDS: int = 60
    DEVICE_DEFAULT_CACHE_MAX_BYTES: int = 1073741824  # 1GB
    DEVICE_DEFAULT_PLAYBACK_MODE: str = "sequential"
    DEVICE_DEFAULT_FALLBACK_BEHAVIOR: str = "keep_last"
    DEVICE_COMMAND_DEFAULT_EXPIRY_SECONDS: int = 300
    
    @property
    def allowed_mime_types_list(self) -> List[str]:
        return [mt.strip() for mt in self.ALLOWED_MIME_TYPES.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"


settings = Settings()
