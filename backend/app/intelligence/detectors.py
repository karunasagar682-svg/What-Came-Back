from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import (
    Product, Return, Supplier, Inventory, RefurbishmentRule, 
    VendorTerm, LiquidationRule, SupplierAlert, ProposedAction
)
from app.engine.calculator import calculate_route_options
from app.schemas.schemas import PriorityItem, BatchIntelligenceResponse



def _cached_first(db: Session, cache_key: tuple, query):
    """Cache repeated lookup results for the lifetime of this request's DB session."""
    cache = db.info.setdefault("_detector_lookup_cache", {})
    if cache_key not in cache:
        cache[cache_key] = query.first()
    return cache[cache_key]


def _cached_all(db: Session, cache_key: tuple, query):
    """Cache repeated list queries for the lifetime of this request's DB session."""
    cache = db.info.setdefault("_detector_lookup_cache", {})
    if cache_key not in cache:
        cache[cache_key] = query.all()
    return cache[cache_key]


def _return_age_days(return_date, current_date: date) -> int:
    """Calculate non-negative age; future-dated records are not treated as old."""
    normalized_date = (
        return_date if isinstance(return_date, date)
        else return_date.date()
    )
    return max(0, (current_date - normalized_date).days)


def _get_vendor_term(db: Session, supplier_id: int, sku: str):
    """Prefer SKU-specific vendor terms, then use supplier-wide terms."""
    sku_term = _cached_first(
        db,
        ("vendor_term_sku", supplier_id, sku),
        db.query(VendorTerm).filter(
            VendorTerm.supplier_id == supplier_id,
            VendorTerm.sku == sku,
        ),
    )
    if sku_term:
        return sku_term

    return _cached_first(
        db,
        ("vendor_term_supplier", supplier_id),
        db.query(VendorTerm).filter(
            VendorTerm.supplier_id == supplier_id,
            VendorTerm.sku.is_(None),
        ),
    )


def _pending_returns(db: Session):
    """Support normalized and original organizer statuses."""
    return db.query(Return).filter(
        Return.status.in_([
            "Pending Decision",
            "Awaiting decision",
            "awaiting decision",
            "pending decision",
        ])
    ).all()


def detect_high_value_waiting_too_long(
    db: Session,
    age_threshold_days: int = 7,
    high_value_threshold: float = 1500.0,
    current_date: Optional[date] = None
) -> List[PriorityItem]:
    """
    PROBLEM 1: High-value returns waiting too long.
    Uses the actual product, inventory and vendor terms in the database.
    """
    current_date = current_date or date.today()
    cutoff_date = current_date - timedelta(days=age_threshold_days)

    query = (
        db.query(Return, Product, Supplier)
        .join(Product, Return.sku == Product.sku)
        .join(Supplier, Product.supplier_id == Supplier.id)
        .filter(Return.status.in_([
            "Pending Decision", "Awaiting decision",
            "awaiting decision", "pending decision"
        ]))
        .filter(Return.return_date <= cutoff_date)
    )

    results: List[PriorityItem] = []

    for ret, prod, supp in query.all():
        total_cost = prod.cost_price * ret.quantity
        if total_cost < high_value_threshold:
            continue

        age = _return_age_days(ret.return_date, current_date)
        inv = _cached_first(db, ("inventory", prod.sku), db.query(Inventory).filter(Inventory.sku == prod.sku))
        refurb = _cached_first(db, ("refurb", prod.category), db.query(RefurbishmentRule).filter(RefurbishmentRule.category == prod.category))
        vt = _get_vendor_term(db, supp.id, prod.sku)
        liq = _cached_first(db, ("liquidation", prod.category, ret.grade), db.query(LiquidationRule).filter(LiquidationRule.category == prod.category, LiquidationRule.grade == ret.grade))

        analysis = calculate_route_options(
            prod, ret, inv, refurb, vt, liq, current_date
        )

        if analysis.recommended_route == "Split-Batch" and analysis.split_recommendation_details:
            rec_net = analysis.split_recommendation_details["total_split_net"]
        else:
            recommended = analysis.routes.get(analysis.recommended_route)
            rec_net = recommended.net_recovery if recommended else 0.0

        urgency_reason = (
            f"Awaiting decision for {age} days "
            f"(threshold: {age_threshold_days} days). "
        )
        if vt and vt.rtv_allowed:
            remaining_days = max(0, vt.window_days - age)
            if remaining_days <= 10:
                urgency_reason += (
                    f"CRITICAL: Vendor return window expires in "
                    f"{remaining_days} days! "
                )
        urgency_reason += f"Recoverable value at risk: ₹{rec_net:,.2f}."

        severity = (
            "Critical"
            if age >= 14 or (
                vt and vt.rtv_allowed
                and max(0, vt.window_days - age) <= 7
            )
            else "High"
        )

        results.append(PriorityItem(
            id=f"aging-{ret.id}",
            problem_category="High-Value Returns Waiting Too Long",
            severity=severity,
            title=f"High-Value Aging Return: {prod.name} ({ret.quantity} units)",
            item_or_batch=f"Return #{ret.id} (Batch: {ret.supplier_batch})",
            sku=prod.sku,
            evidence=(
                f"{ret.quantity}x Grade-{ret.grade} received {age} days ago "
                f"from {supp.supplier_name}. {urgency_reason}"
            ),
            financial_impact=rec_net,
            impact_label="Estimated Recoverable Value",
            recommended_action=(
                f"Route to {analysis.recommended_route} immediately "
                "to avoid further value decay."
            ),
            action_type=f"EXECUTE_{analysis.recommended_route.upper().replace('-', '_').replace(' ', '_')}",
            return_id=ret.id,
            batch=ret.supplier_batch
        ))

    results.sort(key=lambda item: item.financial_impact, reverse=True)
    return results

def detect_avoidable_liquidation_losses(
    db: Session,
    current_date: Optional[date] = None
) -> List[PriorityItem]:
    """
    PROBLEM 2: Items headed for liquidation that could earn more.
    Compares the calculator's recommended route with liquidation.
    """
    current_date = current_date or date.today()
    results: List[PriorityItem] = []

    for ret in _pending_returns(db):
        prod = _cached_first(db, ("product", ret.sku), db.query(Product).filter(Product.sku == ret.sku))
        if not prod:
            continue

        inv = _cached_first(db, ("inventory", prod.sku), db.query(Inventory).filter(Inventory.sku == prod.sku))
        refurb = _cached_first(db, ("refurb", prod.category), db.query(RefurbishmentRule).filter(RefurbishmentRule.category == prod.category))
        vt = _get_vendor_term(db, prod.supplier_id, prod.sku)
        liq = _cached_first(db, ("liquidation", prod.category, ret.grade), db.query(LiquidationRule).filter(LiquidationRule.category == prod.category, LiquidationRule.grade == ret.grade))

        analysis = calculate_route_options(
            prod, ret, inv, refurb, vt, liq, current_date
        )
        liq_route = analysis.routes["Liquidation"]
        best_route_name = analysis.recommended_route

        if best_route_name == "Split-Batch" and analysis.split_recommendation_details:
            best_net = analysis.split_recommendation_details["total_split_net"]
        else:
            best_route = analysis.routes.get(best_route_name)
            best_net = best_route.net_recovery if best_route else 0.0

        incremental_gain = round(best_net - liq_route.net_recovery, 2)

        if best_route_name != "Liquidation" and incremental_gain > 1000.0:
            evidence = (
                f"Liquidation recovery is ₹{liq_route.net_recovery:,.2f}. "
                f"The recommended route '{best_route_name}' recovers "
                f"₹{best_net:,.2f}, avoiding ₹{incremental_gain:,.2f} "
                "in potential value loss."
            )

            results.append(PriorityItem(
                id=f"liq-loss-{ret.id}",
                problem_category="Liquidation Value Destruction",
                severity="High",
                title=f"Avoid Liquidation: {prod.name}",
                item_or_batch=f"Return #{ret.id} (Batch: {ret.supplier_batch})",
                sku=prod.sku,
                evidence=evidence,
                financial_impact=incremental_gain,
                impact_label="Avoidable Loss Saved",
                recommended_action=(
                    f"Compare liquidation with {best_route_name}; "
                    f"estimated recovery gain is ₹{incremental_gain:,.2f}."
                ),
                action_type="DIVERT_FROM_LIQUIDATION",
                return_id=ret.id,
                batch=ret.supplier_batch
            ))

    results.sort(key=lambda item: item.financial_impact, reverse=True)
    return results

def detect_expiring_vendor_windows(
    db: Session,
    warning_days_threshold: int = 7,
    current_date: Optional[date] = None
) -> List[PriorityItem]:
    """
    PROBLEM 3: Vendor return windows about to close.
    Uses SKU-specific vendor terms and the return's actual age.
    """
    current_date = current_date or date.today()
    results: List[PriorityItem] = []

    for ret in _pending_returns(db):
        prod = _cached_first(db, ("product", ret.sku), db.query(Product).filter(Product.sku == ret.sku))
        if not prod:
            continue

        vt = _get_vendor_term(db, prod.supplier_id, prod.sku)
        if not vt or not vt.rtv_allowed:
            continue

        age = _return_age_days(ret.return_date, current_date)
        days_remaining = vt.window_days - age
        eligible_qty = ret.quantity if days_remaining >= 0 else 0

        if 0 <= days_remaining <= warning_days_threshold and eligible_qty > 0:
            supp = _cached_first(db, ("supplier", prod.supplier_id), db.query(Supplier).filter(Supplier.id == prod.supplier_id))
            supp_name = supp.supplier_name if supp else "Supplier"

            unit_credit = round(
                prod.selling_price * (vt.credit_percentage / 100.0), 2
            )
            total_credit = round(unit_credit * eligible_qty, 2)
            severity = "Critical" if days_remaining <= 3 else "High"

            results.append(PriorityItem(
                id=f"vendor-expiring-{ret.id}",
                problem_category="Vendor Return Windows Closing Soon",
                severity=severity,
                title=(
                    f"Vendor Window Closing in {days_remaining} Days: "
                    f"{prod.name}"
                ),
                item_or_batch=f"Batch: {ret.supplier_batch} (Return #{ret.id})",
                sku=prod.sku,
                evidence=(
                    f"{eligible_qty} units eligible for "
                    f"{vt.credit_percentage}% vendor credit "
                    f"(₹{unit_credit}/unit). Deadline: {days_remaining} "
                    f"days remaining in the {vt.window_days}-day window "
                    f"with {supp_name}. ₹{total_credit:,.2f} credit is at risk."
                ),
                financial_impact=total_credit,
                impact_label="Vendor Credit at Risk",
                recommended_action=(
                    f"Generate and approve a vendor return request for "
                    f"{eligible_qty} units before the window closes."
                ),
                action_type="VENDOR_RETURN",
                return_id=ret.id,
                batch=ret.supplier_batch
            ))

    results.sort(key=lambda item: item.financial_impact, reverse=True)
    return results

def detect_supplier_and_batch_anomalies(
    db: Session,
    defect_spike_threshold_pct: float = 15.0
) -> List[PriorityItem]:
    """
    PROBLEM 4: Unusually high returns by SKU or supplier batch.
    Flags evidence-backed dominant defect clusters; no hardcoded batch IDs.
    """
    results: List[PriorityItem] = []
    batches = db.query(Return.supplier_batch).distinct().all()

    for (batch_code,) in batches:
        if not batch_code:
            continue

        returns_in_batch = _cached_all(db, ("batch_returns", batch_code), db.query(Return).filter(Return.supplier_batch == batch_code))
        if not returns_in_batch:
            continue

        total_returned = sum(max(0, r.quantity or 0) for r in returns_in_batch)
        if total_returned <= 0:
            continue

        sample_ret = returns_in_batch[0]
        prod = _cached_first(db, ("product", sample_ret.sku), db.query(Product).filter(Product.sku == sample_ret.sku))
        if not prod:
            continue

        supp = _cached_first(db, ("supplier", prod.supplier_id), db.query(Supplier).filter(Supplier.id == prod.supplier_id))
        supplier_name = supp.supplier_name if supp else "Supplier"

        reason_counts: Dict[str, int] = {}
        for ret in returns_in_batch:
            reason = ret.reason_code or "Unknown"
            reason_counts[reason] = reason_counts.get(reason, 0) + max(0, ret.quantity or 0)

        dominant_reason, dominant_count = max(
            reason_counts.items(), key=lambda item: item[1]
        )
        dominant_pct = dominant_count / total_returned * 100.0

        # The returns file alone does not provide total units sold.
        # Therefore this is a within-batch defect concentration, not a true return rate.
        if dominant_pct < max(50.0, defect_spike_threshold_pct):
            continue

        evidence = (
            f"Batch {batch_code} has {total_returned} returned units. "
            f"{dominant_count} units ({dominant_pct:.1f}%) report "
            f"'{dominant_reason}'. This is a concentrated defect pattern "
            "within the supplied return records; sales-denominator data "
            "is required to calculate a true return rate."
        )
        financial_risk = total_returned * prod.cost_price

        results.append(PriorityItem(
            id=f"anomaly-batch-{batch_code}",
            problem_category="Unusually High Returns & Batch Anomalies",
            severity="Critical" if dominant_pct >= 65.0 else "High",
            title=f"Supplier Defect Spike: Batch {batch_code} ({supplier_name})",
            item_or_batch=f"Batch: {batch_code} ({prod.name})",
            sku=prod.sku,
            evidence=evidence,
            financial_impact=financial_risk,
            impact_label="Batch Quality Risk",
            recommended_action=(
                f"Review the defect cluster and investigate supplier "
                f"{supplier_name}; consider quarantining batch {batch_code}."
            ),
            action_type="SUPPLIER_INVESTIGATION",
            return_id=sample_ret.id,
            batch=batch_code
        ))

    results.sort(key=lambda item: item.financial_impact, reverse=True)
    return results

def detect_refurb_demand_mismatch(
    db: Session,
    excess_stock_days_threshold: int = 45,
    current_date: Optional[date] = None
) -> List[PriorityItem]:
    """
    PROBLEM 5: Refurbishing when demand is weak or new stock is excessive.
    Preserves the existing demand-coverage approach.
    """
    results: List[PriorityItem] = []

    for ret in _pending_returns(db):
        prod = _cached_first(db, ("product", ret.sku), db.query(Product).filter(Product.sku == ret.sku))
        if not prod:
            continue

        inv = _cached_first(db, ("inventory", prod.sku), db.query(Inventory).filter(Inventory.sku == prod.sku))
        if not inv:
            continue

        daily_demand = inv.avg_daily_demand if inv.avg_daily_demand > 0 else 0.5
        coverage_days = int(inv.new_stock / daily_demand)
        refurb_rule = _cached_first(db, ("refurb", prod.category), db.query(RefurbishmentRule).filter(RefurbishmentRule.category == prod.category))

        if (
            coverage_days >= excess_stock_days_threshold
            and ret.grade in ["B", "C"]
            and refurb_rule
        ):
            refurb_cost_total = refurb_rule.refurbishment_cost * ret.quantity
            evidence = (
                f"Inventory has {inv.new_stock} new units "
                f"({coverage_days} days of demand). Refurbishing "
                f"{ret.quantity} units costs ₹{refurb_cost_total:,.2f}; "
                "excess stock may delay resale or reduce margin."
            )

            results.append(PriorityItem(
                id=f"demand-excess-{ret.id}",
                problem_category="Refurbishing What Nobody Wants / Demand Mismatch",
                severity="High" if coverage_days >= 60 else "Medium",
                title=f"Excess Inventory Demand Risk: {prod.name}",
                item_or_batch=f"Return #{ret.id} (Batch: {ret.supplier_batch})",
                sku=prod.sku,
                evidence=evidence,
                financial_impact=refurb_cost_total,
                impact_label="Capital at Stagnation Risk",
                recommended_action=(
                    "Compare vendor return, restock and liquidation recovery "
                    "before committing refurbishment costs."
                ),
                action_type="AVOID_EXCESS_REFURBISHMENT",
                return_id=ret.id,
                batch=ret.supplier_batch
            ))

    results.sort(key=lambda item: item.financial_impact, reverse=True)
    return results

def get_all_priority_issues(db: Session, current_date: Optional[date] = None) -> List[PriorityItem]:
    """
    Aggregates and ranks all detected issues across all 5 mandatory problem categories.
    """
    p1 = detect_high_value_waiting_too_long(db, current_date=current_date)
    p2 = detect_avoidable_liquidation_losses(db, current_date=current_date)
    p3 = detect_expiring_vendor_windows(db, current_date=current_date)
    p4 = detect_supplier_and_batch_anomalies(db)
    p5 = detect_refurb_demand_mismatch(db, current_date=current_date)
    
    combined = p1 + p2 + p3 + p4 + p5
    
    # Deduplicate by title/item
    seen = set()
    unique_items = []
    for item in combined:
        key = (item.problem_category, item.item_or_batch)
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
            
    # Rank by severity (Critical first) then financial impact descending
    severity_rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    unique_items.sort(key=lambda x: (severity_rank.get(x.severity, 4), -x.financial_impact))
    return unique_items


def get_batch_intelligence(
    db: Session,
    batch_code: str
) -> Optional[BatchIntelligenceResponse]:
    """Build a batch report from actual return records and vendor terms."""
    returns = _cached_all(db, ("batch_returns", batch_code), db.query(Return).filter(Return.supplier_batch == batch_code))
    if not returns:
        return None

    total_returns = sum(max(0, ret.quantity or 0) for ret in returns)
    sample_ret = returns[0]
    prod = _cached_first(db, ("product", sample_ret.sku), db.query(Product).filter(Product.sku == sample_ret.sku))
    if not prod:
        return None

    supp = _cached_first(db, ("supplier", prod.supplier_id), db.query(Supplier).filter(Supplier.id == prod.supplier_id))
    supplier_name = supp.supplier_name if supp else "Unknown"

    defects: Dict[str, int] = {}
    for ret in returns:
        reason = ret.reason_code or "Unknown"
        defects[reason] = defects.get(reason, 0) + max(0, ret.quantity or 0)

    dominant_reason = max(defects.items(), key=lambda item: item[1])[0] if defects else "N/A"
    dominant_count = defects.get(dominant_reason, 0)
    dominant_pct = (
        dominant_count / total_returns * 100.0
        if total_returns > 0 else 0.0
    )

    vt = _get_vendor_term(db, prod.supplier_id, prod.sku)
    age = _return_age_days(sample_ret.return_date, date.today())
    window_days = vt.window_days if vt else 0
    days_remaining = max(0, window_days - age) if vt else 0
    eligible_rtv = (
        total_returns
        if vt and vt.rtv_allowed and age <= window_days
        else 0
    )

    is_flagged = dominant_pct >= 50.0

    return BatchIntelligenceResponse(
        supplier_batch=batch_code,
        supplier_name=supplier_name,
        sku=prod.sku,
        product_name=prod.name,
        total_returns=total_returns,
        defect_breakdown=defects,
        dominant_defect=dominant_reason,
        dominant_defect_percentage=round(dominant_pct, 1),
        observed_return_rate=round(dominant_pct, 1),
        baseline_return_rate=5.0,
        is_flagged=is_flagged,
        risk_level=(
            "Critical" if dominant_pct >= 65.0
            else ("High" if is_flagged else "Normal")
        ),
        recommendation=(
            f"Review batch {batch_code} because "
            f"{dominant_pct:.1f}% of recorded returned units report "
            f"'{dominant_reason}'. A true return rate requires total sales."
        ),
        vendor_window_days=window_days,
        days_remaining_in_window=days_remaining,
        eligible_rtv_quantity=eligible_rtv
    )
