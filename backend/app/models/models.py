from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


# ============================================================
# PRODUCT MODEL
# ============================================================

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    cost_price = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id"),
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    supplier = relationship("Supplier", back_populates="products")
    returns = relationship("Return", back_populates="product")
    inventory = relationship(
        "Inventory",
        back_populates="product",
        uselist=False,
    )


# ============================================================
# SUPPLIER MODEL
# ============================================================

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    supplier_name = Column(String(255), unique=True, nullable=False, index=True)
    contact_email = Column(String(255), nullable=False)
    status = Column(
        String(50),
        default="Active",
    )  # Active, Under Investigation, Flagged
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    products = relationship("Product", back_populates="supplier")
    vendor_terms = relationship("VendorTerm", back_populates="supplier")
    alerts = relationship("SupplierAlert", back_populates="supplier")


# ============================================================
# RETURN MODEL
# ============================================================

class Return(Base):
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    return_date = Column(Date, nullable=False)

    sku = Column(
        String(100),
        ForeignKey("products.sku"),
        nullable=False,
        index=True,
    )

    supplier_batch = Column(String(100), nullable=False, index=True)
    reason_code = Column(String(100), nullable=False, index=True)
    grade = Column(String(10), nullable=False, index=True)  # A, B, C, D
    quantity = Column(Integer, default=1, nullable=False)

    status = Column(
        String(50),
        default="Pending Decision",
        index=True,
    )

    received_at = Column(DateTime, default=datetime.utcnow)

    recommended_route = Column(
        String(50),
        nullable=True,
    )  # Restock, Refurbish, Vendor Return, Liquidation, Scrap, Split-Batch

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="returns")

    recovery_analyses = relationship(
        "RecoveryAnalysis",
        back_populates="return_item",
    )


# ============================================================
# SALES MODEL
# ============================================================

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sale_date = Column(Date, nullable=False, index=True)

    sku = Column(
        String(100),
        ForeignKey("products.sku"),
        nullable=False,
        index=True,
    )

    quantity_sold = Column(Integer, nullable=False)
    selling_price = Column(Float, nullable=False)


# ============================================================
# INVENTORY MODEL
# ============================================================

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    sku = Column(
        String(100),
        ForeignKey("products.sku"),
        unique=True,
        nullable=False,
        index=True,
    )

    new_stock = Column(Integer, default=0, nullable=False)
    avg_daily_demand = Column(Float, default=0.0, nullable=False)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    product = relationship("Product", back_populates="inventory")


# ============================================================
# REFURBISHMENT RULE MODEL
# ============================================================

class RefurbishmentRule(Base):
    __tablename__ = "refurbishment_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category = Column(String(100), unique=True, nullable=False, index=True)
    refurbishment_cost = Column(Float, nullable=False)
    days_required = Column(Integer, nullable=False)

    # Example: 75.0 means 75% of the new selling price.
    resale_percentage_of_new_price = Column(Float, nullable=False)


# ============================================================
# VENDOR TERMS MODEL
# ============================================================

class VendorTerm(Base):
    __tablename__ = "vendor_terms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id"),
        nullable=False,
        index=True,
    )

    # Optional SKU-specific override.
    # NULL means the term applies supplier-wide.
    sku = Column(String(100), nullable=True, index=True)

    rtv_allowed = Column(Boolean, default=True, nullable=False)

    # Example: 60.0 means 60% of the applicable price.
    credit_percentage = Column(Float, nullable=False)

    window_days = Column(Integer, default=30, nullable=False)

    # Relationships
    supplier = relationship("Supplier", back_populates="vendor_terms")


# ============================================================
# LIQUIDATION RULE MODEL
# ============================================================

class LiquidationRule(Base):
    __tablename__ = "liquidation_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category = Column(String(100), nullable=False, index=True)
    grade = Column(String(10), nullable=False, index=True)

    # Example: 35.0 means 35% of the product's cost price.
    recovery_percentage_of_cost = Column(Float, nullable=False)


# ============================================================
# RECOVERY ANALYSIS MODEL
# ============================================================

class RecoveryAnalysis(Base):
    __tablename__ = "recovery_analyses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    return_id = Column(
        Integer,
        ForeignKey("returns.id"),
        nullable=True,
        index=True,
    )

    batch_reference = Column(String(100), nullable=True, index=True)

    # Stores the calculated recovery options as JSON.
    route_comparisons = Column(JSON, nullable=False)

    recommended_route = Column(String(50), nullable=False)
    recommendation_reason = Column(Text, nullable=False)
    estimated_net_recovery = Column(Float, nullable=False)
    estimated_time_to_cash_days = Column(Integer, nullable=False)

    analysis_status = Column(
        String(50),
        default="Current",
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    return_item = relationship(
        "Return",
        back_populates="recovery_analyses",
    )


# ============================================================
# SUPPLIER ALERT MODEL
# ============================================================

class SupplierAlert(Base):
    __tablename__ = "supplier_alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id"),
        nullable=False,
        index=True,
    )

    sku = Column(String(100), nullable=True, index=True)
    supplier_batch = Column(String(100), nullable=True, index=True)

    # HIGH_DEFECT_RATE, EXPIRING_WINDOW, ABNORMAL_SPIKE
    alert_type = Column(String(100), nullable=False)

    observed_return_rate = Column(Float, nullable=False)
    baseline_return_rate = Column(Float, nullable=False)

    # Stores supporting evidence and statistics.
    evidence = Column(JSON, nullable=False)

    severity = Column(
        String(20),
        default="High",
        index=True,
    )  # Low, Medium, High, Critical

    status = Column(
        String(50),
        default="Active",
        index=True,
    )  # Active, Investigating, Resolved, Dismissed

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    supplier = relationship("Supplier", back_populates="alerts")


# ============================================================
# PROPOSED ACTION MODEL
# ============================================================

class ProposedAction(Base):
    __tablename__ = "proposed_actions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # VENDOR_RETURN, REFURBISH, RESTOCK, LIQUIDATION,
    # SPLIT_BATCH, SUPPLIER_INVESTIGATION, SUPPLIER_NOTIFICATION
    action_type = Column(String(100), nullable=False, index=True)

    # Stores a list of Return IDs or a batch identifier.
    related_return_ids = Column(JSON, nullable=False)

    proposed_quantity = Column(Integer, nullable=False)
    estimated_recovery = Column(Float, nullable=False)
    explanation = Column(Text, nullable=False)

    # Supporting evidence and assumptions.
    evidence = Column(JSON, nullable=True)
    risks_and_assumptions = Column(JSON, nullable=True)

    status = Column(
        String(50),
        default="Pending",
        index=True,
    )  # Pending, Approved, Rejected, Executed (Simulated)

    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)


# ============================================================
# ACTIVITY LOG MODEL
# ============================================================

class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    actor = Column(
        String(100),
        default="System",
        nullable=False,
    )

    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)

    # Stores additional activity information as JSON.
    details = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# SYSTEM SETTINGS MODEL
# ============================================================

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )