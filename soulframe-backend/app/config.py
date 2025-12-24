from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://smartframe:smartframe@db:5432/smartframe"
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # App
    WEB_BASE_URL: str = "http://localhost:3000"
    MEDIA_STORAGE_PATH: str = "./data/media"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_MIME_TYPES: str = "image/jpeg,image/png,image/gif,image/webp,video/mp4,video/quicktime"
    
    # Pairing
    PAIRING_CODE_LENGTH: int = 8
    PAIRING_CODE_EXPIRY_MINUTES: int = 10
    
    @property
    def allowed_mime_types_list(self) -> List[str]:
        return [mt.strip() for mt in self.ALLOWED_MIME_TYPES.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    class Config:
        env_file = ".env"


settings = Settings()