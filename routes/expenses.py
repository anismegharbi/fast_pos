from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Expense, User
from schemas import ExpenseCreate, ExpenseOut, ExpenseUpdate

router = APIRouter(tags=["expenses"])


def _get_expense(db: Session, license_id: int, expense_id: int) -> Expense:
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.license_id == license_id).first()
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Expense).filter(Expense.license_id == current_user.license_id).order_by(Expense.created_at.desc()).all()


@router.post("/expenses", response_model=ExpenseOut)
def create_expense(payload: ExpenseCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    expense = Expense(**payload.model_dump(exclude_none=True), license_id=current_user.license_id)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/expenses/totals")
def expense_totals(
    start: datetime | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(Expense.license_id == current_user.license_id)
    if start is not None:
        query = query.filter(Expense.created_at >= start)
    return {"total": float(query.scalar() or 0)}


@router.get("/expenses/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_expense(db, current_user.license_id, expense_id)


@router.put("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense = _get_expense(db, current_user.license_id, expense_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(expense, key, value)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    expense = _get_expense(db, current_user.license_id, expense_id)
    db.delete(expense)
    db.commit()
    return {"success": True}
