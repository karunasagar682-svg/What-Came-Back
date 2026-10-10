from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from app.core.database import get_db
from app.models.models import (
    Return,
    Product,
    Supplier,
    Inventory,
    RefurbishmentRule,
    VendorTerm,
    LiquidationRule,
)
from app.schemas.schemas import RouteComparisonResult, SplitBatchRequest, SplitBatchResponse
from app.engine.calculator import calculate_route_options, evaluate_split_plan

router = APIRouter()


def _get_vendor_term(db: Session, product: Product) -> Optional[VendorTerm]:
    """Prefer a product/SKU-specific vendor term, then use a supplier-wide term."""
    sku_term = (
        db.query(VendorTerm)
        .filter(
            VendorTerm.supplier_id == product.supplier_id,
            VendorTerm.sku == product.sku,
        )
        .first()
    )
    if sku_term:
        return sku_term

    return (
        db.query(VendorTerm)
        .filter(
            VendorTerm.supplier_id == product.supplier_id,
            VendorTerm.sku.is_(None),
        )
        .first()
    )


def _get_recovery_context(db: Session, ret: Return, prod: Product):
    """Load the existing recovery rules used by both analysis endpoints."""
    inventory = db.query(Inventory).filter(Inventory.sku == prod.sku).first()
    refurb_rule = (
        db.query(RefurbishmentRule)
        .filter(RefurbishmentRule.category == prod.category)
        .first()
    )
    vendor_term = _get_vendor_term(db, prod)
    liquidation_rule = (
        db.query(LiquidationRule)
        .filter(
            LiquidationRule.category == prod.category,
            LiquidationRule.grade == ret.grade,
        )
        .first()
    )
    return inventory, refurb_rule, vendor_term, liquidation_rule


@router.post("/recovery/analyze", response_model=RouteComparisonResult)
def analyze_recovery(payload: Dict[str, Any], db: Session = Depends(get_db)):
    return_id = payload.get("return_id")
    if not return_id:
        raise HTTPException(status_code=400, detail="return_id is required.")

    ret = db.query(Return).filter(Return.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail=f"Return #{return_id} not found.")

    prod = db.query(Product).filter(Product.sku == ret.sku).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found.")

    inventory, refurb_rule, vendor_term, liquidation_rule = _get_recovery_context(
        db, ret, prod
    )

    # Let the calculation engine determine vendor eligibility from the actual
    # vendor terms and return date; do not special-case a particular batch.
    return calculate_route_options(
        prod,
        ret,
        inventory,
        refurb_rule,
        vendor_term,
        liquidation_rule,
    )


@router.post("/recovery/compare")
def compare_routes(payload: Dict[str, Any], db: Session = Depends(get_db)):
    # Keep the existing comparison response shape for the frontend.
    return_id = payload.get("return_id")
    if not return_id:
        raise HTTPException(status_code=400, detail="return_id is required.")

    analysis = analyze_recovery({"return_id": return_id}, db)
    return {
        "sku": analysis.sku,
        "quantity": analysis.quantity,
        "recommended_route": analysis.recommended_route,
        "recommendation_reason": analysis.recommendation_reason,
        "routes": analysis.routes,
        "incremental_over_liquidation": analysis.incremental_recovery_over_liquidation,
    }


@router.post("/recovery/split-plan", response_model=SplitBatchResponse)
def simulate_split_plan(req: SplitBatchRequest, db: Session = Depends(get_db)):
    ret = None
    if req.return_id:
        ret = db.query(Return).filter(Return.id == req.return_id).first()
    elif req.supplier_batch:
        ret = (
            db.query(Return)
            .filter(Return.supplier_batch == req.supplier_batch)
            .order_by(Return.id.asc())
            .first()
        )

    if not ret:
        raise HTTPException(status_code=404, detail="Return or batch not found.")

    prod = db.query(Product).filter(Product.sku == ret.sku).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Associated product not found.")

    inventory, refurb_rule, vendor_term, liquidation_rule = _get_recovery_context(
        db, ret, prod
    )
    allocations = [
        {"route": allocation.route, "quantity": allocation.quantity}
        for allocation in req.allocations
    ]

    # None allows the engine to calculate the eligible quantity from the real
    # vendor window. A hardcoded batch quota could incorrectly permit/deny RTV.
    return evaluate_split_plan(
        product=prod,
        return_item=ret,
        inventory=inventory,
        refurb_rule=refurb_rule,
        vendor_term=vendor_term,
        liq_rule=liquidation_rule,
        allocations=allocations,
        max_vendor_eligible_qty=None,
    )
