from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends

from database import get_db
from models import License, LicenseStatus
from schemas import AnnouncementResponse, LicenseActivateRequest, LicenseInfo, LicenseResponse

router = APIRouter(tags=["license"])


def _days_left(expires_at: datetime) -> int:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return max((expires_at.date() - now.date()).days, 0)


def _license_payload(license_obj: License) -> LicenseInfo:
    expires_at = license_obj.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return LicenseInfo(
        valid=license_obj.status == LicenseStatus.active and expires_at > datetime.now(timezone.utc),
        status=license_obj.status.value,
        storeName=license_obj.store_name,
        expiresAt=expires_at.date().isoformat(),
        daysLeft=_days_left(expires_at),
    )


def _activate_or_verify(payload: LicenseActivateRequest, db: Session) -> LicenseResponse:
    license_obj = db.query(License).filter(License.license_key == payload.licenseKey).first()
    if license_obj is None:
        return LicenseResponse(success=False, error="License not found or suspended")

    expires_at = license_obj.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if license_obj.status != LicenseStatus.active or expires_at <= datetime.now(timezone.utc):
        if expires_at <= datetime.now(timezone.utc) and license_obj.status != LicenseStatus.expired:
            license_obj.status = LicenseStatus.expired
            db.commit()
            db.refresh(license_obj)
        return LicenseResponse(success=False, error="License not found or suspended")

    if license_obj.device_id is None:
        license_obj.device_id = payload.deviceId
        db.commit()
        db.refresh(license_obj)
    elif license_obj.device_id != payload.deviceId:
        return LicenseResponse(success=False, error="License is already linked to another device")

    return LicenseResponse(success=True, license=_license_payload(license_obj))


@router.post("/activate", response_model=LicenseResponse)
def activate(payload: LicenseActivateRequest, db: Session = Depends(get_db)):
    return _activate_or_verify(payload, db)


@router.post("/verify", response_model=LicenseResponse)
def verify(payload: LicenseActivateRequest, db: Session = Depends(get_db)):
    return _activate_or_verify(payload, db)


@router.get("/announcements", response_model=AnnouncementResponse)
def announcements():
    return AnnouncementResponse(announcements=[])
