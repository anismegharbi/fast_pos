from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import InventoryMovement, Product, User
from schemas import InventoryCreate, InventoryOut

router = APIRouter(tags=["inventory"])


@router.get("/inventory", response_model=list[InventoryOut])
def list_inventory(
    productId: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(InventoryMovement).filter(InventoryMovement.license_id == current_user.license_id)
    if productId is not None:
        query = query.filter(InventoryMovement.product_id == productId)
    return query.order_by(InventoryMovement.created_at.desc()).all()


@router.post("/inventory", response_model=InventoryOut)
def create_inventory_movement(
    payload: InventoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == payload.product_id, Product.license_id == current_user.license_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    data = payload.model_dump()
    data["user_id"] = data.get("user_id") or current_user.id
    movement = InventoryMovement(**data, license_id=current_user.license_id)
    if payload.type in {"in", "add", "purchase", "adjustment_in"}:
        product.stock_qty = (product.stock_qty or 0) + payload.quantity
    elif payload.type in {"out", "remove", "sale", "adjustment_out"}:
        product.stock_qty = (product.stock_qty or 0) - payload.quantity

    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement
