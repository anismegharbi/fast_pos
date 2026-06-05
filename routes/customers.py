from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Customer, User
from schemas import CustomerCreate, CustomerOut, CustomerUpdate

router = APIRouter(tags=["customers"])


def _get_customer(db: Session, license_id: int, customer_id: int) -> Customer:
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.license_id == license_id).first()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Customer).filter(Customer.license_id == current_user.license_id).order_by(Customer.name).all()


@router.post("/customers", response_model=CustomerOut)
def create_customer(
    payload: CustomerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = Customer(**payload.model_dump(), license_id=current_user.license_id)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_customer(db, current_user.license_id, customer_id)


@router.put("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = _get_customer(db, current_user.license_id, customer_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/customers/{customer_id}")
def delete_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = _get_customer(db, current_user.license_id, customer_id)
    db.delete(customer)
    db.commit()
    return {"success": True}
