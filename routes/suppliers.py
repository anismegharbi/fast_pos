from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Supplier, SupplierDebt, User
from schemas import SupplierCreate, SupplierDebtCreate, SupplierDebtOut, SupplierDebtUpdate, SupplierOut, SupplierUpdate

router = APIRouter(tags=["suppliers"])


def _get_supplier(db: Session, license_id: int, supplier_id: int) -> Supplier:
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id, Supplier.license_id == license_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier


def _get_supplier_debt(db: Session, license_id: int, debt_id: int) -> SupplierDebt:
    debt = db.query(SupplierDebt).filter(SupplierDebt.id == debt_id, SupplierDebt.license_id == license_id).first()
    if debt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier debt not found")
    return debt


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Supplier).filter(Supplier.license_id == current_user.license_id).order_by(Supplier.name).all()


@router.post("/suppliers", response_model=SupplierOut)
def create_supplier(
    payload: SupplierCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    supplier = Supplier(**payload.model_dump(), license_id=current_user.license_id)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_supplier(db, current_user.license_id, supplier_id)


@router.put("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    supplier = _get_supplier(db, current_user.license_id, supplier_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/suppliers/{supplier_id}")
def delete_supplier(supplier_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    supplier = _get_supplier(db, current_user.license_id, supplier_id)
    db.delete(supplier)
    db.commit()
    return {"success": True}


@router.get("/supplier-debts", response_model=list[SupplierDebtOut])
def list_supplier_debts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(SupplierDebt).filter(SupplierDebt.license_id == current_user.license_id).order_by(SupplierDebt.created_at.desc()).all()


@router.post("/supplier-debts", response_model=SupplierDebtOut)
def create_supplier_debt(
    payload: SupplierDebtCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    debt = SupplierDebt(**payload.model_dump(), license_id=current_user.license_id)
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return debt


@router.get("/supplier-debts/by-purchase/{purchase_id}", response_model=SupplierDebtOut)
def supplier_debt_by_purchase(
    purchase_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    debt = (
        db.query(SupplierDebt)
        .filter(SupplierDebt.license_id == current_user.license_id, SupplierDebt.purchase_id == purchase_id)
        .first()
    )
    if debt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier debt not found")
    return debt


@router.get("/supplier-debts/{debt_id}", response_model=SupplierDebtOut)
def get_supplier_debt(debt_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_supplier_debt(db, current_user.license_id, debt_id)


@router.put("/supplier-debts/{debt_id}", response_model=SupplierDebtOut)
def update_supplier_debt(
    debt_id: int,
    payload: SupplierDebtUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    debt = _get_supplier_debt(db, current_user.license_id, debt_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(debt, key, value)
    db.commit()
    db.refresh(debt)
    return debt


@router.delete("/supplier-debts/{debt_id}")
def delete_supplier_debt(debt_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    debt = _get_supplier_debt(db, current_user.license_id, debt_id)
    db.delete(debt)
    db.commit()
    return {"success": True}
