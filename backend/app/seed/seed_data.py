from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import (
    Product, Supplier, Return, Sale, Inventory,
    RefurbishmentRule, VendorTerm, LiquidationRule,
    SupplierAlert, ProposedAction, ActivityLog, SystemSetting
)

def seed_demo_database(db: Session):
    """
    Seeds the database deterministically with the reference scenario
    and multi-category datasets covering all 5 problem categories.
    """
    today = date.today()
    
    # Check if already seeded
    existing_product = db.query(Product).first()
    if existing_product:
        return {"status": "Database already contains data", "count": db.query(Product).count()}
        
    # ---------------------------------------------------------
    # 1. SUPPLIERS
    # ---------------------------------------------------------
    supp_soundwave = Supplier(
        id=1,
        supplier_name="SoundWave Dynamics",
        contact_email="returns@soundwavedynamics.com",
        status="Under Review",
        created_at=datetime.utcnow() - timedelta(days=90)
    )
    supp_optix = Supplier(
        id=2,
        supplier_name="Optix Vision Systems",
        contact_email="warranty@optixvision.com",
        status="Active",
        created_at=datetime.utcnow() - timedelta(days=120)
    )
    supp_zenith = Supplier(
        id=3,
        supplier_name="Zenith Computing",
        contact_email="rmas@zenithcomputing.com",
        status="Active",
        created_at=datetime.utcnow() - timedelta(days=150)
    )
    supp_pulse = Supplier(
        id=4,
        supplier_name="Pulse Wearables",
        contact_email="support@pulsewearables.com",
        status="Active",
        created_at=datetime.utcnow() - timedelta(days=100)
    )
    db.add_all([supp_soundwave, supp_optix, supp_zenith, supp_pulse])
    db.commit()

    # ---------------------------------------------------------
    # 2. PRODUCTS
    # ---------------------------------------------------------
    # Required Reference Product: 40 Grade-B Wireless Headphones
    prod_headphones = Product(
        sku="WH-1000XM-B",
        name="AeroSound Elite Wireless Headphones",
        category="Headphones",
        cost_price=1400.0,
        selling_price=2500.0,
        supplier_id=1,
        created_at=datetime.utcnow() - timedelta(days=60)
    )
    # High-Value Aging Product
    prod_camera = Product(
        sku="CAM-PRO-4K",
        name="Lumix Pro 4K Mirrorless Camera",
        category="Cameras",
        cost_price=18000.0,
        selling_price=28000.0,
        supplier_id=2,
        created_at=datetime.utcnow() - timedelta(days=80)
    )
    # Expiring Vendor Window Laptop
    prod_laptop = Product(
        sku="LAP-ZEN-15",
        name="Zenith UltraBook 15 OLED",
        category="Laptops",
        cost_price=35000.0,
        selling_price=52000.0,
        supplier_id=3,
        created_at=datetime.utcnow() - timedelta(days=90)
    )
    # Avoidable Liquidation Loss Smartwatch
    prod_watch = Product(
        sku="SW-FIT-02",
        name="Pulse Active 2 Smartwatch",
        category="Wearables",
        cost_price=1200.0,
        selling_price=2800.0,
        supplier_id=4,
        created_at=datetime.utcnow() - timedelta(days=70)
    )
    # Excess Stock / Low Demand Earbuds
    prod_earbuds = Product(
        sku="EB-BUD-01",
        name="BassPods Neo Wireless Buds",
        category="Audio",
        cost_price=450.0,
        selling_price=999.0,
        supplier_id=1,
        created_at=datetime.utcnow() - timedelta(days=60)
    )
    db.add_all([prod_headphones, prod_camera, prod_laptop, prod_watch, prod_earbuds])
    db.commit()

    # ---------------------------------------------------------
    # 3. REFURBISHMENT RULES
    # ---------------------------------------------------------
    refurb_rules = [
        RefurbishmentRule(
            category="Headphones",
            refurbishment_cost=250.0,
            days_required=5,
            resale_percentage_of_new_price=75.0  # 75% of ₹2,500 = ₹1,875 (Net = ₹1,625)
        ),
        RefurbishmentRule(
            category="Cameras",
            refurbishment_cost=1800.0,
            days_required=7,
            resale_percentage_of_new_price=80.0
        ),
        RefurbishmentRule(
            category="Laptops",
            refurbishment_cost=3200.0,
            days_required=8,
            resale_percentage_of_new_price=75.0
        ),
        RefurbishmentRule(
            category="Wearables",
            refurbishment_cost=300.0,
            days_required=4,
            resale_percentage_of_new_price=70.0  # 70% of ₹2,800 = ₹1,960 (Net = ₹1,660)
        ),
        RefurbishmentRule(
            category="Audio",
            refurbishment_cost=150.0,
            days_required=3,
            resale_percentage_of_new_price=65.0
        ),
    ]
    db.add_all(refurb_rules)

    # ---------------------------------------------------------
    # 4. VENDOR TERMS
    # ---------------------------------------------------------
    vendor_terms = [
        # Reference Scenario: 60% of selling price, 30 days return window
        VendorTerm(
            supplier_id=1,
            sku="WH-1000XM-B",
            rtv_allowed=True,
            credit_percentage=60.0,  # 60% of ₹2,500 = ₹1,500 credit
            window_days=30
        ),
        VendorTerm(
            supplier_id=2,
            sku=None,
            rtv_allowed=True,
            credit_percentage=70.0,
            window_days=45
        ),
        VendorTerm(
            supplier_id=3,
            sku="LAP-ZEN-15",
            rtv_allowed=True,
            credit_percentage=65.0,  # 65% of ₹52,000 = ₹33,800
            window_days=30
        ),
        VendorTerm(
            supplier_id=4,
            sku=None,
            rtv_allowed=False,  # No RTV for Pulse
            credit_percentage=0.0,
            window_days=0
        )
    ]
    db.add_all(vendor_terms)

    # ---------------------------------------------------------
    # 5. LIQUIDATION RULES
    # ---------------------------------------------------------
    # Reference Scenario: Liquidation recovery = 35% of product cost (₹1,400 * 35% = ₹490)
    liquidation_rules = [
        LiquidationRule(category="Headphones", grade="A", recovery_percentage_of_cost=45.0),
        LiquidationRule(category="Headphones", grade="B", recovery_percentage_of_cost=35.0),
        LiquidationRule(category="Headphones", grade="C", recovery_percentage_of_cost=25.0),
        LiquidationRule(category="Headphones", grade="D", recovery_percentage_of_cost=10.0),
        LiquidationRule(category="Cameras", grade="B", recovery_percentage_of_cost=40.0),
        LiquidationRule(category="Laptops", grade="B", recovery_percentage_of_cost=35.0),
        LiquidationRule(category="Wearables", grade="B", recovery_percentage_of_cost=30.0),
        LiquidationRule(category="Audio", grade="B", recovery_percentage_of_cost=25.0),
    ]
    db.add_all(liquidation_rules)

    # ---------------------------------------------------------
    # 6. INVENTORY
    # ---------------------------------------------------------
    # Reference Scenario: Existing new-stock coverage = 60 days of demand (e.g. 600 units / 10 daily demand)
    inventory_records = [
        Inventory(
            sku="WH-1000XM-B",
            new_stock=600,
            avg_daily_demand=10.0,  # 600 / 10 = 60 days coverage!
            updated_at=datetime.utcnow()
        ),
        Inventory(
            sku="CAM-PRO-4K",
            new_stock=15,
            avg_daily_demand=1.2,
            updated_at=datetime.utcnow()
        ),
        Inventory(
            sku="LAP-ZEN-15",
            new_stock=24,
            avg_daily_demand=2.0,
            updated_at=datetime.utcnow()
        ),
        Inventory(
            sku="SW-FIT-02",
            new_stock=40,
            avg_daily_demand=8.0,
            updated_at=datetime.utcnow()
        ),
        Inventory(
            sku="EB-BUD-01",
            new_stock=1500,
            avg_daily_demand=20.0,  # 75 days coverage!
            updated_at=datetime.utcnow()
        )
    ]
    db.add_all(inventory_records)

    # ---------------------------------------------------------
    # 7. RETURNS
    # ---------------------------------------------------------
    # Reference Scenario: 40 Grade-B wireless headphones
    # Received 18 days ago (30-day window -> 12 days remaining)
    # Batch HB-09
    # 70% report same fault ("Audio Driver Hiss / Bluetooth Drop") -> 28 units fault, 12 units other
    ret_headphones_main = Return(
        id=101,
        return_date=today - timedelta(days=18),
        sku="WH-1000XM-B",
        supplier_batch="HB-09",
        reason_code="Audio Driver Hiss / Bluetooth Drop",
        grade="B",
        quantity=28,  # 70% of 40 units!
        status="Pending Decision",
        received_at=datetime.utcnow() - timedelta(days=18),
        recommended_route="Split-Batch",
        created_at=datetime.utcnow() - timedelta(days=18)
    )
    ret_headphones_minor = Return(
        id=102,
        return_date=today - timedelta(days=18),
        sku="WH-1000XM-B",
        supplier_batch="HB-09",
        reason_code="Cosmetic Scuffs on Ear-cup",
        grade="B",
        quantity=12,  # 30% of 40 units (Total = 40 units!)
        status="Pending Decision",
        received_at=datetime.utcnow() - timedelta(days=18),
        recommended_route="Split-Batch",
        created_at=datetime.utcnow() - timedelta(days=18)
    )
    
    # Problem 1: High-Value Return Waiting Too Long (21 days)
    ret_camera_aging = Return(
        id=103,
        return_date=today - timedelta(days=21),
        sku="CAM-PRO-4K",
        supplier_batch="OP-44",
        reason_code="Focus Motor Whine",
        grade="B",
        quantity=15,
        status="Pending Decision",
        received_at=datetime.utcnow() - timedelta(days=21),
        recommended_route="Vendor Return",
        created_at=datetime.utcnow() - timedelta(days=21)
    )
    
    # Problem 3: Vendor Return Window Closing Soon (27 days old vs 30 days window -> 3 days left!)
    ret_laptop_expiring = Return(
        id=104,
        return_date=today - timedelta(days=27),
        sku="LAP-ZEN-15",
        supplier_batch="LP-03",
        reason_code="Trackpad Latency",
        grade="B",
        quantity=8,
        status="Pending Decision",
        received_at=datetime.utcnow() - timedelta(days=27),
        recommended_route="Vendor Return",
        created_at=datetime.utcnow() - timedelta(days=27)
    )
    
    # Problem 2: Avoidable Liquidation Loss (High demand smartwatch marked for exit)
    ret_watch_liq = Return(
        id=105,
        return_date=today - timedelta(days=5),
        sku="SW-FIT-02",
        supplier_batch="SW-88",
        reason_code="Customer Remorse / Unwanted Gift",
        grade="B",
        quantity=25,
        status="Pending Decision",
        received_at=datetime.utcnow() - timedelta(days=5),
        recommended_route="Refurbish",
        created_at=datetime.utcnow() - timedelta(days=5)
    )
    
    # Problem 5: Refurbishing what nobody wants (75 days stock, low value)
    ret_earbuds_excess = Return(
        id=106,
        return_date=today - timedelta(days=10),
        sku="EB-BUD-01",
        supplier_batch="EB-12",
        reason_code="Volume Imbalance",
        grade="B",
        quantity=50,
        status="Pending Decision",
        received_at=datetime.utcnow() - timedelta(days=10),
        recommended_route="Liquidation",
        created_at=datetime.utcnow() - timedelta(days=10)
    )
    
    # Restock Candidate: Grade A Pristine
    ret_headphones_grade_a = Return(
        id=107,
        return_date=today - timedelta(days=2),
        sku="WH-1000XM-B",
        supplier_batch="HB-10",
        reason_code="Unopened Box / Wrong Color Ordered",
        grade="A",
        quantity=10,
        status="Pending Decision",
        received_at=datetime.utcnow() - timedelta(days=2),
        recommended_route="Restock",
        created_at=datetime.utcnow() - timedelta(days=2)
    )

    db.add_all([
        ret_headphones_main, ret_headphones_minor, ret_camera_aging,
        ret_laptop_expiring, ret_watch_liq, ret_earbuds_excess, ret_headphones_grade_a
    ])
    db.commit()

    # ---------------------------------------------------------
    # 8. SALES HISTORY
    # ---------------------------------------------------------
    for day_offset in range(1, 31):
        s_date = today - timedelta(days=day_offset)
        db.add(Sale(sale_date=s_date, sku="WH-1000XM-B", quantity_sold=10, selling_price=2500.0))
        db.add(Sale(sale_date=s_date, sku="CAM-PRO-4K", quantity_sold=1, selling_price=28000.0))
        db.add(Sale(sale_date=s_date, sku="LAP-ZEN-15", quantity_sold=2, selling_price=52000.0))
        db.add(Sale(sale_date=s_date, sku="SW-FIT-02", quantity_sold=8, selling_price=2800.0))
    db.commit()

    # ---------------------------------------------------------
    # 9. SUPPLIER ALERTS
    # ---------------------------------------------------------
    # Alert for Batch HB-09
    alert_hb09 = SupplierAlert(
        supplier_id=1,
        sku="WH-1000XM-B",
        supplier_batch="HB-09",
        alert_type="HIGH_DEFECT_RATE",
        observed_return_rate=28.0,
        baseline_return_rate=5.0,
        evidence={
            "dominant_reason": "Audio Driver Hiss / Bluetooth Drop",
            "dominant_percentage": 70.0,
            "total_returns": 40,
            "severity_note": "Concentrated acoustic hardware failure in batch HB-09"
        },
        severity="Critical",
        status="Active",
        created_at=datetime.utcnow() - timedelta(days=2)
    )
    db.add(alert_hb09)
    db.commit()

    # ---------------------------------------------------------
    # 10. SYSTEM SETTINGS
    # ---------------------------------------------------------
    settings_records = [
        SystemSetting(key="aging_threshold_days", value="7", description="Days waiting before return is flagged as aging"),
        SystemSetting(key="expiring_window_threshold_days", value="7", description="Days remaining before vendor window warning"),
        SystemSetting(key="high_value_threshold", value="1500.0", description="Product cost cutoff for high-value returns"),
        SystemSetting(key="defect_anomaly_percentage", value="15.0", description="Threshold for flagging supplier defect spikes"),
        SystemSetting(key="excess_inventory_days", value="45", description="Days of new stock coverage triggering demand saturation warning")
    ]
    db.add_all(settings_records)

    # ---------------------------------------------------------
    # 11. INITIAL ACTIVITY LOG
    # ---------------------------------------------------------
    log_init = ActivityLog(
        actor="System Seed Engine",
        action="SYSTEM_INITIALIZED",
        entity_type="Database",
        entity_id="ALL",
        details={"message": "Loaded Gadgetbay reference scenario (Batch HB-09, 40 headphones) and demo datasets."},
        created_at=datetime.utcnow()
    )
    db.add(log_init)
    db.commit()

    return {"status": "Success", "message": "Demo data successfully loaded"}
