import pytest
from datetime import date, timedelta
from app.models.models import Product, Return, Inventory, RefurbishmentRule, VendorTerm, LiquidationRule
from app.engine.calculator import calculate_route_options, evaluate_split_plan

def test_reference_40_headphone_scenario():
    """
    Regression test for the required reference scenario from the specification:
    - 40 Grade-B wireless headphones
    - New selling price: ₹2,500
    - Product cost: ₹1,400
    - Refurbishment cost: ₹250
    - Refurbishment duration: 5 days
    - Refurbished resale price: 75% of new price (₹1,875)
    - Vendor credit: 60% of applicable price (₹1,500)
    - Vendor-return window: 30 days
    - Units still eligible for vendor return: 24
    - Liquidation recovery: 35% of cost (₹490)
    - Existing new-stock coverage: 60 days
    """
    prod = Product(
        id=1,
        sku="WH-1000XM-B",
        name="AeroSound Elite Wireless Headphones",
        category="Headphones",
        cost_price=1400.0,
        selling_price=2500.0,
        supplier_id=1
    )
    inv = Inventory(
        id=1,
        sku="WH-1000XM-B",
        new_stock=600,
        avg_daily_demand=10.0  # 600 / 10 = 60 days
    )
    refurb_rule = RefurbishmentRule(
        id=1,
        category="Headphones",
        refurbishment_cost=250.0,
        days_required=5,
        resale_percentage_of_new_price=75.0
    )
    vendor_term = VendorTerm(
        id=1,
        supplier_id=1,
        sku="WH-1000XM-B",
        rtv_allowed=True,
        credit_percentage=60.0,
        window_days=30
    )
    liq_rule = LiquidationRule(
        id=1,
        category="Headphones",
        grade="B",
        recovery_percentage_of_cost=35.0
    )
    
    ret_item = Return(
        id=101,
        return_date=date.today() - timedelta(days=18),
        sku="WH-1000XM-B",
        supplier_batch="HB-09",
        reason_code="Audio Driver Hiss / Bluetooth Drop",
        grade="B",
        quantity=40,
        status="Pending Decision"
    )
    
    # 1. Test calculation engine output
    analysis = calculate_route_options(
        product=prod,
        return_item=ret_item,
        inventory=inv,
        refurb_rule=refurb_rule,
        vendor_term=vendor_term,
        liq_rule=liq_rule,
        vendor_eligible_quantity=24
    )
    
    # Verify Route Values
    # Refurb unit net = 2500 * 0.75 - 250 = 1875 - 250 = 1625
    assert analysis.routes["Refurbish"].recovery_per_unit == 1625.0
    # Vendor unit credit = 2500 * 0.60 = 1500
    assert analysis.routes["Vendor Return"].recovery_per_unit == 1500.0
    assert analysis.routes["Vendor Return"].net_recovery == 36000.0  # 24 * 1500
    # Liquidation unit = 1400 * 0.35 = 490
    assert analysis.routes["Liquidation"].recovery_per_unit == 490.0
    assert analysis.routes["Liquidation"].net_recovery == 19600.0   # 40 * 490
    
    # Verify split recommendation
    assert analysis.is_split_recommended is True
    assert analysis.recommended_route == "Split-Batch"
    
    # 2. Test Split-Batch Allocation (24 Vendor Return + 16 Refurbish)
    allocations = [
        {"route": "Vendor Return", "quantity": 24},
        {"route": "Refurbish", "quantity": 16}
    ]
    
    split_result = evaluate_split_plan(
        product=prod,
        return_item=ret_item,
        inventory=inv,
        refurb_rule=refurb_rule,
        vendor_term=vendor_term,
        liq_rule=liq_rule,
        allocations=allocations,
        max_vendor_eligible_qty=24
    )
    
    assert split_result.is_valid is True
    assert split_result.total_allocated == 40
    assert split_result.remaining_unallocated == 0
    
    # 24 * 1500 = 36000
    # 16 * 1625 = 26000
    # Total = 62000
    assert split_result.total_net_recovery == 62000.0
    assert split_result.all_liquidation_recovery == 19600.0
    # Incremental gain = 62000 - 19600 = +42400
    assert split_result.incremental_gain_over_liquidation == 42400.0

def test_split_plan_over_allocation_rejected():
    """Validates that assigning > 40 units is rejected."""
    prod = Product(id=1, sku="WH-1000XM-B", name="Headphones", category="Headphones", cost_price=1400.0, selling_price=2500.0, supplier_id=1)
    ret_item = Return(id=101, return_date=date.today(), sku="WH-1000XM-B", supplier_batch="HB-09", reason_code="Audio Defect", grade="B", quantity=40, status="Pending Decision")
    
    allocations = [
        {"route": "Vendor Return", "quantity": 25},  # Exceeds vendor limit of 24!
        {"route": "Refurbish", "quantity": 20}       # Sum = 45 > 40!
    ]
    
    split_result = evaluate_split_plan(
        product=prod,
        return_item=ret_item,
        inventory=None,
        refurb_rule=None,
        vendor_term=None,
        liq_rule=None,
        allocations=allocations,
        max_vendor_eligible_qty=24
    )
    
    assert split_result.is_valid is False
    assert len(split_result.validation_errors) > 0
