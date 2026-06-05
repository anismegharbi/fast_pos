from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from auth import get_current_user
from database import get_db
from models import Product, Purchase, PurchaseItem, User
from schemas import PurchaseCreate, PurchaseItemCreate, PurchaseItemOut, PurchaseOut, PurchaseUpdate

router = APIRouter(tags=["purchases"])


def _get_purchase(db: Session, license_id: int, purchase_id: int) -> Purchase:
    purchase = (
        db.query(Purchase)
        .options(selectinload(Purchase.items))
        .filter(Purchase.id == purchase_id, Purchase.license_id == license_id)
        .first()
    )
    if purchase is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase not found")
    return purchase


def _add_purchase_stock(db: Session, license_id: int, purchase: Purchase) -> None:
    for item in purchase.items:
        if item.product_id:
            product = db.query(Product).filter(Product.id == item.product_id, Product.license_id == license_id).first()
            if product:
                product.stock_qty = (product.stock_qty or 0) + item.quantity
                product.cost = item.unit_cost


@router.get("/purchases", response_model=list[PurchaseOut])
def list_purchases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Purchase)
        .options(selectinload(Purchase.items))
        .filter(Purchase.license_id == current_user.license_id)
        .order_by(Purchase.created_at.desc())
        .all()
    )


@router.post("/purchases", response_model=PurchaseOut)
def create_purchase(
    payload: PurchaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude={"items"}, exclude_none=True)
    purchase = Purchase(**data, license_id=current_user.license_id)
    db.add(purchase)
    db.flush()
    for item_payload in payload.items:
        purchase.items.append(PurchaseItem(**item_payload.model_dump(), purchase_id=purchase.id, license_id=current_user.license_id))
    _add_purchase_stock(db, current_user.license_id, purchase)
    db.commit()
    db.refresh(purchase)
    return _get_purchase(db, current_user.license_id, purchase.id)


@router.get("/has-purchases")
def has_purchases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(func.count(Purchase.id)).filter(Purchase.license_id == current_user.license_id).scalar() or 0
    return {"hasPurchases": count > 0}


@router.get("/purchases/{purchase_id}", response_model=PurchaseOut)
def get_purchase(purchase_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_purchase(db, current_user.license_id, purchase_id)


@router.put("/purchases/{purchase_id}", response_model=PurchaseOut)
def update_purchase(
    purchase_id: int,
    payload: PurchaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    purchase = _get_purchase(db, current_user.license_id, purchase_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(purchase, key, value)
    db.commit()
    db.refresh(purchase)
    return purchase


@router.delete("/purchases/{purchase_id}")
def delete_purchase(purchase_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    purchase = _get_purchase(db, current_user.license_id, purchase_id)
    db.delete(purchase)
    db.commit()
    return {"success": True}


@router.get("/purchase-items", response_model=list[PurchaseItemOut])
def list_purchase_items(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(PurchaseItem).filter(PurchaseItem.license_id == current_user.license_id).order_by(PurchaseItem.id.desc()).all()


@router.post("/purchase-items", response_model=PurchaseItemOut)
def create_purchase_item(
    payload: PurchaseItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    purchase = _get_purchase(db, current_user.license_id, payload.purchase_id)
    item = PurchaseItem(**payload.model_dump(), license_id=current_user.license_id)
    purchase.items.append(item)
    db.commit()
    db.refresh(item)
    return item
