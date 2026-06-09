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
# Since we consolidated them into a single server, POST / = activate.
@app.post("/")
async def root_activate(
    request: Request,
    db: license.Session = Depends(license.get_db),
):
    """
    Handle the root POST request that the app sends for activation.
    We read the raw request body to log it, then pass it to the license logic.
    """
    raw_body = await request.body()
    print("RAW REQUEST BODY:", raw_body)
    
    # Parse it manually to avoid Pydantic validation errors if the app sends weird data
    try:
        import json
        payload_data = json.loads(raw_body)
        payload = license.LicenseActivateRequest(**payload_data)
    except Exception as e:
        print("Failed to parse request:", e)
        # If we can't parse, let's just return a generic error or attempt to extract what we can
        raise HTTPException(status_code=400, detail="Invalid request body")
        
    response_obj = license._activate_or_verify(payload, db)
    # Return as pure JSONResponse to force Content-Length instead of chunked encoding
    return JSONResponse(content=response_obj.model_dump())
