from app.database import engine, SessionLocal, Base
from app.models.models import Device
import uuid


def ensure_tables():
    Base.metadata.create_all(bind=engine)


def create_device(token: str, name: str = "test-agent"):
    db = SessionLocal()
    try:
        # Check existing
        existing = db.query(Device).filter(Device.device_token == token).first()
        if existing:
            print("Device already exists:", existing.id)
            return

        d = Device(
            name=name,
            device_token=token,
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        print("Created device:", d.id)
    finally:
        db.close()


if __name__ == "__main__":
    ensure_tables()
    create_device("test-device-token-1234", "local-test-agent")
