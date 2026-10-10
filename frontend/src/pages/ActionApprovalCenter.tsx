import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  AlertTriangle,
  History,
  Info,
  DollarSign,
  Package,
  Layers,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';
import { ProposedAction, ActivityLogItem } from '../types';

export const ActionApprovalCenter: React.FC = () => {
  const [actions, setActions] = useState<ProposedAction[]>([]);
  const [logs, setLogs] = useState<ActivityLogItem[]>([]);
  const [selectedTab, setSelectedTab] = useState<string>('Pending');
  const [loading, setLoading] = useState<boolean>(true);
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [selectedTab]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [actionsData, logsData] = await Promise.all([
        api.getActions(selectedTab === 'All' ? undefined : selectedTab),
        api.getActivityLogs(),
      ]);
      setActions(actionsData);
      setLogs(logsData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: number) => {
    setProcessingId(id);
    try {
      await api.approveAction(id, 'Sarah Operations Manager', 'Verified financial recovery and supplier terms');
      setToast(`Action #${id} Approved (Simulated). Audit trail recorded.`);
      await loadData();
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    } finally {
      setProcessingId(null);
      setTimeout(() => setToast(null), 4000);
    }
  };

  const handleReject = async (id: number) => {
    const reason = prompt('Please enter a rejection reason:', 'Requires higher route recovery');
    if (!reason) return;

    setProcessingId(id);
    try {
      await api.rejectAction(id, 'Sarah Operations Manager', reason);
      setToast(`Action #${id} Rejected.`);
      await loadData();
    } catch (err: any) {
      alert(`Rejection error: ${err.message}`);
    } finally {
      setProcessingId(null);
      setTimeout(() => setToast(null), 4000);
    }
  };

  const pendingCount = actions.filter((a) => a.status === 'Pending').length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Action Approval Center</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Operational governance for returns disposition, split-batch plans, and supplier warranty claims.
          </p>
        </div>

        {/* Governance Notice */}
        <div className="px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-[11px] font-semibold flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-amber-600 shrink-0" />
          <span>All business actions require explicit human review before execution.</span>
        </div>
      </div>

      {toast && (
        <div className="p-4 bg-teal-50 border border-teal-300 text-teal-800 rounded-xl text-xs font-bold flex items-center space-x-2 animate-pulse">
          <CheckCircle2 className="w-4 h-4 text-teal-600" />
          <span>{toast}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-200 pb-2">
        {['Pending', 'Approved', 'Rejected', 'All'].map((tab) => (
          <button
            key={tab}
            onClick={() => setSelectedTab(tab)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition flex items-center space-x-2 ${
              selectedTab === tab
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <span>{tab} Actions</span>
            {tab === 'Pending' && pendingCount > 0 && (
              <span className="bg-amber-500 text-slate-950 px-1.5 py-0.2 rounded-full text-[10px] font-extrabold">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Action Cards List */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-500">
          <div className="w-8 h-8 border-3 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          Loading proposed action queue...
        </div>
      ) : actions.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-2">
          <CheckCircle2 className="w-8 h-8 text-teal-500 mx-auto" />
          <h3 className="text-sm font-bold text-slate-800">No actions found in this state.</h3>
          <p className="text-xs text-slate-500">
            Use the Recovery Decision Center or Copilot to generate proposed split-batch plans.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {actions.map((act) => (
            <div
              key={act.id}
              className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 hover:border-slate-300 transition space-y-4"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wider bg-slate-100 text-slate-700">
                      {act.action_type.replace(/_/g, ' ')}
                    </span>
                    <span className="text-xs font-bold text-slate-400 font-mono">
                      Action #{act.id}
                    </span>
                  </div>
                  <h3 className="text-base font-extrabold text-slate-900 leading-tight">
                    {act.action_type === 'SPLIT_BATCH_RECOVERY'
                      ? `Split-Batch Recovery Plan: ${act.proposed_quantity} units`
                      : `${act.action_type.replace(/_/g, ' ')} (${act.proposed_quantity} units)`}
                  </h3>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Estimated Net Recovery</span>
                    <div className="text-lg font-black text-teal-700">
                      ₹{act.estimated_recovery.toLocaleString('en-IN')}
                    </div>
                  </div>

                  {/* Status Badge */}
                  <div>
                    {act.status.includes('Approved') ? (
                      <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-teal-100 text-teal-800 border border-teal-200 flex items-center space-x-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Approved (Simulated)</span>
                      </span>
                    ) : act.status === 'Rejected' ? (
                      <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-red-100 text-red-800 border border-red-200 flex items-center space-x-1">
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Rejected</span>
                      </span>
                    ) : (
                      <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-amber-100 text-amber-800 border border-amber-200 flex items-center space-x-1">
                        <Clock className="w-3.5 h-3.5" />
                        <span>Pending Approval</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Business Justification & Evidence */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-2">
                <span className="font-bold text-slate-900 block text-[11px] uppercase tracking-wider">
                  Operational Justification & Financial Trade-off
                </span>
                <p className="leading-relaxed">{act.explanation}</p>
              </div>

              {/* Simulation Notice & Action Buttons */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pt-2 gap-3">
                <div className="text-[11px] text-slate-500 italic flex items-center space-x-1.5">
                  <Info className="w-3.5 h-3.5 text-slate-400" />
                  <span>SIMULATED BUSINESS ACTION: Updates internal ledger; does not dispatch physical goods.</span>
                </div>

                {act.status === 'Pending' ? (
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleReject(act.id)}
                      disabled={processingId === act.id}
                      className="px-4 py-2 border border-slate-300 hover:bg-slate-100 text-slate-700 rounded-lg text-xs font-bold transition disabled:opacity-50"
                    >
                      Reject
                    </button>
                    <button
                      onClick={() => handleApprove(act.id)}
                      disabled={processingId === act.id}
                      className="px-5 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold transition shadow-sm flex items-center space-x-1.5 disabled:opacity-50"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>{processingId === act.id ? 'Approving...' : 'Approve (Simulated)'}</span>
                    </button>
                  </div>
                ) : (
                  <div className="text-xs text-slate-400">
                    Reviewed by <span className="font-bold text-slate-600">{act.reviewed_by || 'Manager'}</span> at{' '}
                    {act.reviewed_at ? new Date(act.reviewed_at).toLocaleTimeString() : 'N/A'}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ACTIVITY LOG & AUDIT TIMELINE */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-100">
          <History className="w-4 h-4 text-slate-500" />
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Activity Log & Audit Trail
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-4">Timestamp</th>
                <th className="py-2.5 px-4">Actor</th>
                <th className="py-2.5 px-4">Action</th>
                <th className="py-2.5 px-4">Entity</th>
                <th className="py-2.5 px-4">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {logs.slice(0, 10).map((log) => (
                <tr key={log.id} className="hover:bg-slate-50/80">
                  <td className="py-2.5 px-4 text-slate-400">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="py-2.5 px-4 font-bold text-slate-800">{log.actor}</td>
                  <td className="py-2.5 px-4">
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold text-[10px]">
                      {log.action}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-slate-500">
                    {log.entity_type} #{log.entity_id}
                  </td>
                  <td className="py-2.5 px-4 text-slate-600 max-w-md truncate">
                    {JSON.stringify(log.details)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
