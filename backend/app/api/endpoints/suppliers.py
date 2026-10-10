from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.models import Supplier, SupplierAlert, Return, Product, Sale
from app.schemas.schemas import SupplierResponse, SupplierAlertResponse, BatchIntelligenceResponse
from app.intelligence.detectors import get_batch_intelligence

router = APIRouter()

@router.get("/suppliers", response_model=List[SupplierResponse])
def get_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).all()

@router.get("/suppliers/alerts", response_model=List[SupplierAlertResponse])
def get_supplier_alerts(db: Session = Depends(get_db)):
    alerts = (
        db.query(SupplierAlert, Supplier)
        .join(Supplier, SupplierAlert.supplier_id == Supplier.id)
        .all()
    )
    result = []
    for alert, supp in alerts:
        result.append(SupplierAlertResponse(
            id=alert.id,
            supplier_id=alert.supplier_id,
            supplier_name=supp.supplier_name,
            sku=alert.sku,
            supplier_batch=alert.supplier_batch,
            alert_type=alert.alert_type,
            observed_return_rate=alert.observed_return_rate,
            baseline_return_rate=alert.baseline_return_rate,
            evidence=alert.evidence or {},
            severity=alert.severity,
            status=alert.status,
            created_at=alert.created_at
        ))
    return result

@router.get("/suppliers/batches/{batch_id}", response_model=BatchIntelligenceResponse)
def get_batch_detail(batch_id: str, db: Session = Depends(get_db)):
    intel = get_batch_intelligence(db, batch_id)
    if not intel:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")
    return intel

@router.get("/suppliers/{supplier_id}")
def get_supplier_by_id(supplier_id: int, db: Session = Depends(get_db)):
    supp = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supp:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    products = db.query(Product).filter(Product.supplier_id == supplier_id).all()
    alerts = db.query(SupplierAlert).filter(SupplierAlert.supplier_id == supplier_id).all()
    
    # Calculate return rate
    skus = [p.sku for p in products]
    total_sales = db.query(Sale).filter(Sale.sku.in_(skus)).all()
    total_sold = sum(s.quantity_sold for s in total_sales)
    
    returns = db.query(Return).filter(Return.sku.in_(skus)).all()
    total_returned = sum(r.quantity for r in returns)
    
    return_rate = round((total_returned / total_sold * 100.0), 2) if total_sold > 0 else 0.0
    
    return {
        "supplier": supp,
        "product_count": len(products),
        "total_sold": total_sold,
        "total_returned": total_returned,
        "overall_return_rate": return_rate,
        "active_alerts": alerts
    }
