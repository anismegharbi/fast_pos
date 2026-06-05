from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import create_access_token, ensure_license_valid, get_current_user, hash_password, require_manager_or_admin, verify_password
from database import get_db
from models import License, User, UserRole
from schemas import LoginRequest, PinLoginRequest, RegisterRequest, TokenResponse, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(token=create_access_token(user), user=UserOut.model_validate(user))


def _get_user_for_license(db: Session, license_id: int, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id, User.license_id == license_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    ensure_license_valid(user.license)
    return _token_response(user)


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.license_key == payload.license_key).first()
    ensure_license_valid(license_obj)

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    existing_license_users = db.query(User).filter(User.license_id == license_obj.id).count()
    role = UserRole.admin if existing_license_users == 0 else UserRole.cashier
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role=role,
        license_id=license_obj.id,
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/pin-login", response_model=TokenResponse)
def pin_login(payload: PinLoginRequest, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.pin == payload.pin, User.active.is_(True)).all()
    valid_users = [user for user in users if user.license and user.license.status.value == "active"]
    if len(valid_users) == 0:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN")
    if len(valid_users) > 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PIN is ambiguous; use email login")
    ensure_license_valid(valid_users[0].license)
    return _token_response(valid_users[0])


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserOut])
def list_users(
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).filter(User.license_id == current_user.license_id).order_by(User.id).all()


@router.post("/users", response_model=UserOut)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists for this license")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role=payload.role,
        pin=payload.pin,
        active=payload.active,
        license_id=current_user.license_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    return _get_user_for_license(db, current_user.license_id, user_id)


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    user = _get_user_for_license(db, current_user.license_id, user_id)
    data = payload.model_dump(exclude_unset=True)
    if "email" in data:
        existing = db.query(User).filter(User.email == data["email"], User.id != user_id).first()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    password = data.pop("password", None)
    if password:
        user.password_hash = hash_password(password)
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db),
):
    user = _get_user_for_license(db, current_user.license_id, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own user")
    db.delete(user)
    db.commit()
    return {"success": True}
