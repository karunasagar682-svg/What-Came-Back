import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.seed.seed_data import seed_demo_database
from app.agent.copilot import run_copilot_deterministic_fallback

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    seed_demo_database(session)
    yield session
    session.close()

def test_copilot_fallback_daily_priorities(db_session):
    resp = run_copilot_deterministic_fallback(db_session, "What needs my attention today?")
    assert "Daily Returns Recovery Briefing" in resp.response
    assert "HB-09" in resp.response or "Critical" in resp.response
    assert "Deterministic Recovery Copilot Engine" in resp.provider_used
    assert len(resp.tools_called) > 0

def test_copilot_fallback_batch_hb09(db_session):
    resp = run_copilot_deterministic_fallback(db_session, "Why is batch HB-09 flagged?")
    assert "HB-09" in resp.response
    assert "70.0%" in resp.response or "70%" in resp.response
    assert "SoundWave Dynamics" in resp.response
    assert "Audio Driver Hiss" in resp.response

def test_copilot_fallback_generate_split_action(db_session):
    resp = run_copilot_deterministic_fallback(db_session, "Prepare a proposed action for these 40 headphones")
    assert "Split-Batch Recovery Plan" in resp.response
    assert "62,000" in resp.response
    assert "42,400" in resp.response
    assert "Vendor Return" in resp.response
    assert "Refurbish" in resp.response
