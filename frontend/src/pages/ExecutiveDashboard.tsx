import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowUpRight,
  Clock,
  DollarSign,
  Package,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  CheckCircle,
  ExternalLink,
  PlusCircle,
  X,
  CheckCircle2
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { api } from '../services/api';
import { DashboardSummary } from '../types';

export const ExecutiveDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Manual Data Entry Modal State
  const [showManualModal, setShowManualModal] = useState<boolean>(false);
  const [submittingManual, setSubmittingManual] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

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
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const summary = await api.getDashboardSummary();
      setData(summary);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load executive dashboard data');
    } finally {
      setLoading(false);
    }
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
      setToastMessage(`Return #${res.id} manually created successfully for ${res.product_name}!`);
      await loadData();
    } catch (err: any) {
      alert(`Error creating return: ${err.message}`);
    } finally {
      setSubmittingManual(false);
      setTimeout(() => setToastMessage(null), 5000);
    }
  };

  const setPreset = (presetType: string) => {
    if (presetType === 'headphones') {
      setFormData({
        sku: 'WH-1000XM-B',
        product_name: 'AeroSound Elite Wireless Headphones',
        category: 'Headphones',
        supplier_name: 'SoundWave Dynamics',
        supplier_batch: 'HB-09',
        grade: 'B',
        quantity: 15,
        reason_code: 'Audio Driver Hiss / Bluetooth Drop',
        return_date: new Date().toISOString().split('T')[0],
        cost_price: 1400,
        selling_price: 2500,
      });
    } else if (presetType === 'camera') {
      setFormData({
        sku: 'CAM-PRO-4K',
        product_name: 'Lumix Pro 4K Mirrorless Camera',
        category: 'Cameras',
        supplier_name: 'Optix Vision Systems',
        supplier_batch: 'OP-44',
        grade: 'A',
        quantity: 5,
        reason_code: 'Customer Remorse / Wrong Color',
        return_date: new Date().toISOString().split('T')[0],
        cost_price: 18000,
        selling_price: 28000,
      });
    } else if (presetType === 'watch') {
      setFormData({
        sku: 'SW-FIT-02',
        product_name: 'Pulse Active 2 Smartwatch',
        category: 'Wearables',
        supplier_name: 'Pulse Wearables',
        supplier_batch: 'SW-88',
        grade: 'B',
        quantity: 20,
        reason_code: 'Touchscreen Unresponsive',
        return_date: new Date().toISOString().split('T')[0],
        cost_price: 1200,
        selling_price: 2800,
      });
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-4 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-semibold text-slate-500">Calculating financial recovery routes...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-red-800 space-y-2">
        <div className="flex items-center space-x-2 font-bold">
          <AlertTriangle className="w-5 h-5 text-red-600" />
          <span>Error Loading Dashboard</span>
        </div>
        <p className="text-xs">{error}</p>
        <button
          onClick={loadData}
          className="px-3 py-1 bg-red-600 text-white rounded text-xs font-semibold hover:bg-red-700 transition"
        >
          Retry
        </button>
      </div>
    );
  }

  // Chart data formatting
  const routeChartData = Object.entries(data.recovery_performance_by_route).map(([route, value]) => ({
    route,
    value,
  }));

  const gradeChartData = Object.entries(data.returns_by_grade).map(([grade, count]) => ({
    name: `Grade ${grade}`,
    value: count,
  }));

  const reasonChartData = Object.entries(data.return_reasons).map(([reason, count]) => ({
    reason: reason.length > 20 ? reason.substring(0, 18) + '...' : reason,
    fullName: reason,
    count,
  }));

  const GRADE_COLORS = ['#10b981', '#0d9488', '#f59e0b', '#ef4444'];
  const ROUTE_COLORS: Record<string, string> = {
    'Vendor Return': '#0d9488',
    'Refurbish': '#3b82f6',
    'Split-Batch': '#8b5cf6',
    'Restock': '#10b981',
    'Liquidation': '#f59e0b',
    'Scrap': '#64748b',
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="p-4 bg-teal-50 border border-teal-300 text-teal-800 rounded-xl text-xs font-bold flex items-center justify-between shadow-sm animate-fade-in">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0" />
            <span>{toastMessage}</span>
          </div>
          <button
            onClick={() => navigate('/returns')}
            className="text-xs font-bold text-teal-700 underline hover:text-teal-900 ml-4"
          >
            View in Returns Workbench →
          </button>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Executive Returns Overview</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time returns recovery valuation, supplier quality risks, and required management decisions.
          </p>
        </div>

        {/* Launch Co-Pilot Briefing / Chat with AI & Manual Data Entry Section */}
        <div className="flex items-center space-x-2.5">
          {/* Manual Data Entry Button (placed directly in the briefing section) */}
          <button
            onClick={() => setShowManualModal(true)}
            className="flex items-center space-x-2 px-3.5 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold shadow-sm transition"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Enter Data Manually</span>
          </button>

          {/* Renamed to Chat with AI */}
          <button
            onClick={() => navigate('/copilot')}
            className="flex items-center space-x-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow-sm transition"
          >
            <Sparkles className="w-3.5 h-3.5 text-teal-400" />
            <span>Chat with AI</span>
          </button>
        </div>
      </div>

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-sm space-y-1">
          <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider flex items-center space-x-1">
            <Package className="w-3.5 h-3.5 text-slate-400" />
            <span>Awaiting Decision</span>
          </span>
          <div className="text-2xl font-extrabold text-slate-900">
            {data.total_awaiting_decision} <span className="text-xs font-normal text-slate-500">units</span>
          </div>
          <p className="text-[10px] text-slate-400">Inventory awaiting routing</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-sm space-y-1">
          <span className="text-[11px] font-medium text-teal-700 uppercase tracking-wider flex items-center space-x-1">
            <DollarSign className="w-3.5 h-3.5 text-teal-600" />
            <span>Recoverable Value</span>
          </span>
          <div className="text-2xl font-extrabold text-teal-700">
            ₹{data.total_recoverable_value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <p className="text-[10px] text-teal-600">Deterministic net valuation</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-sm space-y-1">
          <span className="text-[11px] font-medium text-red-600 uppercase tracking-wider flex items-center space-x-1">
            <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
            <span>High-Priority Issues</span>
          </span>
          <div className="text-2xl font-extrabold text-red-600">
            {data.high_priority_issues_count}
          </div>
          <p className="text-[10px] text-slate-400">Aging & Value Destruction</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-sm space-y-1">
          <span className="text-[11px] font-medium text-amber-600 uppercase tracking-wider flex items-center space-x-1">
            <Clock className="w-3.5 h-3.5 text-amber-500" />
            <span>RTV Windows Expiring</span>
          </span>
          <div className="text-2xl font-extrabold text-amber-600">
            {data.expiring_vendor_windows_count}
          </div>
          <p className="text-[10px] text-slate-400">≤ 7 days before forfeiture</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-sm space-y-1">
          <span className="text-[11px] font-medium text-purple-700 uppercase tracking-wider flex items-center space-x-1">
            <ShieldAlert className="w-3.5 h-3.5 text-purple-600" />
            <span>Supplier Alerts</span>
          </span>
          <div className="text-2xl font-extrabold text-purple-700">
            {data.supplier_alerts_count}
          </div>
          <p className="text-[10px] text-slate-400">Defect clusters active</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-sm space-y-1">
          <span className="text-[11px] font-medium text-blue-700 uppercase tracking-wider flex items-center space-x-1">
            <CheckCircle className="w-3.5 h-3.5 text-blue-600" />
            <span>Pending Approvals</span>
          </span>
          <div className="text-2xl font-extrabold text-blue-700">
            {data.pending_approvals_count}
          </div>
          <p className="text-[10px] text-slate-400">Awaiting human sign-off</p>
        </div>
      </div>

      {/* HERO SECTION: "WHAT NEEDS YOUR ATTENTION TODAY?" */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-6 text-white shadow-lg border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-teal-500/20 border border-teal-500/30 rounded-lg text-teal-300">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-black tracking-wider text-teal-400 uppercase">
                WHAT NEEDS YOUR ATTENTION TODAY?
              </h2>
              <p className="text-xs text-slate-300">
                Top operational priorities detected across all 5 mandatory recovery and supplier risk categories.
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowManualModal(true)}
              className="text-xs font-bold text-teal-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Log Return Manually</span>
            </button>
            <button
              onClick={() => navigate('/returns')}
              className="text-xs font-semibold text-slate-300 hover:text-white flex items-center space-x-1 transition px-2 py-1"
            >
              <span>View All</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.urgent_priorities.map((item, idx) => (
            <div
              key={item.id || idx}
              className="bg-slate-800/80 hover:bg-slate-800 border border-slate-700 hover:border-teal-500/50 rounded-xl p-4 flex flex-col justify-between transition group shadow-sm"
            >
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                      item.severity === 'Critical'
                        ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    }`}
                  >
                    {item.severity}
                  </span>
                  <span className="text-[11px] font-semibold text-teal-300">
                    ₹{item.financial_impact.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </div>

                <div>
                  <h3 className="text-xs font-bold text-white group-hover:text-teal-300 transition leading-snug">
                    {item.title}
                  </h3>
                  <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                    {item.item_or_batch}
                  </p>
                </div>

                <p className="text-[11px] text-slate-300 leading-relaxed bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  {item.evidence}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-700/80 flex items-center justify-between">
                <span className="text-[10px] text-slate-400 italic">
                  {item.problem_category.substring(0, 24)}...
                </span>
                <button
                  onClick={() => {
                    if (item.batch === 'HB-09') {
                      navigate('/suppliers');
                    } else if (item.return_id) {
                      navigate(`/recovery?return_id=${item.return_id}`);
                    } else {
                      navigate('/returns');
                    }
                  }}
                  className="px-2.5 py-1 bg-teal-600 hover:bg-teal-500 text-white rounded text-[11px] font-semibold flex items-center space-x-1 transition shadow-sm"
                >
                  <span>Resolve</span>
                  <ExternalLink className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Visual Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recovery Performance by Route */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Recoverable Value by Route
              </h3>
              <p className="text-[11px] text-slate-400">Total net valuation distribution</p>
            </div>
            <TrendingUp className="w-4 h-4 text-teal-600" />
          </div>

          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={routeChartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <XAxis dataKey="route" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip
                  formatter={(val: any) => [`₹${Number(val).toLocaleString('en-IN')}`, 'Recoverable Value']}
                  contentStyle={{ backgroundColor: '#0f172a', color: '#fff', borderRadius: '8px', fontSize: '11px' }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {routeChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={ROUTE_COLORS[entry.route] || '#0d9488'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Returns by Condition Grade */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Condition Grade Breakdown
              </h3>
              <p className="text-[11px] text-slate-400">Physical triage distribution</p>
            </div>
            <Package className="w-4 h-4 text-slate-400" />
          </div>

          <div className="h-56 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={gradeChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="value"
                  label={({ name, percent }: any) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  labelLine={false}
                >
                  {gradeChartData.map((entry, index) => (
                    <Cell key={`pie-cell-${index}`} fill={GRADE_COLORS[index % GRADE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', color: '#fff', borderRadius: '8px', fontSize: '11px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Return Reasons */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Top Return Reasons
              </h3>
              <p className="text-[11px] text-slate-400">Unit counts by reported reason</p>
            </div>
            <ShieldAlert className="w-4 h-4 text-purple-600" />
          </div>

          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={reasonChartData} layout="vertical" margin={{ top: 5, right: 15, left: 10, bottom: 5 }}>
                <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis dataKey="reason" type="category" width={95} tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip
                  formatter={(val: any, name: any, item: any) => [`${val} units`, item.payload.fullName]}
                  contentStyle={{ backgroundColor: '#0f172a', color: '#fff', borderRadius: '8px', fontSize: '11px' }}
                />
                <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* MANUAL DATA ENTRY MODAL */}
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
                    Log an incoming returned batch directly into the recovery ledger.
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

            {/* Quick Demo Fill Presets */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5">
              <span className="font-bold text-slate-700 text-[11px] uppercase tracking-wider block">
                Quick Sample Presets:
              </span>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setPreset('headphones')}
                  className="px-2.5 py-1 bg-white hover:bg-teal-50 border border-slate-200 hover:border-teal-300 rounded text-[11px] font-semibold text-slate-700 transition"
                >
                  🎧 Headphones (Batch HB-09)
                </button>
                <button
                  type="button"
                  onClick={() => setPreset('camera')}
                  className="px-2.5 py-1 bg-white hover:bg-teal-50 border border-slate-200 hover:border-teal-300 rounded text-[11px] font-semibold text-slate-700 transition"
                >
                  📷 Lumix Camera (Grade A)
                </button>
                <button
                  type="button"
                  onClick={() => setPreset('watch')}
                  className="px-2.5 py-1 bg-white hover:bg-teal-50 border border-slate-200 hover:border-teal-300 rounded text-[11px] font-semibold text-slate-700 transition"
                >
                  ⌚ Smartwatch (Batch SW-88)
                </button>
              </div>
            </div>

            {/* Form */}
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
                    <option value="A">Grade A (Pristine / Unopened)</option>
                    <option value="B">Grade B (Minor Defect / Refurbishable)</option>
                    <option value="C">Grade C (Heavy Wear / Major Repair)</option>
                    <option value="D">Grade D (Damaged / Scrap Only)</option>
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
                  <CheckCircle className="w-3.5 h-3.5" />
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
