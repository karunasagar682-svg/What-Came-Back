import pytest
import io
from fastapi import UploadFile, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.seed.seed_data import seed_demo_database
from app.api.endpoints.data import import_csv_dataset

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    seed_demo_database(session)
    yield session
    session.close()

@pytest.mark.anyio
async def test_csv_import_returns_valid_and_invalid(db_session):
    csv_content = (
        "return_date,sku,supplier_batch,reason_code,grade,quantity,status\n"
        "2026-10-01,WH-1000XM-B,HB-09,Broken Slider,B,5,Pending Decision\n"
        "2026-10-02,INVALID-SKU-999,HB-09,Defect,B,2,Pending Decision\n"
        "2026-10-03,WH-1000XM-B,HB-09,Defect,Z,3,Pending Decision\n"  # Invalid grade Z
    )
    
    file = UploadFile(filename="returns.csv", file=io.BytesIO(csv_content.encode("utf-8")))
    
    result = await import_csv_dataset(
        entity_type="returns",
        file=file,
        db=db_session
    )
    
    assert result.total_rows == 3
    assert result.successful_rows == 1
    assert result.failed_rows == 2
    assert len(result.errors) == 2
    assert "INVALID-SKU-999" in result.errors[0]
    assert "Invalid grade 'Z'" in result.errors[1]

@pytest.mark.anyio
async def test_csv_import_missing_columns(db_session):
    bad_csv = "date,sku,notes\n2026-10-01,WH-1000XM-B,Sample"
    file = UploadFile(filename="bad.csv", file=io.BytesIO(bad_csv.encode("utf-8")))
    
    with pytest.raises(HTTPException) as exc_info:
        await import_csv_dataset(entity_type="returns", file=file, db=db_session)
    assert exc_info.value.status_code == 400
    assert "Missing required columns" in exc_info.value.detail
