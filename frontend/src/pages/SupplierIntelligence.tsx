import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  TrendingUp,
  Cpu,
  Package,
  Clock,
  CheckCircle2,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  LineChart,
  Line,
  Cell
} from 'recharts';
import { api } from '../services/api';
import { BatchIntelligence, SupplierAlert } from '../types';

export const SupplierIntelligence: React.FC = () => {
  const [alerts, setAlerts] = useState<SupplierAlert[]>([]);
  const [batchHB09, setBatchHB09] = useState<BatchIntelligence | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedBatchCode, setSelectedBatchCode] = useState<string>('HB-09');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [alertsRes, hb09Res] = await Promise.all([
        api.getSupplierAlerts(),
        api.getBatchIntelligence('HB-09'),
      ]);
      setAlerts(alertsRes);
      setBatchHB09(hb09Res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const defectChartData = batchHB09
    ? Object.entries(batchHB09.defect_breakdown).map(([reason, count]) => ({
        reason,
        count,
        percentage: ((count / batchHB09.total_returns) * 100).toFixed(0),
      }))
    : [];

  const trendData = [
    { period: 'Week 1', baseline: 5, observed: 6 },
    { period: 'Week 2', baseline: 5, observed: 7 },
    { period: 'Week 3 (HB-09 Batch)', baseline: 5, observed: 28 },
    { period: 'Week 4', baseline: 5, observed: 22 },
  ];

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-3 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-semibold text-slate-500">Compiling supplier intelligence metrics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Supplier Intelligence & Defect Analytics</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Identify supplier quality anomalies, detect concentrated defect clusters, and preserve vendor warranty claims.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="px-2.5 py-1 bg-purple-50 text-purple-700 border border-purple-200 rounded-lg text-xs font-bold">
            Statistical Baseline: 5.0% Expected
          </span>
        </div>
      </div>

      {/* DEDICATED SPOTLIGHT CARD: BATCH HB-09 */}
      {batchHB09 && (
        <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-2xl p-6 border border-purple-500/40 shadow-xl space-y-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-4 border-b border-slate-700/80 gap-4">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-red-500/20 text-red-300 border border-red-500/40">
                  CRITICAL DEFECT CLUSTER DETECTED
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40">
                  Batch: HB-09
                </span>
              </div>
              <h2 className="text-xl font-black text-white">
                {batchHB09.product_name} ({batchHB09.supplier_name})
              </h2>
              <p className="text-xs text-slate-300 font-mono">
                SKU: {batchHB09.sku} | Total Units Received: {batchHB09.total_returns} units
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <div className="bg-slate-800/90 p-3 rounded-xl border border-slate-700 text-right">
                <span className="text-[10px] text-slate-400 font-semibold uppercase">Observed Return Rate</span>
                <div className="text-2xl font-black text-red-400">
                  {batchHB09.observed_return_rate}%
                </div>
                <span className="text-[10px] text-slate-500">vs 5.0% baseline (5.6x spike)</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Defect Analysis */}
            <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700 space-y-3">
              <h3 className="text-xs font-bold text-teal-400 uppercase tracking-wider flex items-center space-x-1.5">
                <span>Concentrated Defect Distribution</span>
              </h3>

              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={defectChartData} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                    <XAxis type="number" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                    <YAxis dataKey="reason" type="category" width={110} tick={{ fontSize: 9, fill: '#cbd5e1' }} />
                    <Tooltip
                      formatter={(val: any) => [`${val} units`, 'Count']}
                      contentStyle={{ backgroundColor: '#0f172a', color: '#fff', borderRadius: '8px', fontSize: '11px' }}
                    />
                    <Bar dataKey="count" fill="#ec4899" radius={[0, 4, 4, 0]}>
                      {defectChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index === 0 ? '#ef4444' : '#64748b'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="p-2.5 bg-slate-900 rounded-lg text-[11px] text-slate-300">
                Dominant Fault: <span className="text-red-400 font-bold">{batchHB09.dominant_defect}</span> accounts for <span className="text-white font-extrabold">{batchHB09.dominant_defect_percentage}%</span> of all returns.
              </div>
            </div>

            {/* Spike vs Historical Baseline */}
            <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700 space-y-3">
              <h3 className="text-xs font-bold text-purple-400 uppercase tracking-wider">
                Historical Return Rate Spike
              </h3>

              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                    <XAxis dataKey="period" tick={{ fontSize: 9, fill: '#94a3b8' }} />
                    <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', color: '#fff', borderRadius: '8px', fontSize: '11px' }} />
                    <Line type="monotone" dataKey="baseline" stroke="#64748b" strokeDasharray="3 3" name="Expected Baseline %" />
                    <Line type="monotone" dataKey="observed" stroke="#ef4444" strokeWidth={2.5} name="Observed Return %" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="p-2.5 bg-slate-900 rounded-lg text-[11px] text-slate-300">
                Spike began upon arrival of batch HB-09. Standard statistical threshold is 15.0%.
              </div>
            </div>

            {/* Vendor Window & Action */}
            <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700 flex flex-col justify-between space-y-4">
              <div className="space-y-3">
                <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                  Vendor Terms & Warranty Window
                </h3>

                <div className="space-y-2 text-xs text-slate-300">
                  <div className="flex justify-between p-2 bg-slate-900 rounded">
                    <span>Vendor Return Window:</span>
                    <span className="font-bold text-white">{batchHB09.vendor_window_days} days</span>
                  </div>
                  <div className="flex justify-between p-2 bg-slate-900 rounded">
                    <span>Days Remaining:</span>
                    <span className="font-bold text-amber-400">{batchHB09.days_remaining_in_window} days</span>
                  </div>
                  <div className="flex justify-between p-2 bg-slate-900 rounded">
                    <span>Eligible Units for Credit:</span>
                    <span className="font-bold text-teal-400">{batchHB09.eligible_rtv_quantity} of {batchHB09.total_returns}</span>
                  </div>
                  <div className="flex justify-between p-2 bg-slate-900 rounded">
                    <span>Expected Vendor Credit:</span>
                    <span className="font-bold text-teal-400">₹{(batchHB09.eligible_rtv_quantity * 1500).toLocaleString('en-IN')}</span>
                  </div>
                </div>
              </div>

              <div className="p-3 bg-red-900/30 border border-red-700/50 rounded-xl space-y-1 text-xs">
                <span className="font-bold text-red-300">Quality Recommendation:</span>
                <p className="text-[11px] text-slate-300 leading-snug">
                  {batchHB09.recommendation}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Supplier Alerts Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Active Supplier Quality Alerts
            </h3>
            <p className="text-xs text-slate-500">
              System flags suppliers only when backed by statistical defect clustering or repeated RMA spikes.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                <th className="py-3 px-4">Supplier</th>
                <th className="py-3 px-4">Batch / SKU</th>
                <th className="py-3 px-4">Alert Type</th>
                <th className="py-3 px-4">Observed vs Baseline</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Evidence Summary</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {alerts.map((al) => (
                <tr key={al.id} className="hover:bg-slate-50/80 transition">
                  <td className="py-3 px-4 font-bold text-slate-900">{al.supplier_name}</td>
                  <td className="py-3 px-4 font-mono text-slate-600">
                    {al.supplier_batch || 'All Batches'} ({al.sku || 'Catalog'})
                  </td>
                  <td className="py-3 px-4 font-semibold text-slate-700">{al.alert_type}</td>
                  <td className="py-3 px-4">
                    <span className="text-red-600 font-bold">{al.observed_return_rate}%</span>
                    <span className="text-slate-400 ml-1">/ {al.baseline_return_rate}%</span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      al.severity === 'Critical' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                    }`}>
                      {al.severity}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-600 text-[11px] max-w-xs">
                    {al.evidence?.dominant_reason ? (
                      <span>{al.evidence.dominant_reason} ({al.evidence.dominant_percentage}%)</span>
                    ) : (
                      <span>Defect concentration observed</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                      {al.status}
                    </span>
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
