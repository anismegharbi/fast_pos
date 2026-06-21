from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import init_db
from routes import admin, auth, customers, debts, expenses, inventory, license, products, purchases, sales, suppliers, units


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Voilà POS Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(status_code=exc.status_code, content={"error": message, "code": exc.status_code})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "Validation error", "code": 422, "details": exc.errors()})


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


app.include_router(license.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(sales.router)
app.include_router(customers.router)
app.include_router(debts.router)
app.include_router(inventory.router)
app.include_router(purchases.router)
app.include_router(suppliers.router)
app.include_router(expenses.router)
app.include_router(units.router)
app.include_router(admin.router)


# ── Fallback: compiled app POSTs to root "/" of each Cloud Function URL ──
# The original app uses separate Cloud-Function URLs per endpoint
# (licenseActivateUrl, licenseVerifyUrl) and POSTs to "/" of each one.
# Since we consolidated them into a single server, POST / = activate/verify.
@app.post("/")
async def root_activate(
    request: Request,
    db: license.Session = Depends(license.get_db),
):
    import json as _json
    from license_token import build_license_token

    raw_body = await request.body()
    print("RAW REQUEST BODY:", raw_body)

    try:
        payload_data = _json.loads(raw_body)
    except Exception as e:
        print("Failed to parse JSON:", e)
        raise HTTPException(status_code=400, detail="Invalid request body")

    license_key = payload_data.get("licenseKey", "").strip().upper()
    device_id = payload_data.get("deviceId", "")

    if not license_key or not device_id:
        raise HTTPException(status_code=400, detail="Missing licenseKey or deviceId")

    from models import License as LicenseModel, LicenseStatus
    from datetime import datetime, timezone

    license_obj = db.query(LicenseModel).filter(LicenseModel.license_key == license_key).first()

    if license_obj is None:
        print(f"License not found: {license_key}")
        return JSONResponse(status_code=200, content={"error": "License not found"})

    expires_at = license_obj.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    # Check expiry
    if expires_at <= datetime.now(timezone.utc):
        if license_obj.status != LicenseStatus.expired:
            license_obj.status = LicenseStatus.expired
            db.commit()
            db.refresh(license_obj)

    # Auto-bind device (no device lock)
    if license_obj.device_id != device_id:
        license_obj.device_id = device_id
        db.commit()
        db.refresh(license_obj)

    # Build the signed token response
    token_response = build_license_token(
        license_key=license_obj.license_key,
        device_id=device_id,
        status=license_obj.status.value,   # "active", "expired", "suspended"
        expires_at=expires_at,
        plan="pro",
        features=[],
        max_devices=1,
        offline_allowed=True,
    )

    print("RAW RESPONSE:", _json.dumps(token_response))
    return JSONResponse(content=token_response)

