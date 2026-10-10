import {
  DashboardSummary,
  PriorityItem,
  ReturnItem,
  RouteComparisonResult,
  SplitBatchResponse,
  ProposedAction,
  ActivityLogItem,
  BatchIntelligence,
  SupplierAlert,
  CopilotChatResponse,
  SystemSettings
} from '../types';

const API_BASE = '/api';

export const api = {
  // Health
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  // Dashboard
  async getDashboardSummary(): Promise<DashboardSummary> {
    const res = await fetch(`${API_BASE}/dashboard/summary`);
    if (!res.ok) throw new Error('Failed to fetch dashboard summary');
    return res.json();
  },

  async getDashboardPriorities(): Promise<PriorityItem[]> {
    const res = await fetch(`${API_BASE}/dashboard/priorities`);
    if (!res.ok) throw new Error('Failed to fetch priorities');
    return res.json();
  },

  // Returns
  async getReturns(params?: Record<string, string>): Promise<ReturnItem[]> {
    const query = new URLSearchParams(params || {}).toString();
    const res = await fetch(`${API_BASE}/returns${query ? `?${query}` : ''}`);
    if (!res.ok) throw new Error('Failed to fetch returns');
    return res.json();
  },

  async getReturnDetail(id: number): Promise<{ return: any; recovery_analysis: RouteComparisonResult }> {
    const res = await fetch(`${API_BASE}/returns/${id}`);
    if (!res.ok) throw new Error('Failed to fetch return details');
    return res.json();
  },

  async createReturn(payload: {
    return_date: string;
    sku: string;
    supplier_batch: string;
    reason_code: string;
    grade: string;
    quantity: number;
    status?: string;
    product_name?: string;
    category?: string;
    cost_price?: number;
    selling_price?: number;
    supplier_name?: string;
    recommended_route?: string;
  }): Promise<ReturnItem> {
    const res = await fetch(`${API_BASE}/returns`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create return record');
    }
    return res.json();
  },

  async updateReturn(id: number, payload: Partial<ReturnItem>): Promise<any> {
    const res = await fetch(`${API_BASE}/returns/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to update return record');
    }
    return res.json();
  },

  // Recovery
  async analyzeRecovery(returnId: number): Promise<RouteComparisonResult> {
    const res = await fetch(`${API_BASE}/recovery/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ return_id: returnId })
    });
    if (!res.ok) throw new Error('Failed to analyze recovery');
    return res.json();
  },

  async simulateSplitPlan(payload: {
    return_id?: number;
    supplier_batch?: string;
    total_quantity: number;
    allocations: Array<{ route: string; quantity: number }>;
  }): Promise<SplitBatchResponse> {
    const res = await fetch(`${API_BASE}/recovery/split-plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to evaluate split batch allocation');
    return res.json();
  },

  // Suppliers
  async getSupplierAlerts(): Promise<SupplierAlert[]> {
    const res = await fetch(`${API_BASE}/suppliers/alerts`);
    if (!res.ok) throw new Error('Failed to fetch supplier alerts');
    return res.json();
  },

  async getBatchIntelligence(batchId: string): Promise<BatchIntelligence> {
    const res = await fetch(`${API_BASE}/suppliers/batches/${batchId}`);
    if (!res.ok) throw new Error('Failed to fetch batch intelligence');
    return res.json();
  },

  // Actions
  async getActions(status?: string): Promise<ProposedAction[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    const res = await fetch(`${API_BASE}/actions${query}`);
    if (!res.ok) throw new Error('Failed to fetch proposed actions');
    return res.json();
  },

  async createAction(payload: {
    action_type: string;
    related_return_ids: number[];
    proposed_quantity: number;
    estimated_recovery: number;
    explanation: string;
    evidence?: any;
    risks_and_assumptions?: any;
  }): Promise<ProposedAction> {
    const res = await fetch(`${API_BASE}/actions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to create proposed action');
    return res.json();
  },

  async approveAction(id: number, actor: string = 'Manager', reason?: string): Promise<ProposedAction> {
    const res = await fetch(`${API_BASE}/actions/${id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor, reason })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to approve action');
    }
    return res.json();
  },

  async rejectAction(id: number, actor: string = 'Manager', reason?: string): Promise<ProposedAction> {
    const res = await fetch(`${API_BASE}/actions/${id}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor, reason })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to reject action');
    }
    return res.json();
  },

  async getActivityLogs(): Promise<ActivityLogItem[]> {
    const res = await fetch(`${API_BASE}/actions/logs`);
    if (!res.ok) throw new Error('Failed to fetch activity logs');
    return res.json();
  },

  // Copilot Chat
  async chatWithCopilot(message: string, history: Array<{ role: string; content: string }> = []): Promise<CopilotChatResponse> {
    const res = await fetch(`${API_BASE}/copilot/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history })
    });
    if (!res.ok) throw new Error('Copilot service error');
    return res.json();
  },

  // Settings & Data
  async getSettings(): Promise<SystemSettings> {
    const res = await fetch(`${API_BASE}/settings`);
    if (!res.ok) throw new Error('Failed to fetch settings');
    return res.json();
  },

  async updateSettings(settings: Partial<SystemSettings>): Promise<any> {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    });
    if (!res.ok) throw new Error('Failed to update settings');
    return res.json();
  },

  async getTemplates(): Promise<Record<string, string>> {
    const res = await fetch(`${API_BASE}/data/templates`);
    if (!res.ok) throw new Error('Failed to load templates');
    return res.json();
  },

  async seedDemoScenario(): Promise<any> {
    const res = await fetch(`${API_BASE}/data/seed-demo`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to load demo scenario');
    return res.json();
  },

  async uploadCsv(entityType: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('entity_type', entityType);
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/data/import`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'CSV upload failed');
    }
    return res.json();
  }
};
