from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.core.database import get_db
from app.models.models import Return, Product, SupplierAlert, ProposedAction, Inventory, RefurbishmentRule, VendorTerm, LiquidationRule
from app.intelligence.detectors import (
    get_all_priority_issues,
    detect_high_value_waiting_too_long,
    detect_expiring_vendor_windows
)
from app.engine.calculator import calculate_route_options
from app.schemas.schemas import DashboardSummaryResponse, PriorityItem

router = APIRouter()


def get_vendor_term_for_product(db: Session, supplier_id: int, sku: str):
    """Prefer SKU-specific vendor terms, then use supplier-wide terms."""
    sku_term = (
        db.query(VendorTerm)
        .filter(
            VendorTerm.supplier_id == supplier_id,
            VendorTerm.sku == sku,
        )
        .first()
    )
    if sku_term:
        return sku_term

    return (
        db.query(VendorTerm)
        .filter(
            VendorTerm.supplier_id == supplier_id,
            VendorTerm.sku.is_(None),
        )
        .first()
    )


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    # 1. Total awaiting decision
    pending_returns = db.query(Return).filter(Return.status == "Pending Decision").all()
    total_awaiting = sum(r.quantity for r in pending_returns)

    # 2. Total recoverable value & recovery by route
    total_recoverable = 0.0
    returns_by_grade = {"A": 0, "B": 0, "C": 0, "D": 0}
    returns_by_route = {}
    return_reasons = {}
    route_values = {}

    for r in pending_returns:
        returns_by_grade[r.grade] = returns_by_grade.get(r.grade, 0) + r.quantity
        return_reasons[r.reason_code] = return_reasons.get(r.reason_code, 0) + r.quantity

        prod = db.query(Product).filter(Product.sku == r.sku).first()
        if not prod:
            continue

        inv = db.query(Inventory).filter(Inventory.sku == prod.sku).first()
        refurb = (
            db.query(RefurbishmentRule)
            .filter(RefurbishmentRule.category == prod.category)
            .first()
        )
        vt = get_vendor_term_for_product(db, prod.supplier_id, prod.sku)
        liq = db.query(LiquidationRule).filter(
            LiquidationRule.category == prod.category,
            LiquidationRule.grade == r.grade
        ).first()

        # Vendor eligibility is evaluated by the recovery calculator using
        # the actual vendor terms and return age, not a hardcoded batch rule.
        analysis = calculate_route_options(prod, r, inv, refurb, vt, liq)

        rec_route = analysis.recommended_route
        returns_by_route[rec_route] = returns_by_route.get(rec_route, 0) + r.quantity

        # Calculate net recovery value
        rec_net = 0.0
        if rec_route == "Split-Batch" and analysis.split_recommendation_details:
            rec_net = analysis.split_recommendation_details["total_split_net"]
        elif rec_route in analysis.routes:
            rec_net = analysis.routes[rec_route].net_recovery

        total_recoverable += rec_net
        route_values[rec_route] = route_values.get(rec_route, 0.0) + rec_net

    # 3. High priority count & urgent priorities
    all_issues = get_all_priority_issues(db)
    high_priority_count = len([i for i in all_issues if i.severity in ["Critical", "High"]])

    # 4. Expiring vendor windows
    expiring_count = len(detect_expiring_vendor_windows(db))

    # 5. Supplier alerts count
    supplier_alerts_count = db.query(SupplierAlert).filter(SupplierAlert.status == "Active").count()

    # 6. Pending approvals count
    pending_approvals_count = db.query(ProposedAction).filter(ProposedAction.status == "Pending").count()

    # Top 3 for "What Needs Your Attention Today?"
    urgent_top_3 = all_issues[:3]

    return DashboardSummaryResponse(
        total_awaiting_decision=total_awaiting,
        total_recoverable_value=round(total_recoverable, 2),
        high_priority_issues_count=high_priority_count,
        expiring_vendor_windows_count=expiring_count,
        supplier_alerts_count=supplier_alerts_count,
        pending_approvals_count=pending_approvals_count,
        returns_by_grade=returns_by_grade,
        returns_by_route=returns_by_route,
        return_reasons=return_reasons,
        recovery_performance_by_route={k: round(v, 2) for k, v in route_values.items()},
        urgent_priorities=urgent_top_3
    )


@router.get("/dashboard/priorities", response_model=List[PriorityItem])
def get_dashboard_priorities(db: Session = Depends(get_db)):
    return get_all_priority_issues(db)
