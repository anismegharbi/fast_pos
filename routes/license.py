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


def _activate_or_verify(payload: LicenseActivateRequest, db: Session):
    from license_token import build_license_token

    license_obj = db.query(License).filter(License.license_key == payload.licenseKey).first()
    if license_obj is None:
        return None, "License not found or suspended"

    expires_at = license_obj.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if license_obj.status != LicenseStatus.active or expires_at <= datetime.now(timezone.utc):
        if expires_at <= datetime.now(timezone.utc) and license_obj.status != LicenseStatus.expired:
            license_obj.status = LicenseStatus.expired
            db.commit()
            db.refresh(license_obj)
        return None, "License not found or suspended"

    # Automatically bind or update to the requesting device_id to avoid lock issues
    if license_obj.device_id != payload.deviceId:
        license_obj.device_id = payload.deviceId
        db.commit()
        db.refresh(license_obj)

    token_response = build_license_token(
        license_key=license_obj.license_key,
        device_id=payload.deviceId,
        status=license_obj.status.value,
        expires_at=expires_at,
        plan="pro",
        features=[],
        max_devices=1,
        offline_allowed=license_obj.offline_allowed,
    )
    return token_response, None


@router.post("/activate")
def activate(payload: LicenseActivateRequest, db: Session = Depends(get_db)):
    from fastapi.responses import JSONResponse
    token, error = _activate_or_verify(payload, db)
    if error:
        return JSONResponse(status_code=200, content={"error": error})
    return JSONResponse(content=token)


@router.post("/verify")
def verify(payload: LicenseActivateRequest, db: Session = Depends(get_db)):
    from fastapi.responses import JSONResponse
    token, error = _activate_or_verify(payload, db)
    if error:
        return JSONResponse(status_code=200, content={"error": error})
    return JSONResponse(content=token)


@router.get("/announcements", response_model=AnnouncementResponse)
def announcements():
    return AnnouncementResponse(announcements=[])
