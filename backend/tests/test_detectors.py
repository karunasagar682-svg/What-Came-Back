import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.seed.seed_data import seed_demo_database
from app.intelligence.detectors import (
    detect_high_value_waiting_too_long,
    detect_avoidable_liquidation_losses,
    detect_expiring_vendor_windows,
    detect_supplier_and_batch_anomalies,
    detect_refurb_demand_mismatch,
    get_batch_intelligence
)

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    seed_demo_database(session)
    yield session
    session.close()

def test_problem_1_detect_aging_returns(db_session):
    issues = detect_high_value_waiting_too_long(db_session, age_threshold_days=7)
    assert len(issues) > 0
    # Camera CAM-PRO-4K (21 days old) and headphones (18 days old) should be detected
    skus = [i.sku for i in issues]
    assert "CAM-PRO-4K" in skus

def test_problem_2_detect_liquidation_loss(db_session):
    issues = detect_avoidable_liquidation_losses(db_session)
    assert len(issues) > 0
    # Smartwatch SW-FIT-02 or headphones should be flagged
    assert any("avoid" in i.title.lower() or "liquidation" in i.title.lower() for i in issues)

def test_problem_3_detect_expiring_vendor_windows(db_session):
    issues = detect_expiring_vendor_windows(db_session, warning_days_threshold=7)
    assert len(issues) > 0
    # Laptop LAP-ZEN-15 is 27 days old with 30-day window (3 days left)
    skus = [i.sku for i in issues]
    assert "LAP-ZEN-15" in skus

def test_problem_4_detect_batch_hb09_anomaly(db_session):
    issues = detect_supplier_and_batch_anomalies(db_session)
    assert len(issues) > 0
    # Batch HB-09 should be detected
    batches = [i.batch for i in issues]
    assert "HB-09" in batches

def test_batch_hb09_intelligence_detail(db_session):
    intel = get_batch_intelligence(db_session, "HB-09")
    assert intel is not None
    assert intel.supplier_batch == "HB-09"
    assert intel.dominant_defect_percentage == 70.0
    assert "Audio Driver Hiss" in intel.dominant_defect
    assert intel.is_flagged is True
    assert intel.eligible_rtv_quantity == 24

def test_problem_5_detect_refurb_demand_mismatch(db_session):
    issues = detect_refurb_demand_mismatch(db_session, excess_stock_days_threshold=45)
    assert len(issues) > 0
    # Headphone WH-1000XM-B has 60 days new stock coverage
    skus = [i.sku for i in issues]
    assert "WH-1000XM-B" in skus
