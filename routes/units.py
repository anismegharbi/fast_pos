from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Unit, User
from schemas import UnitCreate, UnitOut, UnitUpdate

router = APIRouter(tags=["units"])


def _get_unit(db: Session, license_id: int, unit_id: int) -> Unit:
    unit = db.query(Unit).filter(Unit.id == unit_id, Unit.license_id == license_id).first()
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    return unit


@router.get("/units", response_model=list[UnitOut])
def list_units(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Unit).filter(Unit.license_id == current_user.license_id).order_by(Unit.sort_order, Unit.name).all()


@router.post("/units", response_model=UnitOut)
def create_unit(payload: UnitCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    unit = Unit(**payload.model_dump(), license_id=current_user.license_id)
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.get("/units/{unit_id}", response_model=UnitOut)
def get_unit(unit_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_unit(db, current_user.license_id, unit_id)


@router.put("/units/{unit_id}", response_model=UnitOut)
def update_unit(
    unit_id: int,
    payload: UnitUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    unit = _get_unit(db, current_user.license_id, unit_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(unit, key, value)
    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/units/{unit_id}")
def delete_unit(unit_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    unit = _get_unit(db, current_user.license_id, unit_id)
    db.delete(unit)
    db.commit()
    return {"success": True}
