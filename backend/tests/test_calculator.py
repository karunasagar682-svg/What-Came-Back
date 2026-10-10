import pytest
from datetime import date, timedelta
from app.models.models import Product, Return, Inventory, RefurbishmentRule, VendorTerm, LiquidationRule
from app.engine.calculator import calculate_route_options, evaluate_split_plan

@pytest.fixture
def sample_product():
    return Product(
        id=1,
        sku="TEST-SKU-01",
        name="Test Wireless Headphones",
        category="Headphones",
        cost_price=1400.0,
        selling_price=2500.0,
        supplier_id=1
    )

@pytest.fixture
def sample_inventory():
    return Inventory(
        id=1,
        sku="TEST-SKU-01",
        new_stock=600,
        avg_daily_demand=10.0  # 60 days of coverage
    )

@pytest.fixture
def sample_refurb_rule():
    return RefurbishmentRule(
        id=1,
        category="Headphones",
        refurbishment_cost=250.0,
        days_required=5,
        resale_percentage_of_new_price=75.0
    )

@pytest.fixture
def sample_vendor_term():
    return VendorTerm(
        id=1,
        supplier_id=1,
        sku="TEST-SKU-01",
        rtv_allowed=True,
        credit_percentage=60.0,
        window_days=30
    )

@pytest.fixture
def sample_liq_rule():
    return LiquidationRule(
        id=1,
        category="Headphones",
        grade="B",
        recovery_percentage_of_cost=35.0
    )

def test_restock_eligibility_grade_a(sample_product, sample_inventory, sample_refurb_rule, sample_vendor_term, sample_liq_rule):
    ret = Return(
        id=1,
        return_date=date.today(),
        sku="TEST-SKU-01",
        supplier_batch="B-01",
        reason_code="Unopened",
        grade="A",
        quantity=10,
        status="Pending Decision"
    )
    res = calculate_route_options(sample_product, ret, sample_inventory, sample_refurb_rule, sample_vendor_term, sample_liq_rule)
    restock = res.routes["Restock"]
    assert restock.is_eligible is True
    assert restock.recovery_per_unit == 2450.0  # 2500 - 50 inspection cost
    assert restock.net_recovery == 24500.0

def test_restock_ineligibility_grade_b(sample_product, sample_inventory, sample_refurb_rule, sample_vendor_term, sample_liq_rule):
    ret = Return(
        id=2,
        return_date=date.today(),
        sku="TEST-SKU-01",
        supplier_batch="B-02",
        reason_code="Scratched",
        grade="B",
        quantity=5,
        status="Pending Decision"
    )
    res = calculate_route_options(sample_product, ret, sample_inventory, sample_refurb_rule, sample_vendor_term, sample_liq_rule)
    restock = res.routes["Restock"]
    assert restock.is_eligible is False
    assert "Grade B" in restock.ineligibility_reason

def test_refurbish_calculation(sample_product, sample_inventory, sample_refurb_rule, sample_vendor_term, sample_liq_rule):
    ret = Return(
        id=3,
        return_date=date.today(),
        sku="TEST-SKU-01",
        supplier_batch="B-03",
        reason_code="Audio Issue",
        grade="B",
        quantity=10,
        status="Pending Decision"
    )
    res = calculate_route_options(sample_product, ret, sample_inventory, sample_refurb_rule, sample_vendor_term, sample_liq_rule)
    refurb = res.routes["Refurbish"]
    assert refurb.is_eligible is True
    # Resale = 75% of 2500 = 1875. Cost = 250. Net = 1625 per unit.
    assert refurb.recovery_per_unit == 1625.0
    assert refurb.net_recovery == 16250.0

def test_liquidation_calculation(sample_product, sample_inventory, sample_refurb_rule, sample_vendor_term, sample_liq_rule):
    ret = Return(
        id=4,
        return_date=date.today(),
        sku="TEST-SKU-01",
        supplier_batch="B-04",
        reason_code="Scratched",
        grade="B",
        quantity=10,
        status="Pending Decision"
    )
    res = calculate_route_options(sample_product, ret, sample_inventory, sample_refurb_rule, sample_vendor_term, sample_liq_rule)
    liq = res.routes["Liquidation"]
    # 35% of cost 1400 = 490 per unit
    assert liq.is_eligible is True
    assert liq.recovery_per_unit == 490.0
    assert liq.net_recovery == 4900.0

def test_vendor_return_window_expired(sample_product, sample_inventory, sample_refurb_rule, sample_vendor_term, sample_liq_rule):
    ret = Return(
        id=5,
        return_date=date.today() - timedelta(days=35),  # 35 days old > 30-day window
        sku="TEST-SKU-01",
        supplier_batch="B-05",
        reason_code="Defective",
        grade="B",
        quantity=10,
        status="Pending Decision"
    )
    res = calculate_route_options(sample_product, ret, sample_inventory, sample_refurb_rule, sample_vendor_term, sample_liq_rule)
    rtv = res.routes["Vendor Return"]
    assert rtv.is_eligible is False
    assert "expired" in rtv.ineligibility_reason.lower()
