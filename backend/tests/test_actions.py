import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from app.core.database import Base
from app.models.models import ProposedAction, ActivityLog
from app.api.endpoints.actions import approve_action, reject_action
from app.schemas.schemas import ActionDecisionRequest

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()

def test_action_approval_lifecycle(db_session):
    # 1. Create a proposed action
    action = ProposedAction(
        action_type="VENDOR_RETURN",
        related_return_ids=[101],
        proposed_quantity=24,
        estimated_recovery=36000.0,
        explanation="Return 24 headphones to vendor for credit.",
        status="Pending"
    )
    db_session.add(action)
    db_session.commit()
    db_session.refresh(action)
    
    # 2. Approve action
    decision = ActionDecisionRequest(actor="Sarah Operations Manager", reason="Approved per batch agreement.")
    approved = approve_action(action.id, decision, db_session)
    
    assert approved.status == "Approved (Simulated)"
    assert approved.reviewed_by == "Sarah Operations Manager"
    assert approved.reviewed_at is not None
    
    # 3. Verify audit log entry
    logs = db_session.query(ActivityLog).filter(ActivityLog.entity_id == str(action.id)).all()
    assert len(logs) == 1
    assert logs[0].action == "ACTION_APPROVED_SIMULATED"
    assert logs[0].actor == "Sarah Operations Manager"
    
    # 4. Test duplicate approval prevention
    with pytest.raises(HTTPException) as exc_info:
        approve_action(action.id, decision, db_session)
    assert exc_info.value.status_code == 400
    assert "already been approved" in exc_info.value.detail

def test_action_rejection(db_session):
    action = ProposedAction(
        action_type="SCRAP",
        related_return_ids=[102],
        proposed_quantity=10,
        estimated_recovery=0.0,
        explanation="Scrap all items.",
        status="Pending"
    )
    db_session.add(action)
    db_session.commit()
    
    decision = ActionDecisionRequest(actor="Lead Manager", reason="Scrap rejected; route to liquidation instead.")
    rejected = reject_action(action.id, decision, db_session)
    
    assert rejected.status == "Rejected"
    assert rejected.reviewed_by == "Lead Manager"
