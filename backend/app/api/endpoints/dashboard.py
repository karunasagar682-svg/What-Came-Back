from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import (
    Return,
    Product,
    SupplierAlert,
    ProposedAction,
    Inventory,
    RefurbishmentRule,
    VendorTerm,
    LiquidationRule,
)
from app.intelligence.detectors import get_all_priority_issues, detect_expiring_vendor_windows
from app.engine.calculator import calculate_route_options
from app.schemas.schemas import DashboardSummaryResponse, PriorityItem

router = APIRouter()


def get_vendor_term_for_product(db: Session, supplier_id: int, sku: str):
    """Prefer SKU-specific vendor terms, then fall back to supplier-wide terms."""
    sku_term = (
        db.query(VendorTerm)
        .filter(VendorTerm.supplier_id == supplier_id, VendorTerm.sku == sku)
        .first()
    )
    if sku_term:
        return sku_term
    return (
        db.query(VendorTerm)
        .filter(VendorTerm.supplier_id == supplier_id, VendorTerm.sku.is_(None))
        .first()
    )


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    # Keep the same pending-return definition and dashboard metrics.
    pending_returns = (
        db.query(Return).filter(Return.status == "Pending Decision").all()
    )
    total_awaiting = sum(r.quantity for r in pending_returns)

    # Load reference tables once instead of issuing several queries per return.
    # The recovery calculator and its recommendations remain unchanged.
    products_by_sku = {p.sku: p for p in db.query(Product).all()}
    inventory_by_sku = {i.sku: i for i in db.query(Inventory).all()}
    refurb_by_category = {r.category: r for r in db.query(RefurbishmentRule).all()}
    vendor_terms_by_key = {
        (term.supplier_id, term.sku): term for term in db.query(VendorTerm).all()
    }
    liquidation_by_key = {
        (rule.category, rule.grade): rule for rule in db.query(LiquidationRule).all()
    }

    total_recoverable = 0.0
    returns_by_grade = {"A": 0, "B": 0, "C": 0, "D": 0}
    returns_by_route = {}
    return_reasons = {}
    route_values = {}

    for r in pending_returns:
        returns_by_grade[r.grade] = returns_by_grade.get(r.grade, 0) + r.quantity
        return_reasons[r.reason_code] = return_reasons.get(r.reason_code, 0) + r.quantity

        prod = products_by_sku.get(r.sku)
        if not prod:
            continue

        inv = inventory_by_sku.get(prod.sku)
        refurb = refurb_by_category.get(prod.category)
        vt = vendor_terms_by_key.get((prod.supplier_id, prod.sku))
        if vt is None:
            vt = vendor_terms_by_key.get((prod.supplier_id, None))
        liq = liquidation_by_key.get((prod.category, r.grade))

        analysis = calculate_route_options(prod, r, inv, refurb, vt, liq)
        rec_route = analysis.recommended_route
        returns_by_route[rec_route] = returns_by_route.get(rec_route, 0) + r.quantity

        rec_net = 0.0
        if rec_route == "Split-Batch" and analysis.split_recommendation_details:
            rec_net = analysis.split_recommendation_details["total_split_net"]
        elif rec_route in analysis.routes:
            rec_net = analysis.routes[rec_route].net_recovery

        total_recoverable += rec_net
        route_values[rec_route] = route_values.get(rec_route, 0.0) + rec_net

    all_issues = get_all_priority_issues(db)
    high_priority_count = sum(
        1 for issue in all_issues if issue.severity in ["Critical", "High"]
    )
    expiring_count = len(detect_expiring_vendor_windows(db))
    supplier_alerts_count = (
        db.query(SupplierAlert).filter(SupplierAlert.status == "Active").count()
    )
    pending_approvals_count = (
        db.query(ProposedAction).filter(ProposedAction.status == "Pending").count()
    )

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
        urgent_priorities=all_issues[:3],
    )


@router.get("/dashboard/priorities", response_model=List[PriorityItem])
def get_dashboard_priorities(db: Session = Depends(get_db)):
    return get_all_priority_issues(db)
