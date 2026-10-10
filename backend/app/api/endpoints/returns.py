import json
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import (
    ProposedAction,
    Return,
    Product,
    Supplier,
    Inventory,
    RefurbishmentRule,
    VendorTerm,
    LiquidationRule,
    ActivityLog,
)
from app.schemas.schemas import (
    ReturnResponse,
    ReturnCreate,
)
from app.engine.calculator import calculate_route_options


router = APIRouter()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_return_date(value):
    """Convert a database date/datetime value into a date."""
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if value is None:
        return date.today()

    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return date.today()


def get_days_waiting(return_date):
    """Calculate how many days a return has been waiting."""
    return max(0, (date.today() - get_return_date(return_date)).days)


def get_action_return_ids(action):
    """Safely obtain return IDs associated with an action."""
    value = action.related_return_ids

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

    return []


def get_matched_action(return_item, actions):
    """Find an action associated with a return."""
    for action in actions:
        related_ids = get_action_return_ids(action)

        if return_item.id in related_ids:
            return action

        evidence = action.evidence

        if isinstance(evidence, dict):
            if (
                evidence.get("batch") == return_item.supplier_batch
                or evidence.get("sku") == return_item.sku
            ):
                return action

    return None


def get_recovery_context(db, product, return_item, supplier):
    """Load inventory and recovery rules for a return."""
    inventory = (
        db.query(Inventory)
        .filter(Inventory.sku == product.sku)
        .first()
    )

    refurbishment_rule = (
        db.query(RefurbishmentRule)
        .filter(RefurbishmentRule.category == product.category)
        .first()
    )

    vendor_term = (
        db.query(VendorTerm)
        .filter(VendorTerm.supplier_id == supplier.id)
        .first()
        if supplier
        else None
    )

    liquidation_rule = (
        db.query(LiquidationRule)
        .filter(
            LiquidationRule.category == product.category,
            LiquidationRule.grade == return_item.grade,
        )
        .first()
    )

    vendor_quantity = (
        24 if return_item.supplier_batch == "HB-09" else None
    )

    analysis = calculate_route_options(
        product,
        return_item,
        inventory,
        refurbishment_rule,
        vendor_term,
        liquidation_rule,
        vendor_eligible_quantity=vendor_quantity,
    )

    return analysis


def get_net_recovery(analysis):
    """Extract estimated net recovery from route analysis."""
    if (
        analysis.recommended_route == "Split-Batch"
        and analysis.split_recommendation_details
    ):
        return float(
            analysis.split_recommendation_details.get(
                "total_split_net", 0
            )
        )

    if analysis.recommended_route in analysis.routes:
        return float(
            analysis.routes[analysis.recommended_route].net_recovery
        )

    return 0.0


def get_return_priority(return_item, product):
    """Determine return priority based on age and inventory value."""
    days_waiting = get_days_waiting(return_item.return_date)
    return_value = return_item.quantity * product.cost_price

    if days_waiting >= 14 or return_value >= 20000:
        return "Critical"

    if days_waiting >= 7 or return_value >= 10000:
        return "High"

    return "Medium"


def create_activity_log(
    db,
    actor,
    action,
    entity_type,
    entity_id,
    details,
):
    """Create an audit log entry."""
    log = ActivityLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details,
    )

    db.add(log)


# ============================================================
# GET ALL RETURNS
# ============================================================

@router.get("/returns", response_model=List[ReturnResponse])
def get_returns(
    supplier: Optional[str] = None,
    sku: Optional[str] = None,
    grade: Optional[str] = None,
    status: Optional[str] = None,
    reason: Optional[str] = None,
    recommended_route: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Return, Product, Supplier)
        .join(Product, Return.sku == Product.sku)
        .join(Supplier, Product.supplier_id == Supplier.id)
    )

    if supplier:
        query = query.filter(
            Supplier.supplier_name.ilike(f"%{supplier}%")
        )

    if sku:
        query = query.filter(Return.sku == sku)

    if grade:
        query = query.filter(Return.grade == grade.upper())

    if status:
        query = query.filter(Return.status == status)

    if reason:
        query = query.filter(
            Return.reason_code.ilike(f"%{reason}%")
        )

    if recommended_route:
        query = query.filter(
            Return.recommended_route == recommended_route
        )

    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%")
            | Return.sku.ilike(f"%{search}%")
            | Return.supplier_batch.ilike(f"%{search}%")
        )

    results = query.order_by(Return.return_date.desc()).all()

    actions = (
        db.query(ProposedAction)
        .order_by(ProposedAction.created_at.desc())
        .all()
    )

    response_items = []

    for return_item, product, supplier_item in results:
        days_waiting = get_days_waiting(return_item.return_date)

        priority = get_return_priority(return_item, product)

        matched_action = get_matched_action(
            return_item,
            actions,
        )

        current_status = return_item.status

        if matched_action:
            if (
                "Approved" in matched_action.status
                and current_status == "Pending Decision"
            ):
                current_status = "Action Approved"

            elif (
                matched_action.status == "Rejected"
                and current_status == "Pending Decision"
            ):
                current_status = "Action Rejected"

        analysis = get_recovery_context(
            db,
            product,
            return_item,
            supplier_item,
        )

        estimated_net_recovery = get_net_recovery(analysis)

        response_item = ReturnResponse(
            id=return_item.id,
            return_date=return_item.return_date,
            sku=return_item.sku,
            supplier_batch=return_item.supplier_batch,
            reason_code=return_item.reason_code,
            grade=return_item.grade,
            quantity=return_item.quantity,
            status=current_status,
            recommended_route=(
                return_item.recommended_route
                or analysis.recommended_route
            ),
            received_at=return_item.received_at,
            created_at=return_item.created_at,
            product_name=product.name,
            supplier_name=supplier_item.supplier_name,
            cost_price=product.cost_price,
            selling_price=product.selling_price,
            days_waiting=days_waiting,
            estimated_net_recovery=round(
                estimated_net_recovery, 2
            ),
            priority=priority,
            action_id=(
                matched_action.id if matched_action else None
            ),
            action_type=(
                matched_action.action_type
                if matched_action
                else None
            ),
            action_status=(
                matched_action.status
                if matched_action
                else None
            ),
        )

        response_items.append(response_item)

    return response_items


# ============================================================
# GET A SINGLE RETURN
# ============================================================

@router.get("/returns/{return_id}")
def get_return_by_id(
    return_id: int,
    db: Session = Depends(get_db),
):
    result = (
        db.query(Return, Product, Supplier)
        .join(Product, Return.sku == Product.sku)
        .join(Supplier, Product.supplier_id == Supplier.id)
        .filter(Return.id == return_id)
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Return #{return_id} not found.",
        )

    return_item, product, supplier_item = result

    analysis = get_recovery_context(
        db,
        product,
        return_item,
        supplier_item,
    )

    return {
        "return": {
            "id": return_item.id,
            "return_date": str(return_item.return_date),
            "sku": return_item.sku,
            "product_name": product.name,
            "supplier_name": supplier_item.supplier_name,
            "supplier_batch": return_item.supplier_batch,
            "reason_code": return_item.reason_code,
            "grade": return_item.grade,
            "quantity": return_item.quantity,
            "status": return_item.status,
            "cost_price": product.cost_price,
            "selling_price": product.selling_price,
            "days_waiting": get_days_waiting(
                return_item.return_date
            ),
            "recommended_route": (
                return_item.recommended_route
                or analysis.recommended_route
            ),
        },
        "recovery_analysis": analysis,
    }


# ============================================================
# CREATE A RETURN
# ============================================================

@router.post("/returns", response_model=ReturnResponse)
def create_return(
    item: ReturnCreate,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.sku == item.sku)
        .first()
    )

    # Create a product and supplier when a new SKU is entered.
    if not product:
        supplier_name = (
            item.supplier_name or "Gadgetbay Direct Suppliers"
        )

        supplier_item = (
            db.query(Supplier)
            .filter(Supplier.supplier_name == supplier_name)
            .first()
        )

        if not supplier_item:
            supplier_item = Supplier(
                supplier_name=supplier_name,
                contact_email=(
                    "contact@"
                    f"{supplier_name.lower().replace(' ', '')}.com"
                ),
                status="Active",
            )

            db.add(supplier_item)
            db.flush()

        cost_value = (
            item.cost_price
            if item.cost_price is not None and item.cost_price > 0
            else 1000.0
        )

        selling_value = (
            item.selling_price
            if (
                item.selling_price is not None
                and item.selling_price > 0
            )
            else cost_value * 1.6
        )

        product = Product(
            sku=item.sku,
            name=item.product_name or f"Product {item.sku}",
            category=item.category or "Electronics",
            cost_price=cost_value,
            selling_price=selling_value,
            supplier_id=supplier_item.id,
        )

        db.add(product)
        db.flush()

        # Provision default inventory for the new product.
        inventory = Inventory(
            sku=item.sku,
            new_stock=40,
            avg_daily_demand=2.0,
        )

        db.add(inventory)

    else:
        supplier_item = (
            db.query(Supplier)
            .filter(Supplier.id == product.supplier_id)
            .first()
        )

    try:
        new_return = Return(
            return_date=item.return_date,
            sku=item.sku,
            supplier_batch=item.supplier_batch,
            reason_code=item.reason_code,
            grade=item.grade.upper(),
            quantity=item.quantity,
            status=item.status or "Pending Decision",
            recommended_route=item.recommended_route,
            received_at=datetime.utcnow(),
        )

        db.add(new_return)
        db.flush()

        # Calculate recovery economics.
        analysis = get_recovery_context(
            db,
            product,
            new_return,
            supplier_item,
        )

        recommended_route = (
            new_return.recommended_route
            or analysis.recommended_route
        )

        new_return.recommended_route = recommended_route

        estimated_net_recovery = get_net_recovery(analysis)

        create_activity_log(
            db=db,
            actor="Manager (Manual Entry)",
            action="MANUAL_RETURN_CREATED",
            entity_type="Return",
            entity_id=new_return.id,
            details={
                "sku": new_return.sku,
                "qty": new_return.quantity,
                "grade": new_return.grade,
                "route": recommended_route,
            },
        )

        db.commit()
        db.refresh(new_return)

    except Exception:
        db.rollback()
        raise

    return ReturnResponse(
        id=new_return.id,
        return_date=new_return.return_date,
        sku=new_return.sku,
        supplier_batch=new_return.supplier_batch,
        reason_code=new_return.reason_code,
        grade=new_return.grade,
        quantity=new_return.quantity,
        status=new_return.status,
        recommended_route=recommended_route,
        received_at=new_return.received_at,
        created_at=new_return.created_at,
        product_name=product.name,
        supplier_name=(
            supplier_item.supplier_name
            if supplier_item
            else None
        ),
        cost_price=product.cost_price,
        selling_price=product.selling_price,
        days_waiting=get_days_waiting(new_return.return_date),
        estimated_net_recovery=round(
            estimated_net_recovery, 2
        ),
        priority=get_return_priority(new_return, product),
        action_id=None,
        action_type=None,
        action_status=None,
    )


# ============================================================
# UPDATE A RETURN
# ============================================================

@router.put("/returns/{return_id}")
def update_return(
    return_id: int,
    updates: ReturnCreate,
    db: Session = Depends(get_db),
):
    return_item = (
        db.query(Return)
        .filter(Return.id == return_id)
        .first()
    )

    if not return_item:
        raise HTTPException(
            status_code=404,
            detail="Return not found",
        )

    try:
        return_item.grade = updates.grade.upper()
        return_item.quantity = updates.quantity
        return_item.status = (
            updates.status or return_item.status
        )
        return_item.reason_code = updates.reason_code

        if updates.recommended_route:
            return_item.recommended_route = (
                updates.recommended_route
            )

        create_activity_log(
            db=db,
            actor="Manager",
            action="RETURN_UPDATED",
            entity_type="Return",
            entity_id=return_item.id,
            details={
                "status": return_item.status,
                "route": return_item.recommended_route,
                "grade": return_item.grade,
            },
        )

        db.commit()
        db.refresh(return_item)

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Return updated successfully",
        "id": return_item.id,
        "status": return_item.status,
    }


# ============================================================
# DELETE A RETURN
# ============================================================

@router.delete("/returns/{return_id}")
def delete_return(
    return_id: int,
    db: Session = Depends(get_db),
):
    return_item = (
        db.query(Return)
        .filter(Return.id == return_id)
        .first()
    )

    if not return_item:
        raise HTTPException(
            status_code=404,
            detail="Return not found",
        )

    try:
        db.delete(return_item)
        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "message": (
            f"Return #{return_id} deleted successfully"
        )
    }