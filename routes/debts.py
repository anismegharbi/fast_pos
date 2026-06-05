from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Debt, DebtPayment, User
from schemas import DebtCreate, DebtOut, DebtPaymentCreate, DebtPaymentOut, DebtUpdate

router = APIRouter(tags=["debts"])


def _get_debt(db: Session, license_id: int, debt_id: int) -> Debt:
    debt = db.query(Debt).filter(Debt.id == debt_id, Debt.license_id == license_id).first()
    if debt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")
    return debt


@router.get("/debts", response_model=list[DebtOut])
def list_debts(
    customerId: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Debt).filter(Debt.license_id == current_user.license_id)
    if customerId is not None:
        query = query.filter(Debt.customer_id == customerId)
    return query.order_by(Debt.created_at.desc()).all()


@router.post("/debts", response_model=DebtOut)
def create_debt(payload: DebtCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    debt = Debt(**payload.model_dump(), license_id=current_user.license_id)
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return debt


@router.get("/debts/balance/{customer_id}")
def customer_debt_balance(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    balance = (
        db.query(func.coalesce(func.sum(Debt.amount - Debt.paid), 0))
        .filter(Debt.license_id == current_user.license_id, Debt.customer_id == customer_id)
        .scalar()
    )
    return {"customerId": customer_id, "balance": float(balance or 0)}


@router.get("/debts/{debt_id}", response_model=DebtOut)
def get_debt(debt_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_debt(db, current_user.license_id, debt_id)


@router.put("/debts/{debt_id}", response_model=DebtOut)
def update_debt(
    debt_id: int,
    payload: DebtUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    debt = _get_debt(db, current_user.license_id, debt_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(debt, key, value)
    db.commit()
    db.refresh(debt)
    return debt


@router.delete("/debts/{debt_id}")
def delete_debt(debt_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    debt = _get_debt(db, current_user.license_id, debt_id)
    db.delete(debt)
    db.commit()
    return {"success": True}


@router.post("/payments", response_model=DebtPaymentOut)
def create_payment(
    payload: DebtPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    debt = _get_debt(db, current_user.license_id, payload.debt_id)
    payment = DebtPayment(**payload.model_dump(), license_id=current_user.license_id)
    debt.paid = (debt.paid or 0) + payload.amount
    if debt.paid >= debt.amount:
        debt.status = "paid"
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment
