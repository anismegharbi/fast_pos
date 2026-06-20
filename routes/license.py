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
        base_dict = res.model_dump(exclude={"data", "result"})
        res.data = base_dict
        res.result = {**base_dict, "data": base_dict}
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
        base_dict = res.model_dump(exclude={"data", "result"})
        res.data = base_dict
        res.result = {**base_dict, "data": base_dict}
        return res

    # Automatically bind or update to the requesting device_id to avoid lock issues
    if license_obj.device_id != payload.deviceId:
        license_obj.device_id = payload.deviceId
        db.commit()
        db.refresh(license_obj)

    license_info = _license_payload(license_obj)
    payload_data = {
        "plan": "active",
        "offlineAllowed": license_obj.offline_allowed,
        "daysLeft": license_info.daysLeft,
        "storeName": license_info.storeName,
    }
    res = LicenseResponse(
        success=True,
        license=license_info,
        payload=payload_data,
        valid=license_info.valid,
        status=license_info.status,
        storeName=license_info.storeName,
        expiresAt=license_info.expiresAt,
        daysLeft=license_info.daysLeft,
        plan=payload_data["plan"],
        offlineAllowed=payload_data["offlineAllowed"],
    )
    base_dict = res.model_dump(exclude={"data", "result"})
    res.data = base_dict
    res.result = {**base_dict, "data": base_dict}
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
