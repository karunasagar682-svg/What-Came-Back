import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import date
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import Product, Return, Supplier, ProposedAction, ActivityLog
from app.intelligence.detectors import (
    get_all_priority_issues,
    get_batch_intelligence,
    detect_high_value_waiting_too_long,
    detect_expiring_vendor_windows,
    detect_avoidable_liquidation_losses,
    detect_refurb_demand_mismatch
)
from app.engine.calculator import calculate_route_options, evaluate_split_plan
from app.schemas.schemas import CopilotChatResponse

logger = logging.getLogger(__name__)

# Backend tools callable by the AI Agent
def tool_get_daily_priorities(db: Session) -> Dict[str, Any]:
    issues = get_all_priority_issues(db)
    top_3 = issues[:3]
    return {
        "total_critical_issues": len(issues),
        "top_priorities": [
            {
                "title": i.title,
                "severity": i.severity,
                "evidence": i.evidence,
                "financial_impact": i.financial_impact,
                "recommended_action": i.recommended_action,
                "sku": i.sku,
                "batch": i.batch
            }
            for i in top_3
        ]
    }

def tool_get_returns_waiting_too_long(db: Session, threshold_days: int = 7) -> Dict[str, Any]:
    issues = detect_high_value_waiting_too_long(db, age_threshold_days=threshold_days)
    return {
        "count": len(issues),
        "aging_returns": [
            {
                "title": i.title,
                "evidence": i.evidence,
                "financial_impact": i.financial_impact,
                "recommended_action": i.recommended_action,
                "sku": i.sku,
                "batch": i.batch
            }
            for i in issues
        ]
    }

def tool_get_expiring_vendor_windows(db: Session, threshold_days: int = 7) -> Dict[str, Any]:
    issues = detect_expiring_vendor_windows(db, warning_days_threshold=threshold_days)
    return {
        "count": len(issues),
        "expiring_windows": [
            {
                "title": i.title,
                "evidence": i.evidence,
                "financial_impact": i.financial_impact,
                "recommended_action": i.recommended_action,
                "batch": i.batch
            }
            for i in issues
        ]
    }

def tool_analyze_supplier_batch(db: Session, batch_code: str) -> Dict[str, Any]:
    intel = get_batch_intelligence(db, batch_code)
    if not intel:
        return {"error": f"Batch '{batch_code}' not found in database."}
    return intel.model_dump()

def get_vendor_term_for_product(db: Session, supplier_id: int, sku: str):
    """Prefer SKU-specific terms, then fall back to supplier-wide terms."""
    from app.models.models import VendorTerm

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


def tool_compare_recovery_routes(db: Session, return_id: int) -> Dict[str, Any]:
    ret = db.query(Return).filter(Return.id == return_id).first()
    if not ret:
        return {"error": f"Return #{return_id} not found."}

    from app.models.models import Inventory, RefurbishmentRule, LiquidationRule

    prod = db.query(Product).filter(Product.sku == ret.sku).first()
    if not prod:
        return {"error": f"Product for SKU '{ret.sku}' not found."}

    inv = db.query(Inventory).filter(Inventory.sku == prod.sku).first()
    refurb = (
        db.query(RefurbishmentRule)
        .filter(RefurbishmentRule.category == prod.category)
        .first()
    )
    vt = get_vendor_term_for_product(db, prod.supplier_id, prod.sku)
    liq = (
        db.query(LiquidationRule)
        .filter(
            LiquidationRule.category == prod.category,
            LiquidationRule.grade == ret.grade,
        )
        .first()
    )

    # The calculator determines eligibility from actual vendor terms and dates.
    analysis = calculate_route_options(prod, ret, inv, refurb, vt, liq)
    return analysis.model_dump()


def tool_create_proposed_action(
    db: Session,
    action_type: str,
    sku: str,
    batch: str,
    quantity: int,
    estimated_recovery: float,
    explanation: str,
    related_return_ids: List[int]
) -> Dict[str, Any]:
    new_action = ProposedAction(
        action_type=action_type,
        related_return_ids=related_return_ids,
        proposed_quantity=quantity,
        estimated_recovery=estimated_recovery,
        explanation=explanation,
        evidence={"sku": sku, "batch": batch},
        risks_and_assumptions={"source": "AI Copilot recommendation", "status": "Requires human review"},
        status="Pending"
    )
    db.add(new_action)
    db.commit()
    db.refresh(new_action)
    
    # Log in activity log
    log = ActivityLog(
        actor="Copilot Agent",
        action="PROPOSED_ACTION_CREATED",
        entity_type="ProposedAction",
        entity_id=str(new_action.id),
        details={"action_type": action_type, "quantity": quantity, "recovery": estimated_recovery}
    )
    db.add(log)
    db.commit()
    
    return {
        "success": True,
        "action_id": new_action.id,
        "status": "Pending Human Approval in Action Approval Center",
        "estimated_recovery": estimated_recovery
    }

TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "get_daily_priorities",
            "description": "Retrieves the highest urgency issues requiring manager attention today across all 5 problem areas.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_returns_waiting_too_long",
            "description": "Finds high-value returned inventory that has exceeded aging thresholds without a disposition decision.",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold_days": {"type": "integer", "description": "Aging threshold in days (default 7)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_expiring_vendor_windows",
            "description": "Identifies return batches nearing their vendor return deadline where vendor credit is at risk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold_days": {"type": "integer", "description": "Warning window threshold in days (default 7)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_supplier_batch",
            "description": "Analyzes defect frequencies, dominant fault reasons, return rates, and supplier alert status for a given batch code (e.g. HB-09).",
            "parameters": {
                "type": "object",
                "properties": {
                    "batch_code": {"type": "string", "description": "The supplier batch code, e.g. 'HB-09'"}
                },
                "required": ["batch_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_recovery_routes",
            "description": "Computes deterministic financial recovery across all 5 routes (Restock, Refurbish, Vendor Return, Liquidation, Scrap) for a return ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "return_id": {"type": "integer", "description": "The Return database ID"}
                },
                "required": ["return_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_proposed_action",
            "description": "Prepares a formal simulated recovery action for manager review and approval in the Action Approval Center.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "description": "Type: VENDOR_RETURN, REFURBISH, SPLIT_BATCH, etc."},
                    "sku": {"type": "string"},
                    "batch": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "estimated_recovery": {"type": "number"},
                    "explanation": {"type": "string"},
                    "related_return_ids": {"type": "array", "items": {"type": "integer"}}
                },
                "required": ["action_type", "sku", "batch", "quantity", "estimated_recovery", "explanation", "related_return_ids"]
            }
        }
    }
]

def run_copilot_deterministic_fallback(db: Session, message: str) -> CopilotChatResponse:
    """
    Deterministic rule-based reasoning engine.
    Executes actual backend tools and builds high-quality, structured business responses.
    """
    msg_lower = message.lower()
    tools_called = []
    
    # 1. "What needs my attention today?" / "daily priorities"
    if any(k in msg_lower for k in ["attention", "today", "priority", "priorities", "what needs"]):
        data = tool_get_daily_priorities(db)
        tools_called.append({"tool": "get_daily_priorities", "result": f"{data['total_critical_issues']} items retrieved"})
        
        items_md = ""
        for idx, item in enumerate(data["top_priorities"], 1):
            items_md += (
                f"### {idx}. [{item['severity']}] {item['title']}\n"
                f"- **Item/Batch**: SKU `{item['sku']}` | Batch `{item['batch']}`\n"
                f"- **Evidence**: {item['evidence']}\n"
                f"- **Financial Impact**: ₹{item['financial_impact']:,.2f}\n"
                f"- **Recommended Action**: {item['recommended_action']}\n\n"
            )
            
        resp_text = (
            f"## Gadgetbay Daily Returns Recovery Briefing\n\n"
            f"Here are the top critical issues requiring your operational decision today:\n\n"
            f"{items_md}"
            f"---\n"
            f"**Recommended Next Step**: Review the highlighted actions in the **Action Approval Center** or inspect batch details in **Supplier Intelligence**."
        )
        return CopilotChatResponse(
            response=resp_text,
            provider_used="Deterministic Recovery Copilot Engine (Rule-based Fallback)",
            tools_called=tools_called,
            evidence=data,
            suggested_actions=["Why is batch HB-09 flagged?", "Prepare a proposed action for these 40 headphones", "Which vendor-return windows are closing soon?"]
        )
        
    # 2. Batch-specific supplier intelligence
    elif any(k in msg_lower for k in ["batch", "concerning return pattern", "why is"]):
        batch_match = re.search(r"\\b([A-Z0-9]+-[A-Z0-9-]+)\\b", message.upper())
        batch_code = batch_match.group(1) if batch_match else None

        if not batch_code:
            first_return = db.query(Return).filter(Return.supplier_batch.isnot(None)).first()
            batch_code = first_return.supplier_batch if first_return else None

        if not batch_code:
            return CopilotChatResponse(
                response="I couldn't find a supplier batch in your message or the returns database.",
                provider_used="Deterministic Recovery Copilot Engine (Rule-based Fallback)",
                tools_called=[],
                suggested_actions=["What needs my attention today?", "Which vendor-return windows are closing soon?"],
            )

        data = tool_analyze_supplier_batch(db, batch_code)
        tools_called.append({
            "tool": "analyze_supplier_batch",
            "args": {"batch_code": batch_code},
            "result": "Batch data retrieved",
        })

        if "error" in data:
            return CopilotChatResponse(
                response=f"Notice: {data['error']}",
                provider_used="Deterministic Recovery Copilot Engine (Rule-based Fallback)",
                tools_called=tools_called,
            )

        resp_text = (
            f"## Supplier Intelligence: Batch {batch_code}\\n\\n"
            f"**Supplier:** {data.get('supplier_name', 'Not available')}\\n"
            f"**Product:** {data.get('product_name', 'Not available')} "
            f"(SKU: `{data.get('sku', 'Not available')}`)\\n\\n"
            f"### Evidence from the database\\n"
            f"- **Total returns:** {data.get('total_returns', 'Not available')} units.\\n"
            f"- **Dominant defect:** {data.get('dominant_defect', 'Not identified')} "
            f"({data.get('dominant_defect_percentage', 'Not available')}% of recorded batch returns).\\n"
            f"- **Observed return rate:** {data.get('observed_return_rate', 'Not available')}%; "
            f"baseline: {data.get('baseline_return_rate', 'Not available')}%.\\n"
            f"- **Vendor-eligible quantity:** {data.get('eligible_rtv_quantity', 'Not available')} units; "
            f"days remaining: {data.get('days_remaining_in_window', 'Not available')}.\\n\\n"
            f"### Recommended next step\\n"
            f"Review the batch evidence and vendor eligibility above before approving a recovery route. "
            f"I have not estimated financial values that are not available in the database."
        )
        return CopilotChatResponse(
            response=resp_text,
            provider_used="Deterministic Recovery Copilot Engine (Rule-based Fallback)",
            tools_called=tools_called,
            evidence=data,
            suggested_actions=[
                "What needs my attention today?",
                "Which vendor-return windows are closing soon?",
                "Show me the financial difference between the best route and liquidation.",
            ],
        )

    # 3. Prepare a data-driven proposed recovery action for an existing batch.
    elif any(k in msg_lower for k in ["40 headphones", "return 24", "split-batch", "split plan", "prepare a proposed action"]):
        batch_match = re.search(r"\\b([A-Z0-9]+-[A-Z0-9-]+)\\b", message.upper())
        batch_code = batch_match.group(1) if batch_match else None

        if not batch_code:
            demo_return = db.query(Return).filter(Return.supplier_batch == "HB-09").first()
            if demo_return:
                batch_code = demo_return.supplier_batch
            else:
                first_return = db.query(Return).filter(Return.status == "Pending Decision").first()
                batch_code = first_return.supplier_batch if first_return else None

        batch_returns = (
            db.query(Return).filter(Return.supplier_batch == batch_code).all()
            if batch_code else []
        )
        if not batch_returns:
            return CopilotChatResponse(
                response="I couldn't find returns for a batch to build a proposed action. Please specify an existing batch code.",
                provider_used="Deterministic Recovery Copilot Engine (Rule-based Fallback)",
                tools_called=tools_called,
                suggested_actions=["What needs my attention today?", "Which vendor-return windows are closing soon?"],
            )

        total_quantity = sum(max(0, int(r.quantity or 0)) for r in batch_returns)
        estimated_recovery = 0.0
        analyzed_count = 0
        route_summary = {}

        for batch_return in batch_returns:
            analysis_data = tool_compare_recovery_routes(db, batch_return.id)
            if "error" in analysis_data:
                continue

            route = analysis_data.get("recommended_route")
            net_value = 0.0
            split_details = analysis_data.get("split_recommendation_details") or {}
            routes = analysis_data.get("routes") or {}
            if route == "Split-Batch":
                net_value = float(split_details.get("total_split_net") or 0.0)
            elif route in routes:
                net_value = float((routes[route] or {}).get("net_recovery") or 0.0)

            estimated_recovery += net_value
            analyzed_count += 1
            route_summary[route or "Unknown"] = (
                route_summary.get(route or "Unknown", 0) + int(batch_return.quantity or 0)
            )

        if analyzed_count == 0:
            return CopilotChatResponse(
                response=f"I found batch `{batch_code}`, but couldn't calculate recovery for its returns. Please check the product and recovery-rule records.",
                provider_used="Deterministic Recovery Copilot Engine (Rule-based Fallback)",
                tools_called=tools_called,
            )

        first_return = batch_returns[0]
        product = db.query(Product).filter(Product.sku == first_return.sku).first()
        sku = product.sku if product else first_return.sku

        action_res = tool_create_proposed_action(
            db=db,
            action_type="BATCH_RECOVERY_REVIEW",
            sku=sku,
            batch=batch_code or "",
            quantity=total_quantity,
            estimated_recovery=round(estimated_recovery, 2),
            explanation=(
                f"Proposed recovery review for batch {batch_code}, based on {analyzed_count} "
                f"return records and deterministic route calculations. Route quantity summary: {route_summary}. "
                "Review vendor eligibility, inventory demand, and route assumptions before approval."
            ),
            related_return_ids=[r.id for r in batch_returns],
        )
        tools_called.append({
            "tool": "create_proposed_action",
            "result": f"Created Action #{action_res['action_id']}",
        })

        route_lines = "\\n".join(
            f"- **{route}**: {quantity} units"
            for route, quantity in sorted(route_summary.items())
        ) or "- Route allocation unavailable"

        resp_text = (
            f"## Proposed Batch Recovery Review: Action #{action_res['action_id']}\\n\\n"
            f"A proposal has been submitted to the **Action Approval Center** for human review.\\n\\n"
            f"- **Batch:** `{batch_code}`\\n"
            f"- **Returns analyzed:** {analyzed_count}\\n"
            f"- **Units represented:** {total_quantity}\\n"
            f"- **Estimated recovery from current route recommendations:** ₹{estimated_recovery:,.2f}\\n\\n"
            f"### Current recommended routes\\n{route_lines}\\n\\n"
            f"**Status:** Pending human approval. This is a recovery review, not a pre-approved split plan."
        )
        return CopilotChatResponse(
            response=resp_text,
            provider_used="Deterministic Recovery Copilot Engine (Rule-based Fallback)",
            tools_called=tools_called,
            evidence=action_res,
            suggested_actions=[
                "What needs my attention today?",
                "Which vendor-return windows are closing soon?",
                "Show me the financial difference between the best route and liquidation.",
            ],
        )

    # 4. "Which vendor-return windows are closing soon?"
    elif any(k in msg_lower for k in ["vendor", "window", "closing", "deadline", "rtv"]):
        data = tool_get_expiring_vendor_windows(db, 7)
        tools_called.append({"tool": "get_expiring_vendor_windows", "result": f"{data['count']} items found"})
        
        items_md = ""
        for i in data["expiring_windows"]:
            items_md += f"- **{i['title']}** (Batch `{i['batch']}`): {i['evidence']} (Financial Value at Risk: ₹{i['financial_impact']:,.2f})\n"
            
        resp_text = (
            f"## Vendor Return Windows Expiring Within 7 Days\n\n"
            f"Found **{data['count']}** batches nearing their vendor return deadline:\n\n"
            f"{items_md}\n"
            f"**Action Required**: Authorize vendor return actions immediately to prevent forfeiting vendor credits."
        )
        return CopilotChatResponse(
            response=resp_text,
            provider_used="Deterministic Recovery Copilot Engine (Rule-based Fallback)",
            tools_called=tools_called,
            evidence=data,
            suggested_actions=["Prepare a proposed action for these 40 headphones", "What needs my attention today?"]
        )
        
    # 5. "Which returns are losing the most recovery value?" / "aging"
    elif any(k in msg_lower for k in ["losing", "aging", "waiting too long", "value decay"]):
        data = tool_get_returns_waiting_too_long(db, 7)
        tools_called.append({"tool": "get_returns_waiting_too_long", "result": f"{data['count']} items found"})
        
        items_md = ""
        for i in data["aging_returns"]:
            items_md += f"- **{i['title']}** (Batch `{i['batch']}`): {i['evidence']} (Value: ₹{i['financial_impact']:,.2f})\n"
            
        resp_text = (
            f"## High-Value Returns Waiting Too Long\n\n"
            f"Found **{data['count']}** return batches exceeding aging thresholds:\n\n"
            f"{items_md}\n"
            f"**Recommendation**: Make immediate disposition decisions to halt value decay and avoid missing RTV cutoffs."
        )
        return CopilotChatResponse(
            response=resp_text,
            provider_used="Deterministic Recovery Copilot Engine (Rule-based Fallback)",
            tools_called=tools_called,
            evidence=data,
            suggested_actions=["What needs my attention today?", "Why is batch HB-09 flagged?"]
        )
        
    # 6. "Which items should not be liquidated?" / "difference between best route and liquidation"
    elif any(k in msg_lower for k in ["liquidat", "earn more", "destruction", "difference"]):
        losses = detect_avoidable_liquidation_losses(db)
        tools_called.append({"tool": "detect_avoidable_liquidation_losses", "result": f"{len(losses)} opportunities identified"})
        
        items_md = ""
        for item in losses[:4]:
            items_md += f"- **{item['title']}**: {item['evidence']} (Incremental gain: **+₹{item['financial_impact']:,.2f}**)\n"
            
        resp_text = (
            f"## Items Headed for Liquidation That Could Earn Significantly More\n\n"
            f"Here are returns where the deterministic recovery engine estimates a higher-value alternative to liquidation:\n\n"
            f"{items_md}\n"
            f"**Business Takeaway**: Rerouting these items to Vendor Return or Refurbishment protects company gross margins."
        )
        return CopilotChatResponse(
            response=resp_text,
            provider_used="Deterministic Recovery Copilot Engine (Rule-based Fallback)",
            tools_called=tools_called,
            suggested_actions=["What needs my attention today?", "Why is batch HB-09 flagged?"]
        )

    # Default fallback response
    priorities = tool_get_daily_priorities(db)
    tools_called.append({"tool": "get_daily_priorities", "result": "Retrieved operational status"})
    return CopilotChatResponse(
        response=(
            f"## Gadgetbay Returns Intelligence Assistant\n\n"
            f"I analyzed current inventory returns against your database. There are currently **{priorities['total_critical_issues']} critical issues** awaiting manager action.\n\n"
            f"- **Top Priority**: {priorities['top_priorities'][0]['title'] if priorities['top_priorities'] else 'No active critical issues.'}\n"
            f"- **Financial Impact**: ₹{priorities['top_priorities'][0]['financial_impact']:,.2f} at risk.\n\n"
            f"You can ask me to:\n"
            f"1. *'What needs my attention today?'*\n"
            f"2. *'Why is batch HB-09 flagged?'*\n"
            f"3. *'Prepare a proposed action for these 40 headphones'*\n"
            f"4. *'Which vendor-return windows are closing soon?'*\n"
            f"5. *'Show me the financial difference between the best route and liquidation'*."
        ),
        provider_used="Deterministic Recovery Copilot Engine (Rule-based Fallback)",
        tools_called=tools_called,
        suggested_actions=["What needs my attention today?", "Why is batch HB-09 flagged?", "Prepare a proposed action for these 40 headphones"]
    )


async def ask_copilot(db: Session, message: str, history: Optional[List[Any]] = None) -> CopilotChatResponse:
    """
    Main entrypoint for Copilot chat. Uses OpenAI with Tool Calling if OPENAI_API_KEY is configured,
    or falls back seamlessly to the deterministic reasoning engine.
    """
    if not settings.OPENAI_API_KEY:
        return run_copilot_deterministic_fallback(db, message)
        
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        system_prompt = (
            "You are the Gadgetbay Recovery Copilot, an AI returns recovery architect for an e-commerce electronics retailer.\n"
            "Rules:\n"
            "1. NEVER hallucinate or invent financial values. Always call backend tools to retrieve factual numbers.\n"
            "2. Explain trade-offs clearly between Restock, Refurbish, Vendor Return, Liquidation, and Scrap.\n"
            "3. Format every important recommendation with: Issue, Business Evidence, Financial Impact, Recommended Next Step, and Assumptions.\n"
            "4. If information is not in the database, explicitly state that it does not exist rather than fabricating an answer."
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for h in history:
                messages.append({"role": h.role, "content": h.content})
        messages.append({"role": "user", "content": message})
        
        # Step 1: Request tool call from model
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=TOOLS_SPEC,
            tool_choice="auto",
            temperature=0.2,
            timeout=15.0
        )
        
        msg = completion.choices[0].message
        
        # If model called tools, execute them
        if msg.tool_calls:
            tools_called_record = []
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                
                tool_output = {}
                if fn_name == "get_daily_priorities":
                    tool_output = tool_get_daily_priorities(db)
                elif fn_name == "get_returns_waiting_too_long":
                    tool_output = tool_get_returns_waiting_too_long(db, fn_args.get("threshold_days", 7))
                elif fn_name == "get_expiring_vendor_windows":
                    tool_output = tool_get_expiring_vendor_windows(db, fn_args.get("threshold_days", 7))
                elif fn_name == "analyze_supplier_batch":
                    tool_output = tool_analyze_supplier_batch(db, fn_args.get("batch_code", "HB-09"))
                elif fn_name == "compare_recovery_routes":
                    tool_output = tool_compare_recovery_routes(db, fn_args.get("return_id", 1))
                elif fn_name == "create_proposed_action":
                    tool_output = tool_create_proposed_action(
                        db, fn_args["action_type"], fn_args["sku"], fn_args["batch"],
                        fn_args["quantity"], fn_args["estimated_recovery"], fn_args["explanation"],
                        fn_args.get("related_return_ids", [1])
                    )
                    
                tools_called_record.append({"tool": fn_name, "args": fn_args, "result": tool_output})
                
                messages.append(msg)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_output)
                })
                
            # Step 2: Final response with tool results
            final_completion = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.2,
                timeout=15.0
            )
            final_text = final_completion.choices[0].message.content or "Completed analysis."
            
            return CopilotChatResponse(
                response=final_text,
                provider_used=f"OpenAI ({settings.OPENAI_MODEL})",
                tools_called=tools_called_record,
                suggested_actions=["What needs my attention today?", "Why is batch HB-09 flagged?"]
            )
        else:
            return CopilotChatResponse(
                response=msg.content or "",
                provider_used=f"OpenAI ({settings.OPENAI_MODEL})",
                tools_called=[],
                suggested_actions=["What needs my attention today?", "Why is batch HB-09 flagged?"]
            )
            
    except Exception as e:
        logger.warning(f"OpenAI API call failed ({str(e)}). Switching to deterministic fallback engine.")
        # Fallback seamlessly to deterministic engine
        fallback_resp = run_copilot_deterministic_fallback(db, message)
        fallback_resp.provider_used = f"Deterministic Recovery Copilot Engine (Rule-based Fallback - {type(e).__name__})"
        return fallback_resp
