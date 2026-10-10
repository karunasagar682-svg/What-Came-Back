import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  RefreshCw,
  PlusCircle,
  Clock,
  CheckCircle2,
  Package,
  X,
  Scale,
  ExternalLink,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';
import { api } from '../services/api';
import { ReturnItem, RouteComparisonResult } from '../types';

const getDispositionStatusClasses = (status: string): string => {
  const normalizedStatus = (status || '').toLowerCase();

  if (normalizedStatus.includes('approved') || normalizedStatus === 'completed' || normalizedStatus === 'processed') {
    return 'bg-emerald-50 text-emerald-800 border-emerald-300';
  }
  if (normalizedStatus.includes('rejected') || normalizedStatus.includes('cancelled')) {
    return 'bg-red-50 text-red-800 border-red-300';
  }
  if (normalizedStatus.includes('process')) {
    return 'bg-blue-50 text-blue-800 border-blue-300';
  }
  if (normalizedStatus.includes('pending') || normalizedStatus.includes('decision')) {
    return 'bg-amber-50 text-amber-800 border-amber-300';
  }
  return 'bg-slate-50 text-slate-700 border-slate-300';
};

const DispositionStatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <span
    className={`inline-flex items-center rounded-lg border px-2.5 py-1 text-[11px] font-bold ${getDispositionStatusClasses(status)}`}
    title={`Current disposition status: ${status || 'Unknown'}`}
  >
    <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-current" />
    {status || 'Unknown'}
  </span>
);

export const ReturnsWorkbench: React.FC = () => {
  const navigate = useNavigate();
  const [returns, setReturns] = useState<ReturnItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [search, setSearch] = useState<string>('');
  const [selectedGrade, setSelectedGrade] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [selectedRoute, setSelectedRoute] = useState<string>('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Drawer state
  const [selectedReturn, setSelectedReturn] = useState<ReturnItem | null>(null);
  const [analysisDetail, setAnalysisDetail] = useState<RouteComparisonResult | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState<boolean>(false);

  // Manual Entry Modal on Workbench
  const [showManualModal, setShowManualModal] = useState<boolean>(false);
  const [submittingManual, setSubmittingManual] = useState<boolean>(false);
  const [formData, setFormData] = useState({
    sku: 'WH-1000XM-B',
    product_name: 'AeroSound Elite Wireless Headphones',
    category: 'Headphones',
    supplier_name: 'SoundWave Dynamics',
    supplier_batch: 'HB-09',
    grade: 'B',
    quantity: 10,
    reason_code: 'Audio Driver Hiss / Bluetooth Drop',
    return_date: new Date().toISOString().split('T')[0],
    cost_price: 1400,
    selling_price: 2500,
  });

  useEffect(() => {
    loadReturns();
  }, [selectedGrade, selectedStatus, selectedRoute]);

  const loadReturns = async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (selectedGrade) params.grade = selectedGrade;
      if (selectedStatus) params.status = selectedStatus;
      if (selectedRoute) params.recommended_route = selectedRoute;
      if (search) params.search = search;

      const data = await api.getReturns(params);
      setReturns(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadReturns();
    setRefreshing(false);
    setToastMessage('Returns workbench table refreshed.');
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadReturns();
  };


  const openReturnDetail = async (item: ReturnItem) => {
    setSelectedReturn(item);
    setLoadingAnalysis(true);
    try {
      const res = await api.analyzeRecovery(item.id);
      setAnalysisDetail(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const closeDetail = () => {
    setSelectedReturn(null);
    setAnalysisDetail(null);
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingManual(true);
    try {
      const res = await api.createReturn({
        sku: formData.sku,
        product_name: formData.product_name,
        category: formData.category,
        supplier_name: formData.supplier_name,
        supplier_batch: formData.supplier_batch,
        grade: formData.grade,
        quantity: Number(formData.quantity),
        reason_code: formData.reason_code,
        return_date: formData.return_date,
        cost_price: Number(formData.cost_price),
        selling_price: Number(formData.selling_price),
        status: 'Pending Decision'
      });
      setShowManualModal(false);
      setToastMessage(`Return #${res.id} manually created successfully!`);
      await loadReturns();
    } catch (err: any) {
      alert(`Error creating return: ${err.message}`);
    } finally {
      setSubmittingManual(false);
      setTimeout(() => setToastMessage(null), 4000);
    }
  };

  return (
    <div className="space-y-5 max-w-7xl mx-auto pb-12">
      {/* Toast */}
      {toastMessage && (
        <div className="p-3.5 bg-teal-50 border border-teal-300 text-teal-800 rounded-xl text-xs font-bold flex items-center space-x-2 animate-fade-in shadow-sm">
          <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Returns Workbench</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Operational triage ledger. Real-time disposition status, route evaluations, and Action Approval tasks.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          {/* Manual Entry Button */}
          <button
            onClick={() => setShowManualModal(true)}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold transition shadow-sm"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Enter Return Manually</span>
          </button>

          {/* Refresh Table Button */}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-lg text-xs font-bold transition shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-teal-600' : ''}`} />
            <span>Refresh Table</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by SKU, product name, batch (e.g. HB-09)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <select
              value={selectedGrade}
              onChange={(e) => setSelectedGrade(e.target.value)}
              className="px-3 py-2 border border-slate-200 rounded-lg text-xs bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500 font-semibold"
            >
              <option value="">All Grades</option>
              <option value="A">Grade A (Pristine)</option>
              <option value="B">Grade B (Minor Defect)</option>
              <option value="C">Grade C (Heavy Wear)</option>
              <option value="D">Grade D (Damaged / Scrap)</option>
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-3 py-2 border border-slate-200 rounded-lg text-xs bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500 font-semibold"
            >
              <option value="">All Statuses</option>
              <option value="Pending Decision">Pending Decision</option>
              <option value="Action Approved">Action Approved</option>
              <option value="In Process">In Process</option>
              <option value="Action Rejected">Action Rejected</option>
              <option value="Completed">Completed</option>
            </select>

            <select
              value={selectedRoute}
              onChange={(e) => setSelectedRoute(e.target.value)}
              className="px-3 py-2 border border-slate-200 rounded-lg text-xs bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500 font-semibold"
            >
              <option value="">All Routes</option>
              <option value="Vendor Return">Vendor Return</option>
              <option value="Refurbish">Refurbish</option>
              <option value="Split-Batch">Split-Batch</option>
              <option value="Restock">Restock</option>
              <option value="Liquidation">Liquidation</option>
              <option value="Scrap">Scrap</option>
            </select>

            <button
              type="submit"
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition"
            >
              Apply Filter
            </button>
          </div>
        </form>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs font-semibold text-slate-500">
            <div className="w-8 h-8 border-3 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            Loading returns catalog...
          </div>
        ) : returns.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <Package className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="text-xs font-semibold text-slate-600">No returns found matching the current filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3 px-3">ID</th>
                  <th className="py-3 px-4">Product & SKU</th>
                  <th className="py-3 px-3">Batch</th>
                  <th className="py-3 px-3">Grade</th>
                  <th className="py-3 px-3">Qty</th>
                  <th className="py-3 px-3">Defect Reason</th>
                  <th className="py-3 px-3">Days Waiting</th>
                  <th className="py-3 px-3">Recommended Route</th>
                  <th className="py-3 px-3">Net Recovery</th>
                  <th className="py-3 px-4">Disposition Status</th>
                  <th className="py-3 px-4">Action Approval Task</th>
                  <th className="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {returns.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-50/80 transition cursor-pointer"
                    onClick={() => openReturnDetail(item)}
                  >
                    <td className="py-3 px-3 font-mono text-slate-500 font-bold">#{item.id}</td>
                    
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-900 leading-snug">{item.product_name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{item.sku}</div>
                    </td>

                    <td className="py-3 px-3">
                      <span className={`font-mono font-semibold px-2 py-0.5 rounded text-[11px] ${
                        item.supplier_batch === 'HB-09' ? 'bg-purple-100 text-purple-800 border border-purple-200 font-bold' : 'text-slate-600'
                      }`}>
                        {item.supplier_batch}
                      </span>
                    </td>

                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        item.grade === 'A' ? 'bg-emerald-100 text-emerald-800' :
                        item.grade === 'B' ? 'bg-teal-100 text-teal-800' :
                        item.grade === 'C' ? 'bg-amber-100 text-amber-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        Grade {item.grade}
                      </span>
                    </td>

                    <td className="py-3 px-3 font-bold text-slate-800">{item.quantity}</td>

                    <td className="py-3 px-3 text-slate-600 max-w-[130px] truncate" title={item.reason_code}>
                      {item.reason_code}
                    </td>

                    <td className="py-3 px-3">
                      <span className={`font-semibold flex items-center space-x-1 text-[11px] ${
                        item.days_waiting >= 14 ? 'text-red-600' :
                        item.days_waiting >= 7 ? 'text-amber-600' : 'text-slate-600'
                      }`}>
                        <Clock className="w-3 h-3 shrink-0" />
                        <span>{item.days_waiting}d</span>
                      </span>
                    </td>

                    <td className="py-3 px-3">
                      <span className="font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200 text-[11px]">
                        {item.recommended_route}
                      </span>
                    </td>

                    <td className="py-3 px-3 font-black text-slate-900">
                      ₹{item.estimated_net_recovery?.toLocaleString('en-IN') || 0}
                    </td>

                    {/* DISPOSITION STATUS: dynamically reflects the current backend status */}
                    <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                      <DispositionStatusBadge status={item.status} />
                    </td>

                    {/* ACTION APPROVAL TASK COLUMN (Reflects Action Approval Center tasks) */}
                    <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                      {item.action_id ? (
                        <div className="space-y-1">
                          <button
                            onClick={() => navigate('/approvals')}
                            className="text-left group flex items-center space-x-1"
                          >
                            <span className="font-mono text-[10px] text-purple-700 font-bold bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200 group-hover:bg-purple-100 transition">
                              Task #{item.action_id}
                            </span>
                            <span className={`text-[10px] font-extrabold px-1.5 py-0.5 rounded ${
                              item.action_status?.includes('Approved')
                                ? 'bg-emerald-100 text-emerald-800'
                                : item.action_status === 'Rejected'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-amber-100 text-amber-800'
                            }`}>
                              {item.action_status || 'Pending'}
                            </span>
                          </button>
                          <div className="text-[10px] text-slate-500 font-medium truncate max-w-[140px]">
                            {item.action_type?.replace(/_/g, ' ')}
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => navigate(`/recovery?return_id=${item.id}`)}
                          className="px-2 py-0.5 rounded bg-slate-100 hover:bg-teal-50 text-slate-600 hover:text-teal-700 border border-slate-200 text-[10px] font-bold transition flex items-center space-x-1"
                        >
                          <Scale className="w-3 h-3" />
                          <span>Assign Task</span>
                        </button>
                      )}
                    </td>

                    <td className="py-3 px-3 text-right" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => openReturnDetail(item)}
                        className="px-2.5 py-1 text-[11px] font-semibold text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded transition"
                      >
                        Analyze
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detail Drawer / Modal */}
      {selectedReturn && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex justify-end">
          <div className="bg-white w-full max-w-2xl h-full shadow-2xl overflow-y-auto p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-200 pb-4">
              <div>
                <span className="text-[10px] font-bold text-teal-600 uppercase tracking-wider">
                  Returns Routing Engine
                </span>
                <h2 className="text-lg font-black text-slate-900">
                  {selectedReturn.product_name}
                </h2>
                <p className="text-xs text-slate-400 font-mono">
                  Return #{selectedReturn.id} | SKU: {selectedReturn.sku} | Batch: {selectedReturn.supplier_batch}
                </p>
              </div>
              <button
                onClick={closeDetail}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Basic Info Cards */}
            <div className="grid grid-cols-4 gap-3">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Quantity</span>
                <div className="text-base font-bold text-slate-900">{selectedReturn.quantity} units</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Condition</span>
                <div className="text-base font-bold text-teal-700">Grade {selectedReturn.grade}</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Retail Price</span>
                <div className="text-base font-bold text-slate-900">₹{selectedReturn.selling_price}</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Cost Price</span>
                <div className="text-base font-bold text-slate-900">₹{selectedReturn.cost_price}</div>
              </div>
            </div>

            {/* Dynamic current status; status changes remain managed by the existing action workflow */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between gap-3">
              <div>
                <span className="text-xs font-bold text-slate-800 block">Disposition Status</span>
                <span className="text-[11px] text-slate-500">Current status from the returns record</span>
              </div>
              <DispositionStatusBadge status={selectedReturn.status} />
            </div>

            {/* Route Analysis Comparison */}
            {loadingAnalysis ? (
              <div className="py-12 text-center text-xs text-slate-400">
                Calculating recovery equations...
              </div>
            ) : analysisDetail ? (
              <div className="space-y-4">
                <div className="p-4 bg-teal-50/70 border border-teal-200 rounded-xl space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-teal-900">
                      Recommendation: {analysisDetail.recommended_route}
                    </span>
                    <span className="text-xs font-extrabold text-teal-800">
                      +₹{analysisDetail.incremental_recovery_over_liquidation.toLocaleString('en-IN')} vs Liquidation
                    </span>
                  </div>
                  <p className="text-xs text-teal-800 leading-relaxed">
                    {analysisDetail.recommendation_reason}
                  </p>
                </div>

                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Side-by-Side Route Comparison
                </h3>

                <div className="space-y-2.5">
                  {Object.entries(analysisDetail.routes).map(([name, route]) => (
                    <div
                      key={name}
                      className={`p-3.5 rounded-xl border transition ${
                        route.is_eligible
                          ? name === analysisDetail.recommended_route
                            ? 'bg-teal-50/40 border-teal-400 shadow-sm'
                            : 'bg-white border-slate-200'
                          : 'bg-slate-50 border-slate-200 opacity-60'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-bold text-slate-900">{name}</span>
                          {!route.is_eligible && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-red-100 text-red-700 font-semibold">
                              Ineligible
                            </span>
                          )}
                          {name === analysisDetail.recommended_route && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-teal-600 text-white font-bold">
                              Best Choice
                            </span>
                          )}
                        </div>
                        <div className="text-right">
                          <span className="text-xs font-extrabold text-slate-900">
                            {route.is_eligible ? `₹${route.net_recovery.toLocaleString('en-IN')}` : '₹0'}
                          </span>
                          <span className="text-[10px] text-slate-400 ml-1">
                            (₹{route.recovery_per_unit}/unit)
                          </span>
                        </div>
                      </div>

                      <div className="mt-2 grid grid-cols-3 gap-2 text-[11px] text-slate-500">
                        <div>
                          <span className="text-slate-400 block text-[10px]">Processing Costs</span>
                          <span>₹{route.processing_costs.toLocaleString('en-IN')}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Time-to-Cash</span>
                          <span>{route.time_to_cash_days} days</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Demand Fit</span>
                          <span className="font-medium text-slate-700">{route.demand_fit}</span>
                        </div>
                      </div>

                      {route.ineligibility_reason && (
                        <p className="mt-2 text-[10px] text-red-600 bg-red-50 p-1.5 rounded">
                          {route.ineligibility_reason}
                        </p>
                      )}
                    </div>
                  ))}
                </div>

                {/* Direct Action Navigation */}
                <div className="pt-4 border-t border-slate-200 flex items-center justify-between gap-3">
                  <button
                    onClick={() => {
                      closeDetail();
                      navigate(`/recovery?return_id=${selectedReturn.id}`);
                    }}
                    className="flex-1 py-2.5 px-4 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 shadow-sm"
                  >
                    <Scale className="w-4 h-4" />
                    <span>Open in Recovery Decision Center / Split Planner</span>
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* MANUAL DATA ENTRY MODAL ON WORKBENCH */}
      {showManualModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5 animate-scale-in">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-teal-100 flex items-center justify-center text-teal-700">
                  <PlusCircle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-black text-slate-900">Manual Return Data Entry</h3>
                  <p className="text-xs text-slate-500">
                    Log an incoming returned batch directly into the Returns Workbench ledger.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowManualModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleManualSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">SKU:</label>
                  <input
                    type="text"
                    required
                    value={formData.sku}
                    onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 font-mono"
                    placeholder="e.g. WH-1000XM-B"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Product Name:</label>
                  <input
                    type="text"
                    required
                    value={formData.product_name}
                    onChange={(e) => setFormData({ ...formData, product_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                    placeholder="e.g. AeroSound Elite Headphones"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Category:</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-teal-500"
                  >
                    <option value="Headphones">Headphones</option>
                    <option value="Cameras">Cameras</option>
                    <option value="Laptops">Laptops</option>
                    <option value="Wearables">Wearables</option>
                    <option value="Audio">Audio</option>
                    <option value="Electronics">Other Electronics</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Supplier Name:</label>
                  <input
                    type="text"
                    required
                    value={formData.supplier_name}
                    onChange={(e) => setFormData({ ...formData, supplier_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                    placeholder="e.g. SoundWave Dynamics"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Supplier Batch:</label>
                  <input
                    type="text"
                    required
                    value={formData.supplier_batch}
                    onChange={(e) => setFormData({ ...formData, supplier_batch: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 font-mono"
                    placeholder="e.g. HB-09"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Return Date:</label>
                  <input
                    type="date"
                    required
                    value={formData.return_date}
                    onChange={(e) => setFormData({ ...formData, return_date: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Quantity (Units):</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={formData.quantity}
                    onChange={(e) => setFormData({ ...formData, quantity: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 font-bold"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Condition Grade:</label>
                  <select
                    value={formData.grade}
                    onChange={(e) => setFormData({ ...formData, grade: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-teal-500 font-bold"
                  >
                    <option value="A">Grade A (Pristine)</option>
                    <option value="B">Grade B (Minor Defect)</option>
                    <option value="C">Grade C (Heavy Wear)</option>
                    <option value="D">Grade D (Damaged / Scrap)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Cost Price (₹ per unit):</label>
                  <input
                    type="number"
                    min="0"
                    required
                    value={formData.cost_price}
                    onChange={(e) => setFormData({ ...formData, cost_price: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Selling Price (₹ per unit):</label>
                  <input
                    type="number"
                    min="0"
                    required
                    value={formData.selling_price}
                    onChange={(e) => setFormData({ ...formData, selling_price: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 font-mono"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block font-bold text-slate-700 mb-1">Reported Defect / Reason:</label>
                  <input
                    type="text"
                    required
                    value={formData.reason_code}
                    onChange={(e) => setFormData({ ...formData, reason_code: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                    placeholder="e.g. Audio Driver Hiss / Bluetooth Drop"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowManualModal(false)}
                  className="px-4 py-2 border border-slate-300 hover:bg-slate-100 text-slate-700 rounded-lg text-xs font-bold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingManual}
                  className="px-5 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold transition shadow-sm flex items-center space-x-1.5 disabled:opacity-50"
                >
                  <span>{submittingManual ? 'Saving...' : 'Save & Calculate Recovery'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
