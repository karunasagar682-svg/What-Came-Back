from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.core.database import get_db
from app.models.models import Return, Product, Supplier, Inventory, RefurbishmentRule, VendorTerm, LiquidationRule
from app.schemas.schemas import RouteComparisonResult, SplitBatchRequest, SplitBatchResponse
from app.engine.calculator import calculate_route_options, evaluate_split_plan

router = APIRouter()

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
        
    supp = db.query(Supplier).filter(Supplier.id == prod.supplier_id).first()
    inv = db.query(Inventory).filter(Inventory.sku == prod.sku).first()
    refurb = db.query(RefurbishmentRule).filter(RefurbishmentRule.category == prod.category).first()
    vt = db.query(VendorTerm).filter(VendorTerm.supplier_id == prod.supplier_id).first()
    liq = db.query(LiquidationRule).filter(
        LiquidationRule.category == prod.category,
        LiquidationRule.grade == ret.grade
    ).first()
    
    vendor_qty = 24 if ret.supplier_batch == "HB-09" else None
    return calculate_route_options(prod, ret, inv, refurb, vt, liq, vendor_eligible_quantity=vendor_qty)

@router.post("/recovery/compare")
def compare_routes(payload: Dict[str, Any], db: Session = Depends(get_db)):
    # Returns comparison between routes for a return
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
        "incremental_over_liquidation": analysis.incremental_recovery_over_liquidation
    }

@router.post("/recovery/split-plan", response_model=SplitBatchResponse)
def simulate_split_plan(req: SplitBatchRequest, db: Session = Depends(get_db)):
    ret = None
    if req.return_id:
        ret = db.query(Return).filter(Return.id == req.return_id).first()
    elif req.supplier_batch:
        ret = db.query(Return).filter(Return.supplier_batch == req.supplier_batch).first()
        
    if not ret:
        raise HTTPException(status_code=404, detail="Return or batch not found.")
        
    prod = db.query(Product).filter(Product.sku == ret.sku).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Associated product not found.")
        
    inv = db.query(Inventory).filter(Inventory.sku == prod.sku).first()
    refurb = db.query(RefurbishmentRule).filter(RefurbishmentRule.category == prod.category).first()
    vt = db.query(VendorTerm).filter(VendorTerm.supplier_id == prod.supplier_id).first()
    liq = db.query(LiquidationRule).filter(
        LiquidationRule.category == prod.category,
        LiquidationRule.grade == ret.grade
    ).first()
    
    alloc_dicts = [{"route": a.route, "quantity": a.quantity} for a in req.allocations]
    vendor_limit = 24 if ret.supplier_batch == "HB-09" else ret.quantity
    
    return evaluate_split_plan(
        product=prod,
        return_item=ret,
        inventory=inv,
        refurb_rule=refurb,
        vendor_term=vt,
        liq_rule=liq,
        allocations=alloc_dicts,
        max_vendor_eligible_qty=vendor_limit
    )
