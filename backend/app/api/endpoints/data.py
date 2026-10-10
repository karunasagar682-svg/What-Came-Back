```python
import io
import csv
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import (
    Product, Supplier, Return, Inventory, ActivityLog,
    Sale, VendorTerm, RefurbishmentRule, LiquidationRule
)
from app.schemas.schemas import CsvImportResult
from app.seed.seed_data import seed_demo_database

router = APIRouter()

TEMPLATES = {
    "products": "sku,name,category,cost_price,selling_price,supplier_id\nWH-PRO-01,Pro Wireless Headphones,Headphones,1400.0,2500.0,1",
    "returns": "return_date,sku,supplier_batch,reason_code,grade,quantity,status\n2026-10-01,WH-PRO-01,HB-09,Audio Driver Hiss,B,10,Pending Decision",
    "suppliers": "supplier_name,contact_email,status\nTechSupplies Inc,contact@techsupplies.com,Active",
    "inventory": "sku,new_stock,avg_daily_demand\nWH-PRO-01,300,10.0",
    "vendor_terms": "supplier,sku,rtv_allowed,credit_pct,window_days\nTechLink Distributors,GB-001,Yes,0.60,30",
    "refurbishment": "category,refurb_cost,days_required,resale_pct_of_new\nHeadphones,150,3,0.65",
    "liquidation": "category,condition_grade,recovery_pct_of_cost\nHeadphones,B,0.30",
    "sales": "date,sku,qty_sold,selling_price\n2026-10-01,WH-PRO-01,10,2500"
}


def normalize_headers(row):
    """Normalize CSV header names and cell values."""
    return {
        str(key).strip().lower().lstrip("\ufeff"):
        str(value or "").strip()
        for key, value in row.items()
        if key is not None
    }


def parse_date(value):
    """Parse supported dataset date formats."""
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue

    raise ValueError(f"Invalid date '{value}'.")


def parse_bool(value):
    value = str(value).strip().lower()

    if value in {"yes", "true", "1", "y"}:
        return True

    if value in {"no", "false", "0", "n"}:
        return False

    raise ValueError(f"Invalid boolean value '{value}'.")


def normalize_percentage(value):
    """
    Dataset fractions such as 0.60 mean 60%.
    Preserve values already expressed as 60.
    """
    value = float(value)

    if value < 0 or value > 100:
        raise ValueError("Percentage must be between 0 and 100.")

    return value * 100 if value <= 1 else value


def get_or_create_supplier(db, supplier_name):
    supplier_name = supplier_name.strip()

    if not supplier_name:
        raise ValueError("Supplier name cannot be empty.")

    supplier = (
        db.query(Supplier)
        .filter(Supplier.supplier_name == supplier_name)
        .first()
    )

    if not supplier:
        supplier = Supplier(
            supplier_name=supplier_name,
            contact_email="not-provided@example.invalid",
            status="Active"
        )
        db.add(supplier)
        db.flush()

    return supplier


@router.get("/data/templates")
def get_templates():
    return TEMPLATES


@router.post("/data/seed-demo")
def trigger_demo_seed(db: Session = Depends(get_db)):
    # Existing demo reset behavior retained.
    from app.core.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    result = seed_demo_database(db)

    return {
        "message": "Demo scenario loaded successfully",
        "result": result
    }


@router.post("/data/import", response_model=CsvImportResult)
async def import_csv_dataset(
    entity_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    entity_type = entity_type.lower().strip()

    supported_entities = {
        "products", "returns", "suppliers", "inventory",
        "vendor_terms", "refurbishment", "liquidation", "sales"
    }

    if entity_type not in supported_entities:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported entity type '{entity_type}'."
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="CSV file is empty.")

    try:
        decoded = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = contents.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))

    if not reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="Empty or invalid CSV file."
        )

    headers = {
        h.strip().lower().lstrip("\ufeff")
        for h in reader.fieldnames if h
    }

    rows = [
        normalize_headers(row)
        for row in reader
        if any(str(v or "").strip() for v in row.values())
    ]

    total = len(rows)
    successful = 0
    failed = 0
    errors = []

    # PRODUCTS
    if entity_type == "products":
        organizer_format = "product" in headers and "supplier" in headers

        required = (
            {"sku", "product", "category", "cost_price",
             "selling_price", "supplier"}
            if organizer_format else
            {"sku", "name", "category", "cost_price",
             "selling_price", "supplier_id"}
        )

        missing = required - headers

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing product columns: {', '.join(sorted(missing))}"
            )

        for idx, row in enumerate(rows, 2):
            try:
                with db.begin_nested():
                    sku = row["sku"]
                    name = row.get("product") or row.get("name")
                    category = row["category"]
                    cost = float(row["cost_price"])
                    selling = float(row["selling_price"])

                    if not sku or not name:
                        raise ValueError("SKU and product name are required.")

                    if cost < 0 or selling < 0:
                        raise ValueError("Prices cannot be negative.")

                    if organizer_format:
                        supplier = get_or_create_supplier(db, row["supplier"])
                        supplier_id = supplier.id
                    else:
                        supplier_id = int(row["supplier_id"])

                        supplier = db.query(Supplier).filter(
                            Supplier.id == supplier_id
                        ).first()

                        if not supplier:
                            raise ValueError(
                                f"Supplier ID {supplier_id} does not exist."
                            )

                    product = db.query(Product).filter(
                        Product.sku == sku
                    ).first()

                    if product:
                        product.name = name
                        product.category = category
                        product.cost_price = cost
                        product.selling_price = selling
                        product.supplier_id = supplier_id
                    else:
                        db.add(Product(
                            sku=sku,
                            name=name,
                            category=category,
                            cost_price=cost,
                            selling_price=selling,
                            supplier_id=supplier_id
                        ))

                successful += 1

            except Exception as exc:
                failed += 1
                errors.append(f"Row {idx}: {str(exc)}")

    # RETURNS
    elif entity_type == "returns":
        organizer_format = {
            "return_id", "date_received", "sku",
            "supplier_batch", "reason_code",
            "condition_grade", "status"
        }.issubset(headers)

        required = (
            {"return_id", "date_received", "sku", "supplier_batch",
             "reason_code", "condition_grade", "status"}
            if organizer_format else
            {"return_date", "sku", "supplier_batch",
             "reason_code", "grade", "quantity"}
        )

        missing = required - headers

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing return columns: {', '.join(sorted(missing))}"
            )

        status_mapping = {
            "awaiting decision": "Pending Decision",
            "pending decision": "Pending Decision",
            "processed": "Completed",
            "completed": "Completed",
            "queued for liquidation": "Queued for Liquidation",
            "in refurbishment queue": "In Refurbishment Queue",
            "in process": "In Process"
        }

        for idx, row in enumerate(rows, 2):
            try:
                with db.begin_nested():
                    sku = row["sku"]

                    product = db.query(Product).filter(
                        Product.sku == sku
                    ).first()

                    if not product:
                        raise ValueError(
                            f"Product SKU '{sku}' does not exist. "
                            "Import products first."
                        )

                    r_date = parse_date(
                        row.get("date_received") or row.get("return_date")
                    )

                    grade = (
                        row.get("condition_grade") or row.get("grade")
                    ).upper()

                    if grade not in {"A", "B", "C", "D"}:
                        raise ValueError(f"Invalid grade '{grade}'.")

                    quantity = (
                        1 if organizer_format
                        else int(row["quantity"])
                    )

                    if quantity <= 0:
                        raise ValueError("Quantity must be positive.")

                    raw_status = row.get("status") or "Pending Decision"
                    status = status_mapping.get(raw_status.lower())

                    if not status:
                        raise ValueError(
                            f"Unsupported return status '{raw_status}'."
                        )

                    return_id = (
                        int(row["return_id"])
                        if organizer_format else None
                    )

                    ret = None

                    if return_id is not None:
                        ret = db.query(Return).filter(
                            Return.id == return_id
                        ).first()

                    values = {
                        "return_date": r_date,
                        "sku": sku,
                        "supplier_batch": row["supplier_batch"],
                        "reason_code": row["reason_code"],
                        "grade": grade,
                        "quantity": quantity,
                        "status": status
                    }

                    if ret:
                        for key, value in values.items():
                            setattr(ret, key, value)
                    else:
                        values["received_at"] = datetime.utcnow()

                        if return_id is not None:
                            values["id"] = return_id

                        db.add(Return(**values))

                successful += 1

            except Exception as exc:
                failed += 1
                errors.append(f"Row {idx}: {str(exc)}")

    # SUPPLIERS
    elif entity_type == "suppliers":
        required = {"supplier_name", "contact_email"}
        missing = required - headers

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing supplier columns: {', '.join(sorted(missing))}"
            )

        for idx, row in enumerate(rows, 2):
            try:
                with db.begin_nested():
                    name = row["supplier_name"]
                    email = row["contact_email"]

                    supplier = db.query(Supplier).filter(
                        Supplier.supplier_name == name
                    ).first()

                    if supplier:
                        supplier.contact_email = email
                        supplier.status = row.get("status") or "Active"
                    else:
                        db.add(Supplier(
                            supplier_name=name,
                            contact_email=email,
                            status=row.get("status") or "Active"
                        ))

                successful += 1

            except Exception as exc:
                failed += 1
                errors.append(f"Row {idx}: {str(exc)}")

    # INVENTORY
    elif entity_type == "inventory":
        required = {"sku", "new_stock", "avg_daily_demand"}
        missing = required - headers

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing inventory columns: {', '.join(sorted(missing))}"
            )

        for idx, row in enumerate(rows, 2):
            try:
                with db.begin_nested():
                    sku = row["sku"]
                    stock = int(row["new_stock"])
                    demand = float(row["avg_daily_demand"])

                    if stock < 0 or demand < 0:
                        raise ValueError("Stock and demand cannot be negative.")

                    if not db.query(Product).filter(
                        Product.sku == sku
                    ).first():
                        raise ValueError(f"Unknown SKU '{sku}'.")

                    inventory = db.query(Inventory).filter(
                        Inventory.sku == sku
                    ).first()

                    if inventory:
                        inventory.new_stock = stock
                        inventory.avg_daily_demand = demand
                    else:
                        db.add(Inventory(
                            sku=sku,
                            new_stock=stock,
                            avg_daily_demand=demand
                        ))

                successful += 1

            except Exception as exc:
                failed += 1
                errors.append(f"Row {idx}: {str(exc)}")

    # VENDOR TERMS
    elif entity_type == "vendor_terms":
        required = {
            "supplier", "sku", "rtv_allowed",
            "credit_pct", "window_days"
        }
        missing = required - headers

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing vendor-term columns: {', '.join(sorted(missing))}"
            )

        for idx, row in enumerate(rows, 2):
            try:
                with db.begin_nested():
                    supplier = db.query(Supplier).filter(
                        Supplier.supplier_name == row["supplier"]
                    ).first()

                    if not supplier:
                        raise ValueError(
                            f"Unknown supplier '{row['supplier']}'."
                        )

                    sku = row["sku"]

                    if not db.query(Product).filter(
                        Product.sku == sku,
                        Product.supplier_id == supplier.id
                    ).first():
                        raise ValueError(
                            f"SKU '{sku}' does not belong to this supplier."
                        )

                    allowed = parse_bool(row["rtv_allowed"])
                    credit = normalize_percentage(row["credit_pct"])
                    window = int(row["window_days"])

                    if window < 0:
                        raise ValueError("Window days cannot be negative.")

                    term = db.query(VendorTerm).filter(
                        VendorTerm.supplier_id == supplier.id,
                        VendorTerm.sku == sku
                    ).first()

                    if term:
                        term.rtv_allowed = allowed
                        term.credit_percentage = credit
                        term.window_days = window
                    else:
                        db.add(VendorTerm(
                            supplier_id=supplier.id,
                            sku=sku,
                            rtv_allowed=allowed,
                            credit_percentage=credit,
                            window_days=window
                        ))

                successful += 1

            except Exception as exc:
                failed += 1
                errors.append(f"Row {idx}: {str(exc)}")

    # REFURBISHMENT RULES
    elif entity_type == "refurbishment":
        required = {
            "category", "refurb_cost",
            "days_required", "resale_pct_of_new"
        }
        missing = required - headers

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing refurbishment columns: {', '.join(sorted(missing))}"
            )

        for idx, row in enumerate(rows, 2):
            try:
                with db.begin_nested():
                    category = row["category"]
                    cost = float(row["refurb_cost"])
                    days = int(row["days_required"])
                    resale = normalize_percentage(
                        row["resale_pct_of_new"]
                    )

                    if cost < 0 or days < 0:
                        raise ValueError("Invalid refurbishment cost or duration.")

                    rule = db.query(RefurbishmentRule).filter(
                        RefurbishmentRule.category == category
                    ).first()

                    if rule:
                        rule.refurbishment_cost = cost
                        rule.days_required = days
                        rule.resale_percentage_of_new_price = resale
                    else:
                        db.add(RefurbishmentRule(
                            category=category,
                            refurbishment_cost=cost,
                            days_required=days,
                            resale_percentage_of_new_price=resale
                        ))

                successful += 1

            except Exception as exc:
                failed += 1
                errors.append(f"Row {idx}: {str(exc)}")

    # LIQUIDATION RULES
    elif entity_type == "liquidation":
        required = {
            "category", "condition_grade",
            "recovery_pct_of_cost"
        }
        missing = required - headers

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing liquidation columns: {', '.join(sorted(missing))}"
            )

        for idx, row in enumerate(rows, 2):
            try:
                with db.begin_nested():
                    category = row["category"]
                    grade = row["condition_grade"].upper()
                    recovery = normalize_percentage(
                        row["recovery_pct_of_cost"]
                    )

                    if grade not in {"A", "B", "C", "D"}:
                        raise ValueError(f"Invalid grade '{grade}'.")

                    rule = db.query(LiquidationRule).filter(
                        LiquidationRule.category == category,
                        LiquidationRule.grade == grade
                    ).first()

                    if rule:
                        rule.recovery_percentage_of_cost = recovery
                    else:
                        db.add(LiquidationRule(
                            category=category,
                            grade=grade,
                            recovery_percentage_of_cost=recovery
                        ))

                successful += 1

            except Exception as exc:
                failed += 1
                errors.append(f"Row {idx}: {str(exc)}")

    # SALES
    elif entity_type == "sales":
        required = {"date", "sku", "qty_sold", "selling_price"}
        missing = required - headers

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing sales columns: {', '.join(sorted(missing))}"
            )

        for idx, row in enumerate(rows, 2):
            try:
                with db.begin_nested():
                    sku = row["sku"]
                    sale_date = parse_date(row["date"])
                    quantity = int(row["qty_sold"])
                    price = float(row["selling_price"])

                    if quantity < 0 or price < 0:
                        raise ValueError("Sales values cannot be negative.")

                    if not db.query(Product).filter(
                        Product.sku == sku
                    ).first():
                        raise ValueError(f"Unknown SKU '{sku}'.")

                    sale = db.query(Sale).filter(
                        Sale.sale_date == sale_date,
                        Sale.sku == sku,
                        Sale.quantity_sold == quantity,
                        Sale.selling_price == price
                    ).first()

                    if not sale:
                        db.add(Sale(
                            sale_date=sale_date,
                            sku=sku,
                            quantity_sold=quantity,
                            selling_price=price
                        ))

                successful += 1

            except Exception as exc:
                failed += 1
                errors.append(f"Row {idx}: {str(exc)}")

    # COMMIT
    try:
        db.commit()

        db.add(ActivityLog(
            actor="Data Manager",
            action="CSV_IMPORT",
            entity_type=entity_type,
            entity_id="BULK",
            details={
                "total": total,
                "successful": successful,
                "failed": failed,
                "filename": file.filename
            }
        ))

        db.commit()

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"CSV import failed: {str(exc)}"
        )

    return CsvImportResult(
        entity=entity_type,
        total_rows=total,
        successful_rows=successful,
        failed_rows=failed,
        errors=errors[:10]
    )
```
