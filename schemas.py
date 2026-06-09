from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from models import LicenseStatus, UserRole


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    error: str
    code: int


class LicenseActivateRequest(BaseModel):
    licenseKey: str
    deviceId: str


class LicenseInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    valid: bool
    status: str
    storeName: str
    expiresAt: str
    daysLeft: int


class LicenseResponse(BaseModel):
    success: bool
    license: LicenseInfo | None = None
    error: str | None = None


class AnnouncementResponse(BaseModel):
    announcements: list[dict[str, Any]] = Field(default_factory=list)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    licenseKey: str


class PinLoginRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=4)


class UserOut(APIModel):
    id: int
    email: EmailStr
    name: str
    role: UserRole
    pin: str | None = None
    license_id: int
    active: bool
    created_at: datetime
    updated_at: datetime


class UserPublic(APIModel):
    id: int
    email: EmailStr
    name: str
    role: UserRole


class TokenResponse(BaseModel):
    token: str
    user: UserOut


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: UserRole = UserRole.cashier
    pin: str | None = Field(default=None, min_length=4, max_length=4)
    active: bool = True


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    name: str | None = None
    role: UserRole | None = None
    pin: str | None = Field(default=None, min_length=4, max_length=4)
    active: bool | None = None


class ProductBase(BaseModel):
    name: str
    barcode: str | None = None
    category_id: int | None = None
    price: float = 0
    price_gros: float | None = None
    price_semi_gros: float | None = None
    cost: float = 0
    stock_qty: float = 0
    low_stock_threshold: float = 0
    image_uri: str | None = None
    active: bool = True
    featured: bool = False
    unit: str = "pcs"
    expire_date: datetime | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    barcode: str | None = None
    category_id: int | None = None
    price: float | None = None
    price_gros: float | None = None
    price_semi_gros: float | None = None
    cost: float | None = None
    stock_qty: float | None = None
    low_stock_threshold: float | None = None
    image_uri: str | None = None
    active: bool | None = None
    featured: bool | None = None
    unit: str | None = None
    expire_date: datetime | None = None


class ProductOut(ProductBase, APIModel):
    id: int
    created_at: datetime
    updated_at: datetime
    license_id: int


class CustomerBase(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    total_spent: float = 0
    visit_count: int = 0


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    total_spent: float | None = None
    visit_count: int | None = None


class CustomerOut(CustomerBase, APIModel):
    id: int
    created_at: datetime
    updated_at: datetime
    license_id: int


class SaleItemNestedCreate(BaseModel):
    product_id: int | None = None
    product_name: str
    quantity: float
    unit_price: float
    discount: float = 0
    total: float
    cost_at_sale: float = 0


class SaleItemCreate(SaleItemNestedCreate):
    sale_id: int


class SaleItemOut(SaleItemNestedCreate, APIModel):
    id: int
    sale_id: int
    license_id: int


class SaleBase(BaseModel):
    user_id: int | None = None
    customer_id: int | None = None
    subtotal: float = 0
    tax: float = 0
    discount: float = 0
    total: float = 0
    payment_method: str = "cash"
    status: str = "completed"
    created_at: datetime | None = None


class SaleCreate(SaleBase):
    items: list[SaleItemNestedCreate] = Field(default_factory=list)


class SaleUpdate(BaseModel):
    user_id: int | None = None
    customer_id: int | None = None
    subtotal: float | None = None
    tax: float | None = None
    discount: float | None = None
    total: float | None = None
    payment_method: str | None = None
    status: str | None = None
    created_at: datetime | None = None


class SaleOut(SaleBase, APIModel):
    id: int
    created_at: datetime
    license_id: int
    items: list[SaleItemOut] = []


class DebtBase(BaseModel):
    customer_id: int | None = None
    sale_id: int | None = None
    amount: float
    paid: float = 0
    note: str | None = None
    status: str = "open"
    due_date: datetime | None = None


class DebtCreate(DebtBase):
    pass


class DebtUpdate(BaseModel):
    customer_id: int | None = None
    sale_id: int | None = None
    amount: float | None = None
    paid: float | None = None
    note: str | None = None
    status: str | None = None
    due_date: datetime | None = None


class DebtOut(DebtBase, APIModel):
    id: int
    created_at: datetime
    updated_at: datetime
    license_id: int


class DebtPaymentCreate(BaseModel):
    debt_id: int
    amount: float
    payment_method: str = "cash"
    note: str | None = None


class DebtPaymentOut(DebtPaymentCreate, APIModel):
    id: int
    created_at: datetime
    license_id: int


class InventoryCreate(BaseModel):
    product_id: int
    type: str
    quantity: float
    reason: str | None = None
    user_id: int | None = None


class InventoryUpdate(BaseModel):
    product_id: int | None = None
    type: str | None = None
    quantity: float | None = None
    reason: str | None = None
    user_id: int | None = None


class InventoryOut(InventoryCreate, APIModel):
    id: int
    created_at: datetime
    license_id: int


class SupplierBase(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    note: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    note: str | None = None


class SupplierOut(SupplierBase, APIModel):
    id: int
    created_at: datetime
    updated_at: datetime
    license_id: int


class PurchaseItemNestedCreate(BaseModel):
    product_id: int | None = None
    product_name: str
    quantity: float
    unit_cost: float
    total: float


class PurchaseItemCreate(PurchaseItemNestedCreate):
    purchase_id: int


class PurchaseItemOut(PurchaseItemNestedCreate, APIModel):
    id: int
    purchase_id: int
    license_id: int


class PurchaseBase(BaseModel):
    supplier_id: int | None = None
    supplier_name: str | None = None
    total: float = 0
    amount_paid: float = 0
    payment_method: str = "cash"
    status: str = "completed"
    note: str | None = None
    created_at: datetime | None = None


class PurchaseCreate(PurchaseBase):
    items: list[PurchaseItemNestedCreate] = Field(default_factory=list)


class PurchaseUpdate(BaseModel):
    supplier_id: int | None = None
    supplier_name: str | None = None
    total: float | None = None
    amount_paid: float | None = None
    payment_method: str | None = None
    status: str | None = None
    note: str | None = None
    created_at: datetime | None = None


class PurchaseOut(PurchaseBase, APIModel):
    id: int
    created_at: datetime
    license_id: int
    items: list[PurchaseItemOut] = []


class SupplierDebtBase(BaseModel):
    supplier_id: int | None = None
    purchase_id: int | None = None
    amount: float
    paid: float = 0
    note: str | None = None
    status: str = "open"
    due_date: datetime | None = None


class SupplierDebtCreate(SupplierDebtBase):
    pass


class SupplierDebtUpdate(BaseModel):
    supplier_id: int | None = None
    purchase_id: int | None = None
    amount: float | None = None
    paid: float | None = None
    note: str | None = None
    status: str | None = None
    due_date: datetime | None = None


class SupplierDebtOut(SupplierDebtBase, APIModel):
    id: int
    created_at: datetime
    updated_at: datetime
    license_id: int


class ExpenseBase(BaseModel):
    category: str
    amount: float
    description: str | None = None
    payment_method: str = "cash"
    created_at: datetime | None = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    category: str | None = None
    amount: float | None = None
    description: str | None = None
    payment_method: str | None = None
    created_at: datetime | None = None


class ExpenseOut(ExpenseBase, APIModel):
    id: int
    created_at: datetime
    license_id: int


class UnitBase(BaseModel):
    name: str
    allow_decimal: bool = False
    is_builtin: bool = False
    sort_order: int = 0


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    name: str | None = None
    allow_decimal: bool | None = None
    is_builtin: bool | None = None
    sort_order: int | None = None


class UnitOut(UnitBase, APIModel):
    id: int
    created_at: datetime
    updated_at: datetime
    license_id: int


class AdminLicenseCreate(BaseModel):
    licenseKey: str | None = None
    deviceId: str | None = None
    storeName: str
    ownerName: str | None = None
    ownerPhone: str | None = None
    status: LicenseStatus = LicenseStatus.active
    expiresAt: datetime
    notes: str | None = None


class AdminLicenseUpdate(BaseModel):
    licenseKey: str | None = None
    deviceId: str | None = None
    storeName: str | None = None
    ownerName: str | None = None
    ownerPhone: str | None = None
    status: LicenseStatus | None = None
    expiresAt: datetime | None = None
    notes: str | None = None


class LicenseAdminOut(APIModel):
    id: int
    license_key: str
    device_id: str | None
    store_name: str
    owner_name: str | None
    owner_phone: str | None
    status: LicenseStatus
    expires_at: datetime
    created_at: datetime
    notes: str | None


class GeneratedKeyResponse(BaseModel):
    licenseKey: str


class SummaryResponse(BaseModel):
    sales_total: float
    sales_count: int
    customers_count: int
    products_count: int
    debts_balance: float
    expenses_total: float
    low_stock_count: int
