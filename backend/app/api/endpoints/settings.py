from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.models import SystemSetting
from app.schemas.schemas import SystemSettingsModel

router = APIRouter()

@router.get("/settings", response_model=SystemSettingsModel)
def get_system_settings(db: Session = Depends(get_db)):
    db_settings = {s.key: s.value for s in db.query(SystemSetting).all()}
    
    return SystemSettingsModel(
        aging_threshold_days=int(db_settings.get("aging_threshold_days", settings.AGING_THRESHOLD_DAYS)),
        expiring_window_threshold_days=int(db_settings.get("expiring_window_threshold_days", settings.EXPIRING_WINDOW_THRESHOLD_DAYS)),
        high_value_threshold=float(db_settings.get("high_value_threshold", settings.HIGH_VALUE_THRESHOLD)),
        defect_anomaly_percentage=float(db_settings.get("defect_anomaly_percentage", settings.DEFECT_ANOMALY_PERCENTAGE)),
        excess_inventory_days=int(db_settings.get("excess_inventory_days", settings.EXCESS_INVENTORY_DAYS)),
        openai_configured=bool(settings.OPENAI_API_KEY),
        openai_model=settings.OPENAI_MODEL
    )

@router.put("/settings")
def update_system_settings(payload: SystemSettingsModel, db: Session = Depends(get_db)):
    def set_key(key: str, val: str):
        item = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if item:
            item.value = val
        else:
            db.add(SystemSetting(key=key, value=val))
            
    set_key("aging_threshold_days", str(payload.aging_threshold_days))
    set_key("expiring_window_threshold_days", str(payload.expiring_window_threshold_days))
    set_key("high_value_threshold", str(payload.high_value_threshold))
    set_key("defect_anomaly_percentage", str(payload.defect_anomaly_percentage))
    set_key("excess_inventory_days", str(payload.excess_inventory_days))
    
    db.commit()
    return {"message": "Settings updated successfully"}
