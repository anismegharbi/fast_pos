from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Product, User
from schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(tags=["products"])


def _get_product(db: Session, license_id: int, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id, Product.license_id == license_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.get("/products", response_model=list[ProductOut])
def list_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Product).filter(Product.license_id == current_user.license_id).order_by(Product.id.desc()).all()


@router.post("/products", response_model=ProductOut)
def create_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = Product(**payload.model_dump(), license_id=current_user.license_id)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/products/low-stock", response_model=list[ProductOut])
def low_stock_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Product)
        .filter(
            Product.license_id == current_user.license_id,
            Product.active.is_(True),
            Product.stock_qty <= Product.low_stock_threshold,
        )
        .order_by(Product.stock_qty.asc())
        .all()
    )


@router.get("/products/barcode/{barcode}", response_model=ProductOut)
def product_by_barcode(
    barcode: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.license_id == current_user.license_id, Product.barcode == barcode).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.get("/barcodes/{barcode}", response_model=ProductOut)
def barcode_lookup(
    barcode: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return product_by_barcode(barcode, current_user, db)


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_product(db, current_user.license_id, product_id)


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = _get_product(db, current_user.license_id, product_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = _get_product(db, current_user.license_id, product_id)
    db.delete(product)
    db.commit()
    return {"success": True}
