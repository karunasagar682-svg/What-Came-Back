from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from app.models.models import Product, Return, Inventory, RefurbishmentRule, VendorTerm, LiquidationRule
from app.schemas.schemas import RouteDetail, RouteComparisonResult, SplitBatchResponse, SplitBatchRouteSummary

def calculate_route_options(
    product: Product,
    return_item: Return,
    inventory: Optional[Inventory],
    refurb_rule: Optional[RefurbishmentRule],
    vendor_term: Optional[VendorTerm],
    liq_rule: Optional[LiquidationRule],
    current_date: Optional[date] = None,
    vendor_eligible_quantity: Optional[int] = None
) -> RouteComparisonResult:
    """
    Deterministic calculation engine for evaluating all 5 recovery routes.
    Never hallucinates financial values.
    """
    if current_date is None:
        current_date = date.today()
    
    return_date = return_item.return_date if isinstance(return_item.return_date, date) else return_item.return_date.date()
    days_waiting = max(0, (current_date - return_date).days)
    
    qty = return_item.quantity
    selling_price = product.selling_price
    cost_price = product.cost_price
    grade = return_item.grade.upper()
    category = product.category
    
    # Inventory & Demand context
    new_stock = inventory.new_stock if inventory else 0
    daily_demand = inventory.avg_daily_demand if inventory and inventory.avg_daily_demand > 0 else 1.0
    stock_coverage_days = int(new_stock / daily_demand) if daily_demand > 0 else 0
    
    # -------------------------------------------------------------
    # ROUTE 1: RESTOCK
    # -------------------------------------------------------------
    restock_cost_per_unit = 50.0  # Inspection & repackaging cost
    is_restock_eligible = (grade == "A")
    restock_ineligible_reason = None if is_restock_eligible else f"Grade {grade} items cannot be returned to shelf stock without refurbishment or vendor repair."
    
    if is_restock_eligible:
        restock_gross = selling_price * qty
        restock_cost = restock_cost_per_unit * qty
        restock_net = max(0.0, restock_gross - restock_cost)
        restock_time_to_cash = 1 + int(new_stock / daily_demand) if daily_demand > 0 else 7
        restock_demand_fit = "High" if daily_demand >= 1.0 else "Moderate"
    else:
        restock_gross = 0.0
        restock_cost = 0.0
        restock_net = 0.0
        restock_time_to_cash = 0
        restock_demand_fit = "Ineligible"
    
    restock_detail = RouteDetail(
        route="Restock",
        is_eligible=is_restock_eligible,
        ineligibility_reason=restock_ineligible_reason,
        gross_recovery=round(restock_gross, 2),
        processing_costs=round(restock_cost, 2),
        net_recovery=round(restock_net, 2),
        recovery_per_unit=round(restock_net / qty, 2) if qty > 0 and is_restock_eligible else 0.0,
        time_to_cash_days=restock_time_to_cash,
        demand_fit=restock_demand_fit,
        assumptions=["Standard ₹50/unit QA inspection & re-boxing fee", "Full MSRP resale in Grade A condition"],
        risks=["Minimal; slight resale delay if existing stock is high"]
    )
    
    # -------------------------------------------------------------
    # ROUTE 2: REFURBISH
    # -------------------------------------------------------------
    is_refurb_eligible = (grade in ["B", "C"]) and (refurb_rule is not None)
    refurb_ineligible_reason = None
    if grade not in ["B", "C"]:
        refurb_ineligible_reason = f"Grade {grade} is not suited for standard refurbishment (Grade A needs no repair; Grade D is scrap)."
    elif not refurb_rule:
        refurb_ineligible_reason = f"No active refurbishment rule configured for category '{category}'."
        
    if is_refurb_eligible and refurb_rule:
        resale_pct = refurb_rule.resale_percentage_of_new_price / 100.0
        refurb_resale_unit = round(selling_price * resale_pct, 2)
        refurb_cost_unit = refurb_rule.refurbishment_cost
        unit_net = round(refurb_resale_unit - refurb_cost_unit, 2)
        refurb_gross = round(refurb_resale_unit * qty, 2)
        refurb_cost = round(refurb_cost_unit * qty, 2)
        refurb_net = round(unit_net * qty, 2)
        
        # Time to cash: repair duration + sales time
        repair_days = refurb_rule.days_required
        selling_days = max(5, int((new_stock * 0.5) / daily_demand)) if daily_demand > 0 else 14
        refurb_time_to_cash = repair_days + min(selling_days, 45)
        
        if stock_coverage_days >= 45:
            refurb_demand_fit = "Excess Risk (High New Stock)"
            refurb_risks = [
                f"Existing new-stock coverage is {stock_coverage_days} days. Refurbished units will face resale competition from new inventory."
            ]
        elif daily_demand >= 2.0:
            refurb_demand_fit = "High"
            refurb_risks = ["Minor cosmetic variance risk upon secondary delivery"]
        else:
            refurb_demand_fit = "Moderate"
            refurb_risks = ["Sales velocity may require promotional discounting"]
    else:
        refurb_gross = 0.0
        refurb_cost = 0.0
        refurb_net = 0.0
        refurb_time_to_cash = 0
        refurb_demand_fit = "Ineligible"
        refurb_risks = [refurb_ineligible_reason or "Ineligible"]
        
    refurb_detail = RouteDetail(
        route="Refurbish",
        is_eligible=is_refurb_eligible,
        ineligibility_reason=refurb_ineligible_reason,
        gross_recovery=round(refurb_gross, 2),
        processing_costs=round(refurb_cost, 2),
        net_recovery=round(refurb_net, 2),
        recovery_per_unit=round(refurb_net / qty, 2) if qty > 0 and is_refurb_eligible else 0.0,
        time_to_cash_days=refurb_time_to_cash,
        demand_fit=refurb_demand_fit,
        assumptions=[
            f"Resale percentage: {refurb_rule.resale_percentage_of_new_price if refurb_rule else 0}% of new price (₹{round(selling_price * (refurb_rule.resale_percentage_of_new_price/100.0), 2) if refurb_rule else 0}/unit)",
            f"Refurbishment labor & parts: ₹{refurb_rule.refurbishment_cost if refurb_rule else 0}/unit"
        ],
        risks=refurb_risks
    )
    
    # -------------------------------------------------------------
    # ROUTE 3: VENDOR RETURN (RTV)
    # -------------------------------------------------------------
    has_rtv = (vendor_term is not None and vendor_term.rtv_allowed)
    window_days = vendor_term.window_days if vendor_term else 0
    days_remaining = max(0, window_days - days_waiting)
    
    # If explicit vendor eligible qty passed (like 24 out of 40), use it, else check window
    effective_vendor_qty = vendor_eligible_quantity if vendor_eligible_quantity is not None else (qty if days_waiting <= window_days else 0)
    is_vendor_eligible = has_rtv and (effective_vendor_qty > 0) and (days_remaining > 0 or effective_vendor_qty > 0)
    
    vendor_ineligible_reason = None
    if not has_rtv:
        vendor_ineligible_reason = "Supplier agreement does not permit Return-to-Vendor (RTV)."
    elif days_waiting > window_days and effective_vendor_qty == 0:
        vendor_ineligible_reason = f"Vendor return window expired ({days_waiting} days elapsed vs {window_days}-day limit)."
    elif effective_vendor_qty == 0:
        vendor_ineligible_reason = "No units eligible under current vendor return quota or policy."
        
    if is_vendor_eligible and vendor_term:
        credit_pct = vendor_term.credit_percentage / 100.0
        # If reference scenario specifies credit on selling price (60% of 2500 = 1500), or vendor terms
        # Standard convention: credit_percentage applied to selling_price if > cost_price or as agreed in terms
        # For headphones scenario: 60% of ₹2,500 selling price = ₹1,500
        vendor_credit_unit = round(selling_price * credit_pct, 2)
        vendor_gross = round(vendor_credit_unit * effective_vendor_qty, 2)
        vendor_cost = 0.0  # Standard vendor credit has no internal repair cost
        vendor_net = vendor_gross
        vendor_time_to_cash = 14  # Typical vendor reconciliation ledger credit
        vendor_demand_fit = "Guaranteed (Vendor Credit)"
        vendor_risks = [
            f"{days_remaining} days remaining until deadline. Return authorization and dispatch must occur promptly."
        ]
    else:
        vendor_gross = 0.0
        vendor_cost = 0.0
        vendor_net = 0.0
        vendor_time_to_cash = 0
        vendor_demand_fit = "Ineligible"
        vendor_risks = [vendor_ineligible_reason or "Ineligible"]
        
    vendor_detail = RouteDetail(
        route="Vendor Return",
        is_eligible=is_vendor_eligible,
        ineligibility_reason=vendor_ineligible_reason,
        gross_recovery=round(vendor_gross, 2),
        processing_costs=round(vendor_cost, 2),
        net_recovery=round(vendor_net, 2),
        recovery_per_unit=round(vendor_net / effective_vendor_qty, 2) if effective_vendor_qty > 0 and is_vendor_eligible else 0.0,
        time_to_cash_days=vendor_time_to_cash,
        demand_fit=vendor_demand_fit,
        assumptions=[
            f"Vendor credit: {vendor_term.credit_percentage if vendor_term else 0}% of selling price (₹{round(selling_price * (vendor_term.credit_percentage/100.0), 2) if vendor_term else 0}/unit)",
            f"{days_remaining} days remaining in {window_days}-day return window",
            f"Eligible units: {effective_vendor_qty} of {qty}"
        ],
        risks=vendor_risks
    )
    
    # -------------------------------------------------------------
    # ROUTE 4: LIQUIDATION
    # -------------------------------------------------------------
    liq_pct = (liq_rule.recovery_percentage_of_cost / 100.0) if liq_rule else 0.30
    liq_unit = round(cost_price * liq_pct, 2)
    liq_gross = round(liq_unit * qty, 2)
    liq_cost = 0.0
    liq_net = liq_gross
    liq_time_to_cash = 3  # Fast liquidator pickup
    
    liq_detail = RouteDetail(
        route="Liquidation",
        is_eligible=True,
        ineligibility_reason=None,
        gross_recovery=round(liq_gross, 2),
        processing_costs=0.0,
        net_recovery=round(liq_net, 2),
        recovery_per_unit=round(liq_unit, 2),
        time_to_cash_days=liq_time_to_cash,
        demand_fit="Immediate Cash / Value Compromise",
        assumptions=[f"Liquidation rate: {round(liq_pct * 100, 1)}% of product cost (₹{liq_unit}/unit)"],
        risks=["Destroys avoidable recovery value if higher routes are eligible"]
    )
    
    # -------------------------------------------------------------
    # ROUTE 5: SCRAP
    # -------------------------------------------------------------
    scrap_unit_value = 20.0 if grade == "D" else 0.0
    scrap_disposal_fee = 20.0
    scrap_net_unit = max(0.0, scrap_unit_value - scrap_disposal_fee)
    scrap_gross = scrap_unit_value * qty
    scrap_cost = scrap_disposal_fee * qty
    scrap_net = scrap_net_unit * qty
    
    scrap_detail = RouteDetail(
        route="Scrap",
        is_eligible=(grade == "D" or not (is_restock_eligible or is_refurb_eligible or is_vendor_eligible)),
        ineligibility_reason=None if (grade == "D") else "Usable value remains in other recovery channels.",
        gross_recovery=round(scrap_gross, 2),
        processing_costs=round(scrap_cost, 2),
        net_recovery=round(scrap_net, 2),
        recovery_per_unit=round(scrap_net_unit, 2),
        time_to_cash_days=2,
        demand_fit="Zero Resale Value",
        assumptions=["Certified e-waste recycling disposal fee ₹20/unit"],
        risks=["Zero recovery; strictly last resort"]
    )
    
    routes = {
        "Restock": restock_detail,
        "Refurbish": refurb_detail,
        "Vendor Return": vendor_detail,
        "Liquidation": liq_detail,
        "Scrap": scrap_detail
    }
    
    # -------------------------------------------------------------
    # RECOMMENDATION SELECTION & SPLIT LOGIC
    # -------------------------------------------------------------
    # Check if a split-batch allocation is warranted:
    # E.g. vendor return has high per-unit credit and 0 demand risk, but is capped at 24 units out of 40.
    is_split_recommended = False
    split_details = None
    
    if effective_vendor_qty > 0 and effective_vendor_qty < qty:
        remaining_qty = qty - effective_vendor_qty
        # Compare remaining qty options
        rem_refurb_net = (refurb_detail.recovery_per_unit * remaining_qty) if is_refurb_eligible else 0.0
        rem_liq_net = (liq_detail.recovery_per_unit * remaining_qty)
        
        best_remaining_route = "Refurbish" if (is_refurb_eligible and rem_refurb_net > rem_liq_net) else "Liquidation"
        total_split_net = vendor_detail.net_recovery + (rem_refurb_net if best_remaining_route == "Refurbish" else rem_liq_net)
        all_liq_net = liq_detail.net_recovery
        
        is_split_recommended = True
        split_details = {
            "vendor_quantity": effective_vendor_qty,
            "vendor_net": vendor_detail.net_recovery,
            "remaining_quantity": remaining_qty,
            "remaining_route": best_remaining_route,
            "remaining_net": rem_refurb_net if best_remaining_route == "Refurbish" else rem_liq_net,
            "total_split_net": round(total_split_net, 2),
            "incremental_gain_over_liquidation": round(total_split_net - all_liq_net, 2),
            "notes": f"Return {effective_vendor_qty} units to vendor for guaranteed credit (₹{vendor_detail.recovery_per_unit}/unit). {best_remaining_route} the remaining {remaining_qty} units (₹{refurb_detail.recovery_per_unit if best_remaining_route == 'Refurbish' else liq_detail.recovery_per_unit}/unit)."
        }
        recommended_route = "Split-Batch"
        rec_reason = (
            f"Split-batch strategy maximizes total recovery at ₹{round(total_split_net, 2):,}: "
            f"Return {effective_vendor_qty} eligible units to vendor for ₹{round(vendor_detail.net_recovery, 2):,} credit "
            f"(eliminating inventory & demand risk), and {best_remaining_route.lower()} the remaining {remaining_qty} units for ₹{round(rem_refurb_net if best_remaining_route == 'Refurbish' else rem_liq_net, 2):,} net recovery."
        )
        best_alt_route = "Liquidation"
        incremental_over_liq = round(total_split_net - liq_net, 2)
    else:
        # Standard single route ranking
        eligible_routes = [r for r in routes.values() if r.is_eligible and r.route != "Scrap"]
        if not eligible_routes:
            recommended_route = "Scrap"
            rec_reason = "No higher recovery routes are eligible due to product grade or policy constraints."
            best_alt_route = None
            incremental_over_liq = 0.0
        else:
            # Sort primarily by net recovery, but penalize refurbish if high stock coverage (> 45 days) and vendor return is close
            def route_score(r: RouteDetail):
                score = r.net_recovery
                if r.route == "Refurbish" and stock_coverage_days >= 45:
                    score -= (r.net_recovery * 0.05)  # minor penalty for demand risk
                return score
            
            sorted_routes = sorted(eligible_routes, key=route_score, reverse=True)
            top_route = sorted_routes[0]
            recommended_route = top_route.route
            
            if len(sorted_routes) > 1:
                alt = sorted_routes[1]
                best_alt_route = alt.route
            else:
                best_alt_route = "Liquidation" if top_route.route != "Liquidation" else None
                
            incremental_over_liq = round(top_route.net_recovery - liq_net, 2)
            
            rec_reason = (
                f"{recommended_route} yields the highest net recovery of ₹{top_route.net_recovery:,} "
                f"(₹{top_route.recovery_per_unit}/unit) with estimated time-to-cash of {top_route.time_to_cash_days} days. "
            )
            if best_alt_route and best_alt_route != recommended_route:
                alt_net = routes[best_alt_route].net_recovery
                rec_reason += f"Outperforms {best_alt_route} (₹{alt_net:,}) by ₹{round(top_route.net_recovery - alt_net, 2):,}."

    supplier_name = product.supplier.supplier_name if product.supplier else "Unknown Supplier"

    return RouteComparisonResult(
        return_id=return_item.id,
        sku=product.sku,
        product_name=product.name,
        supplier_name=supplier_name,
        supplier_batch=return_item.supplier_batch,
        grade=grade,
        quantity=qty,
        cost_price=cost_price,
        selling_price=selling_price,
        days_waiting=days_waiting,
        routes=routes,
        recommended_route=recommended_route,
        recommendation_reason=rec_reason,
        best_alternative_route=best_alt_route,
        incremental_recovery_over_liquidation=incremental_over_liq,
        is_split_recommended=is_split_recommended,
        split_recommendation_details=split_details
    )


def evaluate_split_plan(
    product: Product,
    return_item: Return,
    inventory: Optional[Inventory],
    refurb_rule: Optional[RefurbishmentRule],
    vendor_term: Optional[VendorTerm],
    liq_rule: Optional[LiquidationRule],
    allocations: List[Dict[str, Any]],
    current_date: Optional[date] = None,
    max_vendor_eligible_qty: Optional[int] = None
) -> SplitBatchResponse:
    """
    Validates and simulates manager's proposed split batch allocation.
    Guarantees that total allocated does not exceed batch quantity,
    and enforces route eligibility constraints.
    """
    total_qty = return_item.quantity
    selling_price = product.selling_price
    cost_price = product.cost_price
    grade = return_item.grade.upper()
    
    validation_errors = []
    total_allocated = 0
    route_summaries = []
    total_net_recovery = 0.0
    weighted_time_days = 0.0
    
    # Calculate baseline liquidation
    liq_pct = (liq_rule.recovery_percentage_of_cost / 100.0) if liq_rule else 0.30
    unit_liq_recovery = round(cost_price * liq_pct, 2)
    all_liq_recovery = round(unit_liq_recovery * total_qty, 2)
    
    # Check max vendor limit
    vendor_limit = max_vendor_eligible_qty if max_vendor_eligible_qty is not None else total_qty
    
    # Check each allocated route
    for item in allocations:
        route = item.get("route")
        alloc_qty = item.get("quantity", 0)
        
        if alloc_qty < 0:
            validation_errors.append(f"Quantity for {route} cannot be negative.")
            continue
        if alloc_qty == 0:
            continue
            
        total_allocated += alloc_qty
        
        # Check route-specific eligibility and unit economics
        is_eligible = True
        eligibility_note = None
        per_unit_net = 0.0
        time_days = 0
        
        if route == "Restock":
            if grade != "A":
                is_eligible = False
                eligibility_note = f"Grade {grade} is not restock eligible without refurbishment."
                validation_errors.append(eligibility_note)
            else:
                per_unit_net = round(selling_price - 50.0, 2)
                time_days = 7
        elif route == "Refurbish":
            if grade not in ["B", "C"]:
                is_eligible = False
                eligibility_note = f"Grade {grade} is not suitable for refurbishment."
                validation_errors.append(eligibility_note)
            elif not refurb_rule:
                is_eligible = False
                eligibility_note = "No refurbishment rule configured for this category."
                validation_errors.append(eligibility_note)
            else:
                resale_price = round(selling_price * (refurb_rule.resale_percentage_of_new_price / 100.0), 2)
                per_unit_net = round(resale_price - refurb_rule.refurbishment_cost, 2)
                time_days = refurb_rule.days_required + 10
        elif route == "Vendor Return":
            if not vendor_term or not vendor_term.rtv_allowed:
                is_eligible = False
                eligibility_note = "Supplier does not accept Return-to-Vendor."
                validation_errors.append(eligibility_note)
            elif alloc_qty > vendor_limit:
                is_eligible = False
                eligibility_note = f"Allocated quantity ({alloc_qty}) exceeds eligible vendor quota ({vendor_limit})."
                validation_errors.append(eligibility_note)
            else:
                per_unit_net = round(selling_price * (vendor_term.credit_percentage / 100.0), 2)
                time_days = 14
        elif route == "Liquidation":
            per_unit_net = unit_liq_recovery
            time_days = 3
        elif route == "Scrap":
            per_unit_net = 0.0
            time_days = 2
        else:
            is_eligible = False
            eligibility_note = f"Unknown recovery route '{route}'."
            validation_errors.append(eligibility_note)
            
        subtotal = round(per_unit_net * alloc_qty, 2)
        total_net_recovery += subtotal
        weighted_time_days += (time_days * alloc_qty)
        
        route_summaries.append(SplitBatchRouteSummary(
            route=route,
            quantity=alloc_qty,
            per_unit_net=per_unit_net,
            subtotal_net_recovery=subtotal,
            time_to_cash_days=time_days,
            is_eligible=is_eligible,
            eligibility_note=eligibility_note
        ))
        
    if total_allocated > total_qty:
        validation_errors.append(
            f"Total allocated quantity ({total_allocated}) exceeds total batch quantity ({total_qty})."
        )
        
    is_valid = (len(validation_errors) == 0) and (total_allocated > 0)
    
    weighted_avg_time = round(weighted_time_days / total_allocated, 1) if total_allocated > 0 else 0.0
    incremental_gain = round(total_net_recovery - all_liq_recovery, 2)
    remaining_unallocated = max(0, total_qty - total_allocated)
    
    explanation = (
        f"Split allocation achieves ₹{round(total_net_recovery, 2):,} total recovery across {total_allocated} units. "
        f"Outperforms full liquidation (₹{round(all_liq_recovery, 2):,}) by +₹{incremental_gain:,} "
        f"with a weighted average time-to-cash of {weighted_avg_time} days."
    )
    
    return SplitBatchResponse(
        is_valid=is_valid,
        validation_errors=validation_errors,
        total_allocated=total_allocated,
        remaining_unallocated=remaining_unallocated,
        route_breakdowns=route_summaries,
        total_net_recovery=round(total_net_recovery, 2),
        weighted_time_to_cash_days=weighted_avg_time,
        all_liquidation_recovery=all_liq_recovery,
        incremental_gain_over_liquidation=incremental_gain,
        trade_off_explanation=explanation,
        recommended_action_title=f"Split Recovery Plan: {total_allocated} units ({product.sku})"
    )
