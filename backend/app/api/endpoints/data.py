import io
import csv
from datetime import datetime, date
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.core.database import get_db
from app.models.models import (
    Product, Supplier, Return, Inventory, ActivityLog
)
from app.schemas.schemas import CsvImportResult
from app.seed.seed_data import seed_demo_database

router = APIRouter()

TEMPLATES = {
    "products": "sku,name,category,cost_price,selling_price,supplier_id\nWH-PRO-01,Pro Wireless Headphones,Headphones,1400.0,2500.0,1\nCAM-MINI-01,Mini Action Cam,Cameras,8000.0,12000.0,2",
    "returns": "return_date,sku,supplier_batch,reason_code,grade,quantity,status\n2026-10-01,WH-PRO-01,HB-09,Audio Driver Hiss,B,10,Pending Decision\n2026-10-02,CAM-MINI-01,CM-01,Lens Scratch,C,5,Pending Decision",
    "suppliers": "supplier_name,contact_email,status\nTechSupplies Inc,contact@techsupplies.com,Active\nApex Audio Ltd,returns@apexaudio.com,Active",
    "inventory": "sku,new_stock,avg_daily_demand\nWH-PRO-01,300,10.0\nCAM-MINI-01,45,1.5"
}

@router.get("/data/templates")
def get_templates():
    return TEMPLATES

@router.post("/data/seed-demo")
def trigger_demo_seed(db: Session = Depends(get_db)):
    # Clear and re-seed database
    from app.core.database import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    result = seed_demo_database(db)
    return {"message": "Demo scenario loaded successfully", "result": result}

@router.post("/data/import", response_model=CsvImportResult)
async def import_csv_dataset(
    entity_type: str = Form(...),  # products, returns, suppliers, inventory
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    entity_type = entity_type.lower().strip()
    contents = await file.read()
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        decoded = contents.decode("latin-1")
        
    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Empty or invalid CSV file.")
        
    headers = [h.strip() for h in reader.fieldnames]
    rows = list(reader)
    
    total = len(rows)
    successful = 0
    failed = 0
    errors: List[str] = []
    
    # Validation per entity
    if entity_type == "products":
        required = {"sku", "name", "category", "cost_price", "selling_price", "supplier_id"}
        missing = required - set(headers)
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required columns for products: {', '.join(missing)}")
            
        for idx, row in enumerate(rows, 1):
            try:
                sku = row["sku"].strip()
                name = row["name"].strip()
                cat = row["category"].strip()
                cost = float(row["cost_price"])
                selling = float(row["selling_price"])
                supp_id = int(row["supplier_id"])
                
                # Check supplier exists
                supp = db.query(Supplier).filter(Supplier.id == supp_id).first()
                if not supp:
                    errors.append(f"Row {idx}: Supplier ID {supp_id} does not exist.")
                    failed += 1
                    continue
                    
                prod = db.query(Product).filter(Product.sku == sku).first()
                if prod:
                    prod.name = name
                    prod.category = cat
                    prod.cost_price = cost
                    prod.selling_price = selling
                    prod.supplier_id = supp_id
                else:
                    db.add(Product(
                        sku=sku, name=name, category=cat,
                        cost_price=cost, selling_price=selling, supplier_id=supp_id
                    ))
                successful += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
                failed += 1
                
    elif entity_type == "returns":
        required = {"return_date", "sku", "supplier_batch", "reason_code", "grade", "quantity"}
        missing = required - set(headers)
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required columns for returns: {', '.join(missing)}")
            
        for idx, row in enumerate(rows, 1):
            try:
                sku = row["sku"].strip()
                prod = db.query(Product).filter(Product.sku == sku).first()
                if not prod:
                    errors.append(f"Row {idx}: Product with SKU '{sku}' does not exist.")
                    failed += 1
                    continue
                    
                r_date = datetime.strptime(row["return_date"].strip(), "%Y-%m-%d").date()
                grade = row["grade"].strip().upper()
                if grade not in ["A", "B", "C", "D"]:
                    errors.append(f"Row {idx}: Invalid grade '{grade}'. Must be A, B, C, or D.")
                    failed += 1
                    continue
                    
                qty = int(row["quantity"])
                batch = row["supplier_batch"].strip()
                reason = row["reason_code"].strip()
                status = row.get("status", "Pending Decision").strip()
                
                db.add(Return(
                    return_date=r_date,
                    sku=sku,
                    supplier_batch=batch,
                    reason_code=reason,
                    grade=grade,
                    quantity=qty,
                    status=status,
                    received_at=datetime.utcnow()
                ))
                successful += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
                failed += 1
                
    elif entity_type == "suppliers":
        required = {"supplier_name", "contact_email"}
        missing = required - set(headers)
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required columns for suppliers: {', '.join(missing)}")
            
        for idx, row in enumerate(rows, 1):
            try:
                s_name = row["supplier_name"].strip()
                s_email = row["contact_email"].strip()
                s_status = row.get("status", "Active").strip()
                
                supp = db.query(Supplier).filter(Supplier.supplier_name == s_name).first()
                if supp:
                    supp.contact_email = s_email
                    supp.status = s_status
                else:
                    db.add(Supplier(supplier_name=s_name, contact_email=s_email, status=s_status))
                successful += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
                failed += 1
                
    elif entity_type == "inventory":
        required = {"sku", "new_stock", "avg_daily_demand"}
        missing = required - set(headers)
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required columns for inventory: {', '.join(missing)}")
            
        for idx, row in enumerate(rows, 1):
            try:
                sku = row["sku"].strip()
                stock = int(row["new_stock"])
                demand = float(row["avg_daily_demand"])
                
                inv = db.query(Inventory).filter(Inventory.sku == sku).first()
                if inv:
                    inv.new_stock = stock
                    inv.avg_daily_demand = demand
                else:
                    db.add(Inventory(sku=sku, new_stock=stock, avg_daily_demand=demand))
                successful += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
                failed += 1
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported entity type '{entity_type}'. Must be products, returns, suppliers, or inventory.")

    db.commit()
    
    # Audit log
    db.add(ActivityLog(
        actor="Data Manager",
        action="CSV_IMPORT",
        entity_type=entity_type,
        entity_id="BULK",
        details={"total": total, "successful": successful, "failed": failed}
    ))
    db.commit()

    return CsvImportResult(
        entity=entity_type,
        total_rows=total,
        successful_rows=successful,
        failed_rows=failed,
        errors=errors[:10]  # Return top 10 row errors
    )
