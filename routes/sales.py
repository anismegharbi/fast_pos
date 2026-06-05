from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from auth import get_current_user
from database import get_db
from models import Customer, Debt, Expense, Product, Sale, SaleItem, User
from schemas import SaleCreate, SaleItemCreate, SaleItemOut, SaleOut, SaleUpdate, SummaryResponse

router = APIRouter(tags=["sales"])


def _get_sale(db: Session, license_id: int, sale_id: int) -> Sale:
    sale = (
        db.query(Sale)
        .options(selectinload(Sale.items))
        .filter(Sale.id == sale_id, Sale.license_id == license_id)
        .first()
    )
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")
    return sale


def _apply_sale_side_effects(db: Session, license_id: int, sale: Sale) -> None:
    if sale.customer_id:
        customer = db.query(Customer).filter(Customer.id == sale.customer_id, Customer.license_id == license_id).first()
        if customer:
            customer.total_spent = (customer.total_spent or 0) + sale.total
            customer.visit_count = (customer.visit_count or 0) + 1

    for item in sale.items:
        if item.product_id:
            product = db.query(Product).filter(Product.id == item.product_id, Product.license_id == license_id).first()
            if product:
                product.stock_qty = (product.stock_qty or 0) - item.quantity


@router.get("/sales", response_model=list[SaleOut])
def list_sales(
    customerId: int | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=500),
    start: datetime | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Sale).options(selectinload(Sale.items)).filter(Sale.license_id == current_user.license_id)
    if customerId is not None:
        query = query.filter(Sale.customer_id == customerId)
    if start is not None:
        query = query.filter(Sale.created_at >= start)
    query = query.order_by(Sale.created_at.desc())
    if limit is not None:
        query = query.limit(limit)
    return query.all()


@router.post("/sales", response_model=SaleOut)
def create_sale(
    payload: SaleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude={"items"}, exclude_none=True)
    if data.get("user_id") is None:
        data["user_id"] = current_user.id
    sale = Sale(**data, license_id=current_user.license_id)
    db.add(sale)
    db.flush()
    for item_payload in payload.items:
        sale.items.append(SaleItem(**item_payload.model_dump(), sale_id=sale.id, license_id=current_user.license_id))
    _apply_sale_side_effects(db, current_user.license_id, sale)
    db.commit()
    db.refresh(sale)
    return _get_sale(db, current_user.license_id, sale.id)


@router.post("/sale/", response_model=SaleOut)
def create_sale_alias(
    payload: SaleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_sale(payload, current_user, db)


@router.get("/sales/daily-total")
def daily_total(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    total = (
        db.query(func.coalesce(func.sum(Sale.total), 0))
        .filter(Sale.license_id == current_user.license_id, Sale.created_at >= today)
        .scalar()
    )
    return {"total": float(total or 0)}


@router.get("/summary", response_model=SummaryResponse)
def summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    license_id = current_user.license_id
    sales_total = db.query(func.coalesce(func.sum(Sale.total), 0)).filter(Sale.license_id == license_id).scalar() or 0
    sales_count = db.query(func.count(Sale.id)).filter(Sale.license_id == license_id).scalar() or 0
    customers_count = db.query(func.count(Customer.id)).filter(Customer.license_id == license_id).scalar() or 0
    products_count = db.query(func.count(Product.id)).filter(Product.license_id == license_id).scalar() or 0
    debts_total = db.query(func.coalesce(func.sum(Debt.amount - Debt.paid), 0)).filter(Debt.license_id == license_id).scalar() or 0
    expenses_total = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(Expense.license_id == license_id).scalar() or 0
    low_stock_count = (
        db.query(func.count(Product.id))
        .filter(Product.license_id == license_id, Product.active.is_(True), Product.stock_qty <= Product.low_stock_threshold)
        .scalar()
        or 0
    )
    return SummaryResponse(
        sales_total=float(sales_total),
        sales_count=int(sales_count),
        customers_count=int(customers_count),
        products_count=int(products_count),
        debts_balance=float(debts_total),
        expenses_total=float(expenses_total),
        low_stock_count=int(low_stock_count),
    )


@router.get("/sales/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_sale(db, current_user.license_id, sale_id)


@router.put("/sales/{sale_id}", response_model=SaleOut)
def update_sale(
    sale_id: int,
    payload: SaleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sale = _get_sale(db, current_user.license_id, sale_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(sale, key, value)
    db.commit()
    db.refresh(sale)
    return sale


@router.delete("/sales/{sale_id}")
def delete_sale(sale_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sale = _get_sale(db, current_user.license_id, sale_id)
    db.delete(sale)
    db.commit()
    return {"success": True}


@router.get("/sale-items", response_model=list[SaleItemOut])
def list_sale_items(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(SaleItem).filter(SaleItem.license_id == current_user.license_id).order_by(SaleItem.id.desc()).all()


@router.post("/sale-items", response_model=SaleItemOut)
def create_sale_item(
    payload: SaleItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sale = _get_sale(db, current_user.license_id, payload.sale_id)
    item = SaleItem(**payload.model_dump(), license_id=current_user.license_id)
    sale.items.append(item)
    db.commit()
    db.refresh(item)
    return item
