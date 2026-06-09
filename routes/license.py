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
        res = LicenseResponse(success=False, error="License not found or suspended")
        res.data = res.model_dump(exclude={"data", "result"})
        res.result = res.data
        return res

    expires_at = license_obj.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if license_obj.status != LicenseStatus.active or expires_at <= datetime.now(timezone.utc):
        if expires_at <= datetime.now(timezone.utc) and license_obj.status != LicenseStatus.expired:
            license_obj.status = LicenseStatus.expired
            db.commit()
            db.refresh(license_obj)
        res = LicenseResponse(success=False, error="License not found or suspended")
        res.data = res.model_dump(exclude={"data", "result"})
        res.result = res.data
        return res

    if license_obj.device_id is None:
        license_obj.device_id = payload.deviceId
        db.commit()
        db.refresh(license_obj)
    elif license_obj.device_id != payload.deviceId:
        res = LicenseResponse(success=False, error="License is already linked to another device")
        res.data = res.model_dump(exclude={"data", "result"})
        res.result = res.data
        return res

    res = LicenseResponse(success=True, license=_license_payload(license_obj))
    res.data = res.model_dump(exclude={"data", "result"})
    res.result = res.data
    return res


@router.post("/activate")
def activate(payload: LicenseActivateRequest, db: Session = Depends(get_db)):
    from fastapi.responses import JSONResponse
    res = _activate_or_verify(payload, db)
    return JSONResponse(content=res.model_dump())


@router.post("/verify")
def verify(payload: LicenseActivateRequest, db: Session = Depends(get_db)):
    from fastapi.responses import JSONResponse
    res = _activate_or_verify(payload, db)
    return JSONResponse(content=res.model_dump())


@router.get("/announcements", response_model=AnnouncementResponse)
def announcements():
    return AnnouncementResponse(announcements=[])
