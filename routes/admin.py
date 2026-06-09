import os
import secrets
import string

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import License, User
from schemas import AdminLicenseCreate, AdminLicenseUpdate, GeneratedKeyResponse, LicenseAdminOut, UserOut

load_dotenv()

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin_secret(x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret")) -> None:
    expected = os.getenv("ADMIN_SECRET")
    if not expected:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ADMIN_SECRET is not configured")
    if x_admin_secret != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin secret")


def generate_license_key() -> str:
    alphabet = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
    return "VOILA-" + "-".join(parts)


def unique_license_key(db: Session) -> str:
    for _ in range(20):
        key = generate_license_key()
        if db.query(License).filter(License.license_key == key).first() is None:
            return key
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate a unique license key")


def _get_license(db: Session, license_id: int) -> License:
    license_obj = db.get(License, license_id)
    if license_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")
    return license_obj


@router.get("/licenses", response_model=list[LicenseAdminOut], dependencies=[Depends(require_admin_secret)])
def list_licenses(db: Session = Depends(get_db)):
    return db.query(License).order_by(License.created_at.desc()).all()


@router.post("/licenses", response_model=LicenseAdminOut, dependencies=[Depends(require_admin_secret)])
def create_license(payload: AdminLicenseCreate, db: Session = Depends(get_db)):
    key = payload.licenseKey or unique_license_key(db)

    existing = db.query(License).filter(License.license_key == key).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="License key already exists")

    license_obj = License(
        license_key=key,
        device_id=payload.deviceId,
        store_name=payload.storeName,
        owner_name=payload.ownerName,
        owner_phone=payload.ownerPhone,
        status=payload.status,
        expires_at=payload.expiresAt,
        notes=payload.notes,
    )
    db.add(license_obj)
    db.commit()
    db.refresh(license_obj)
    return license_obj


_ADMIN_FIELD_MAP = {
    "licenseKey": "license_key",
    "deviceId": "device_id",
    "storeName": "store_name",
    "ownerName": "owner_name",
    "ownerPhone": "owner_phone",
    "expiresAt": "expires_at",
}


@router.put("/licenses/{license_id}", response_model=LicenseAdminOut, dependencies=[Depends(require_admin_secret)])
def update_license(license_id: int, payload: AdminLicenseUpdate, db: Session = Depends(get_db)):
    license_obj = _get_license(db, license_id)
    data = payload.model_dump(exclude_unset=True)
    if "licenseKey" in data:
        existing = db.query(License).filter(License.license_key == data["licenseKey"], License.id != license_id).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="License key already exists")
    for key, value in data.items():
        db_key = _ADMIN_FIELD_MAP.get(key, key)
        setattr(license_obj, db_key, value)
    db.commit()
    db.refresh(license_obj)
    return license_obj


@router.delete("/licenses/{license_id}", dependencies=[Depends(require_admin_secret)])
def delete_license(license_id: int, db: Session = Depends(get_db)):
    license_obj = _get_license(db, license_id)
    db.delete(license_obj)
    db.commit()
    return {"success": True}


@router.get("/licenses/{license_id}/users", response_model=list[UserOut], dependencies=[Depends(require_admin_secret)])
def license_users(license_id: int, db: Session = Depends(get_db)):
    _get_license(db, license_id)
    return db.query(User).filter(User.license_id == license_id).order_by(User.id).all()


@router.post("/generate-key", response_model=GeneratedKeyResponse, dependencies=[Depends(require_admin_secret)])
def generate_key(db: Session = Depends(get_db)):
    return GeneratedKeyResponse(licenseKey=unique_license_key(db))
