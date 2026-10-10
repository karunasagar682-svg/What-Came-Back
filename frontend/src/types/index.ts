export interface ReturnItem {
  id: number;
  return_date: string;
  sku: string;
  product_name: string;
  supplier_name: string;
  supplier_batch: string;
  reason_code: string;
  grade: 'A' | 'B' | 'C' | 'D';
  quantity: number;
  status: string;
  cost_price: number;
  selling_price: number;
  days_waiting: number;
  recommended_route: string;
  estimated_net_recovery: number;
  priority: 'Critical' | 'High' | 'Medium' | 'Low';
  action_id?: number;
  action_type?: string;
  action_status?: string;
}

export interface RouteDetail {
  route: 'Restock' | 'Refurbish' | 'Vendor Return' | 'Liquidation' | 'Scrap';
  is_eligible: boolean;
  ineligibility_reason?: string;
  gross_recovery: number;
  processing_costs: number;
  net_recovery: number;
  recovery_per_unit: number;
  time_to_cash_days: number;
  demand_fit: string;
  assumptions: string[];
  risks: string[];
}

export interface RouteComparisonResult {
  return_id?: number;
  sku: string;
  product_name: string;
  supplier_name: string;
  supplier_batch: string;
  grade: string;
  quantity: number;
  cost_price: number;
  selling_price: number;
  days_waiting: number;
  routes: Record<string, RouteDetail>;
  recommended_route: string;
  recommendation_reason: string;
  best_alternative_route?: string;
  incremental_recovery_over_liquidation: number;
  is_split_recommended: boolean;
  split_recommendation_details?: {
    vendor_quantity: number;
    vendor_net: number;
    remaining_quantity: number;
    remaining_route: string;
    remaining_net: number;
    total_split_net: number;
    incremental_gain_over_liquidation: number;
    notes: string;
  };
}

export interface SplitRouteSummary {
  route: string;
  quantity: number;
  per_unit_net: number;
  subtotal_net_recovery: number;
  time_to_cash_days: number;
  is_eligible: boolean;
  eligibility_note?: string;
}

export interface SplitBatchResponse {
  is_valid: boolean;
  validation_errors: string[];
  total_allocated: number;
  remaining_unallocated: number;
  route_breakdowns: SplitRouteSummary[];
  total_net_recovery: number;
  weighted_time_to_cash_days: number;
  all_liquidation_recovery: number;
  incremental_gain_over_liquidation: number;
  trade_off_explanation: string;
  recommended_action_title: string;
}

export interface PriorityItem {
  id: string;
  problem_category: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  title: string;
  item_or_batch: string;
  sku: string;
  evidence: string;
  financial_impact: number;
  impact_label: string;
  recommended_action: string;
  action_type: string;
  return_id?: number;
  batch?: string;
}

export interface DashboardSummary {
  total_awaiting_decision: number;
  total_recoverable_value: number;
  high_priority_issues_count: number;
  expiring_vendor_windows_count: number;
  supplier_alerts_count: number;
  pending_approvals_count: number;
  returns_by_grade: Record<string, number>;
  returns_by_route: Record<string, number>;
  return_reasons: Record<string, number>;
  recovery_performance_by_route: Record<string, number>;
  urgent_priorities: PriorityItem[];
}

export interface ProposedAction {
  id: number;
  action_type: string;
  related_return_ids: any;
  proposed_quantity: number;
  estimated_recovery: number;
  explanation: string;
  evidence?: any;
  risks_and_assumptions?: any;
  status: 'Pending' | 'Approved (Simulated)' | 'Rejected' | 'Executed (Simulated)';
  created_at: string;
  reviewed_at?: string;
  reviewed_by?: string;
}

export interface ActivityLogItem {
  id: number;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: any;
  created_at: string;
}

export interface BatchIntelligence {
  supplier_batch: string;
  supplier_name: string;
  sku: string;
  product_name: string;
  total_returns: number;
  defect_breakdown: Record<string, number>;
  dominant_defect: string;
  dominant_defect_percentage: number;
  observed_return_rate: number;
  baseline_return_rate: number;
  is_flagged: boolean;
  risk_level: string;
  recommendation: string;
  vendor_window_days: number;
  days_remaining_in_window: number;
  eligible_rtv_quantity: number;
}

export interface SupplierAlert {
  id: number;
  supplier_id: number;
  supplier_name: string;
  sku?: string;
  supplier_batch?: string;
  alert_type: string;
  observed_return_rate: number;
  baseline_return_rate: number;
  evidence: any;
  severity: string;
  status: string;
  created_at: string;
}

export interface CopilotChatResponse {
  response: string;
  provider_used: string;
  tools_called: Array<{ tool: string; args?: any; result?: any }>;
  evidence?: any;
  suggested_actions: string[];
}

export interface SystemSettings {
  aging_threshold_days: number;
  expiring_window_threshold_days: number;
  high_value_threshold: number;
  defect_anomaly_percentage: number;
  excess_inventory_days: number;
  openai_configured: boolean;
  openai_model: string;
}
