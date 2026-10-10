from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.models.models import ProposedAction, ActivityLog, Return
from app.schemas.schemas import (
    ProposedActionCreate, ProposedActionResponse, 
    ActionDecisionRequest, ActivityLogResponse
)

router = APIRouter()

@router.get("/actions", response_model=List[ProposedActionResponse])
def get_actions(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ProposedAction)
    if status and status != "All":
        query = query.filter(ProposedAction.status.ilike(f"%{status}%"))
    return query.order_by(ProposedAction.created_at.desc()).all()

@router.get("/actions/logs", response_model=List[ActivityLogResponse])
def get_activity_logs(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit).all()

@router.get("/actions/{action_id}", response_model=ProposedActionResponse)
def get_action_by_id(action_id: int, db: Session = Depends(get_db)):
    action = db.query(ProposedAction).filter(ProposedAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action

@router.post("/actions", response_model=ProposedActionResponse)
def create_action(payload: ProposedActionCreate, db: Session = Depends(get_db)):
    action = ProposedAction(
        action_type=payload.action_type,
        related_return_ids=payload.related_return_ids,
        proposed_quantity=payload.proposed_quantity,
        estimated_recovery=payload.estimated_recovery,
        explanation=payload.explanation,
        evidence=payload.evidence or {},
        risks_and_assumptions=payload.risks_and_assumptions or {},
        status="Pending",
        created_at=datetime.utcnow()
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    
    # Activity log
    log = ActivityLog(
        actor="System",
        action="ACTION_PROPOSED",
        entity_type="ProposedAction",
        entity_id=str(action.id),
        details={"type": action.action_type, "quantity": action.proposed_quantity, "recovery": action.estimated_recovery}
    )
    db.add(log)
    db.commit()
    
    return action

@router.post("/actions/{action_id}/approve", response_model=ProposedActionResponse)
def approve_action(action_id: int, decision: ActionDecisionRequest, db: Session = Depends(get_db)):
    action = db.query(ProposedAction).filter(ProposedAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail=f"Action #{action_id} not found.")
        
    # Idempotency / Duplicate approval prevention
    if "Approved" in action.status or "Executed" in action.status:
        raise HTTPException(
            status_code=400,
            detail=f"Action #{action_id} has already been approved and executed (Status: '{action.status}'). Duplicate approvals are rejected."
        )
        
    if action.status == "Rejected":
        raise HTTPException(
            status_code=400,
            detail=f"Action #{action_id} was previously rejected. Create a new proposal to reconsider."
        )
        
    action.status = "Approved (Simulated)"
    action.reviewed_at = datetime.utcnow()
    action.reviewed_by = decision.actor
    
    # Update related returns status if any
    return_ids = []
    if action.related_return_ids:
        if isinstance(action.related_return_ids, list):
            return_ids = action.related_return_ids
        elif isinstance(action.related_return_ids, str):
            try:
                import json
                parsed = json.loads(action.related_return_ids)
                if isinstance(parsed, list):
                    return_ids = parsed
            except:
                pass
                
    route_name = action.action_type.replace('_', ' ').title()
    if "Split" in route_name:
        route_name = "Split-Batch"
    elif "Vendor" in route_name:
        route_name = "Vendor Return"
    elif "Refurb" in route_name:
        route_name = "Refurbish"
        
    for ret_id in return_ids:
        try:
            r_id = int(ret_id)
            ret = db.query(Return).filter(Return.id == r_id).first()
            if ret:
                ret.status = "Action Approved"
                ret.recommended_route = route_name
        except:
            pass
            
    # Also if action has evidence with batch (e.g. HB-09):
    if action.evidence and isinstance(action.evidence, dict) and "batch" in action.evidence:
        batch_name = action.evidence["batch"]
        matching_returns = db.query(Return).filter(Return.supplier_batch == batch_name).all()
        for ret in matching_returns:
            ret.status = "Action Approved"
            ret.recommended_route = route_name
                
    # Record in audit log
    log = ActivityLog(
        actor=decision.actor,
        action="ACTION_APPROVED_SIMULATED",
        entity_type="ProposedAction",
        entity_id=str(action.id),
        details={
            "action_type": action.action_type,
            "quantity": action.proposed_quantity,
            "estimated_recovery": action.estimated_recovery,
            "note": decision.reason or "Approved in Action Approval Center (Simulation Mode)"
        }
    )
    db.add(log)
    db.commit()
    db.refresh(action)
    return action

@router.post("/actions/{action_id}/reject", response_model=ProposedActionResponse)
def reject_action(action_id: int, decision: ActionDecisionRequest, db: Session = Depends(get_db)):
    action = db.query(ProposedAction).filter(ProposedAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail=f"Action #{action_id} not found.")
        
    if "Approved" in action.status:
        raise HTTPException(
            status_code=400,
            detail=f"Action #{action_id} is already approved and cannot be rejected."
        )
        
    action.status = "Rejected"
    action.reviewed_at = datetime.utcnow()
    action.reviewed_by = decision.actor
    
    # Update return status if rejected
    return_ids = []
    if action.related_return_ids:
        if isinstance(action.related_return_ids, list):
            return_ids = action.related_return_ids
        elif isinstance(action.related_return_ids, str):
            try:
                import json
                parsed = json.loads(action.related_return_ids)
                if isinstance(parsed, list):
                    return_ids = parsed
            except:
                pass
    for ret_id in return_ids:
        try:
            r_id = int(ret_id)
            ret = db.query(Return).filter(Return.id == r_id).first()
            if ret:
                ret.status = "Action Rejected"
        except:
            pass
    
    log = ActivityLog(
        actor=decision.actor,
        action="ACTION_REJECTED",
        entity_type="ProposedAction",
        entity_id=str(action.id),
        details={"reason": decision.reason or "Rejected by manager"}
    )
    db.add(log)
    db.commit()
    db.refresh(action)
    return action
