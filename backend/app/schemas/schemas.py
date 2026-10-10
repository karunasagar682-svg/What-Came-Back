from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, date

# --- Product Schemas ---
class ProductBase(BaseModel):
    sku: str
    name: str
    category: str
    cost_price: float
    selling_price: float
    supplier_id: int

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# --- Supplier Schemas ---
class SupplierBase(BaseModel):
    supplier_name: str
    contact_email: str
    status: str = "Active"

class SupplierCreate(SupplierBase):
    pass

class SupplierResponse(SupplierBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# --- Return Schemas ---
class ReturnBase(BaseModel):
    return_date: date
    sku: str
    supplier_batch: str
    reason_code: str
    grade: str
    quantity: int = 1
    status: str = "Pending Decision"
    recommended_route: Optional[str] = None

class ReturnCreate(ReturnBase):
    product_name: Optional[str] = None
    category: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    supplier_name: Optional[str] = None

class ReturnResponse(ReturnBase):
    id: int
    received_at: datetime
    created_at: datetime
    product_name: Optional[str] = None
    supplier_name: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    days_waiting: Optional[int] = None
    estimated_net_recovery: Optional[float] = None
    priority: Optional[str] = "Medium"
    action_id: Optional[int] = None
    action_type: Optional[str] = None
    action_status: Optional[str] = None
    class Config:
        from_attributes = True


# --- Recovery Route Calculation Schemas ---
class RouteDetail(BaseModel):
    route: str  # Restock, Refurbish, Vendor Return, Liquidation, Scrap
    is_eligible: bool
    ineligibility_reason: Optional[str] = None
    gross_recovery: float
    processing_costs: float
    net_recovery: float
    recovery_per_unit: float
    time_to_cash_days: int
    demand_fit: str  # High, Medium, Low, Excess Risk, N/A
    assumptions: List[str]
    risks: List[str]

class RouteComparisonResult(BaseModel):
    return_id: Optional[int] = None
    sku: str
    product_name: str
    supplier_name: str
    supplier_batch: str
    grade: str
    quantity: int
    cost_price: float
    selling_price: float
    days_waiting: int
    routes: Dict[str, RouteDetail]
    recommended_route: str
    recommendation_reason: str
    best_alternative_route: Optional[str] = None
    incremental_recovery_over_liquidation: float
    is_split_recommended: bool = False
    split_recommendation_details: Optional[Dict[str, Any]] = None


# --- Split Batch Schemas ---
class SplitBatchAllocationItem(BaseModel):
    route: str
    quantity: int

class SplitBatchRequest(BaseModel):
    return_id: Optional[int] = None
    sku: Optional[str] = None
    supplier_batch: Optional[str] = None
    total_quantity: int
    allocations: List[SplitBatchAllocationItem]

class SplitBatchRouteSummary(BaseModel):
    route: str
    quantity: int
    per_unit_net: float
    subtotal_net_recovery: float
    time_to_cash_days: int
    is_eligible: bool
    eligibility_note: Optional[str] = None

class SplitBatchResponse(BaseModel):
    is_valid: bool
    validation_errors: List[str] = []
    total_allocated: int
    remaining_unallocated: int
    route_breakdowns: List[SplitBatchRouteSummary]
    total_net_recovery: float
    weighted_time_to_cash_days: float
    all_liquidation_recovery: float
    incremental_gain_over_liquidation: float
    trade_off_explanation: str
    recommended_action_title: str


# --- Supplier Intelligence Schemas ---
class SupplierAlertResponse(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str
    sku: Optional[str] = None
    supplier_batch: Optional[str] = None
    alert_type: str
    observed_return_rate: float
    baseline_return_rate: float
    evidence: Dict[str, Any]
    severity: str
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class BatchIntelligenceResponse(BaseModel):
    supplier_batch: str
    supplier_name: str
    sku: str
    product_name: str
    total_returns: int
    defect_breakdown: Dict[str, int]
    dominant_defect: str
    dominant_defect_percentage: float
    observed_return_rate: float
    baseline_return_rate: float
    is_flagged: bool
    risk_level: str
    recommendation: str
    vendor_window_days: int
    days_remaining_in_window: int
    eligible_rtv_quantity: int


# --- Proposed Action Schemas ---
class ProposedActionCreate(BaseModel):
    action_type: str
    related_return_ids: List[int] = []
    supplier_batch: Optional[str] = None
    sku: Optional[str] = None
    proposed_quantity: int
    estimated_recovery: float
    explanation: str
    evidence: Optional[Dict[str, Any]] = None
    risks_and_assumptions: Optional[Dict[str, Any]] = None

class ProposedActionResponse(BaseModel):
    id: int
    action_type: str
    related_return_ids: Any
    proposed_quantity: int
    estimated_recovery: float
    explanation: str
    evidence: Optional[Dict[str, Any]] = None
    risks_and_assumptions: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    class Config:
        from_attributes = True

class ActionDecisionRequest(BaseModel):
    actor: str = "Manager"
    reason: Optional[str] = None


# --- Activity Log Schemas ---
class ActivityLogResponse(BaseModel):
    id: int
    actor: str
    action: str
    entity_type: str
    entity_id: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime
    class Config:
        from_attributes = True


# --- Copilot Schemas ---
class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str

class CopilotChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []

class CopilotChatResponse(BaseModel):
    response: str
    provider_used: str  # "OpenAI (gpt-4o)" or "Deterministic Recovery Copilot Engine (Rule-based Fallback)"
    tools_called: List[Dict[str, Any]] = []
    evidence: Optional[Dict[str, Any]] = None
    suggested_actions: List[str] = []


# --- Dashboard Schemas ---
class PriorityItem(BaseModel):
    id: str
    problem_category: str  # Problem 1-5
    severity: str  # Critical, High, Medium
    title: str
    item_or_batch: str
    sku: str
    evidence: str
    financial_impact: float
    impact_label: str
    recommended_action: str
    action_type: str
    return_id: Optional[int] = None
    batch: Optional[str] = None

class DashboardSummaryResponse(BaseModel):
    total_awaiting_decision: int
    total_recoverable_value: float
    high_priority_issues_count: int
    expiring_vendor_windows_count: int
    supplier_alerts_count: int
    pending_approvals_count: int
    returns_by_grade: Dict[str, int]
    returns_by_route: Dict[str, int]
    return_reasons: Dict[str, int]
    recovery_performance_by_route: Dict[str, float]
    urgent_priorities: List[PriorityItem]


# --- Settings & Ingestion Schemas ---
class SystemSettingsModel(BaseModel):
    aging_threshold_days: int
    expiring_window_threshold_days: int
    high_value_threshold: float
    defect_anomaly_percentage: float
    excess_inventory_days: int
    openai_configured: bool
    openai_model: str

class CsvImportResult(BaseModel):
    entity: str
    total_rows: int
    successful_rows: int
    failed_rows: int
    errors: List[str]
