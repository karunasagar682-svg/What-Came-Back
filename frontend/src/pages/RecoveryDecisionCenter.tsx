import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Scale,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Sliders,
  DollarSign,
  Clock,
  ArrowRight,
  HelpCircle,
  Package
} from 'lucide-react';
import { api } from '../services/api';
import { ReturnItem, RouteComparisonResult, SplitBatchResponse } from '../types';

export const RecoveryDecisionCenter: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [returnsList, setReturnsList] = useState<ReturnItem[]>([]);
  const [selectedReturnId, setSelectedReturnId] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<RouteComparisonResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Split Batch State
  const [allocations, setAllocations] = useState<{ [route: string]: number }>({
    'Vendor Return': 0,
    'Refurbish': 0,
    'Restock': 0,
    'Liquidation': 0,
    'Scrap': 0,
  });
  const [splitSimulation, setSplitSimulation] = useState<SplitBatchResponse | null>(null);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadReturns();
  }, []);

  const loadReturns = async () => {
    try {
      setLoading(true);
      const items = await api.getReturns();
      setReturnsList(items);

      const paramId = searchParams.get('return_id');
      if (paramId) {
        setSelectedReturnId(Number(paramId));
      } else if (items.length > 0) {
        // Default to reference scenario batch HB-09 item if present
        const refItem = items.find((i) => i.supplier_batch === 'HB-09') || items[0];
        setSelectedReturnId(refItem.id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedReturnId) {
      loadAnalysis(selectedReturnId);
    }
  }, [selectedReturnId]);

  const loadAnalysis = async (id: number) => {
    try {
      setLoading(true);
      const res = await api.analyzeRecovery(id);
      setAnalysis(res);

      // Pre-fill allocation defaults
      if (res.is_split_recommended && res.split_recommendation_details) {
        const details = res.split_recommendation_details;
        setAllocations({
          'Vendor Return': details.vendor_quantity,
          'Refurbish': details.remaining_route === 'Refurbish' ? details.remaining_quantity : 0,
          'Restock': 0,
          'Liquidation': details.remaining_route === 'Liquidation' ? details.remaining_quantity : 0,
          'Scrap': 0,
        });
      } else {
        setAllocations({
          'Vendor Return': res.recommended_route === 'Vendor Return' ? res.quantity : 0,
          'Refurbish': res.recommended_route === 'Refurbish' ? res.quantity : 0,
          'Restock': res.recommended_route === 'Restock' ? res.quantity : 0,
          'Liquidation': res.recommended_route === 'Liquidation' ? res.quantity : 0,
          'Scrap': res.recommended_route === 'Scrap' ? res.quantity : 0,
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Re-run split simulation when allocations change
  useEffect(() => {
    if (analysis && selectedReturnId) {
      runSplitSimulation();
    }
  }, [allocations, analysis]);

  const runSplitSimulation = async () => {
    if (!analysis) return;
    setSimulating(true);
    try {
      const allocList = Object.entries(allocations).map(([route, quantity]) => ({
        route,
        quantity,
      }));
      const sim = await api.simulateSplitPlan({
        return_id: analysis.return_id,
        supplier_batch: analysis.supplier_batch,
        total_quantity: analysis.quantity,
        allocations: allocList,
      });
      setSplitSimulation(sim);
    } catch (err) {
      console.error(err);
    } finally {
      setSimulating(false);
    }
  };

  const handleAllocationChange = (route: string, val: number) => {
    setAllocations((prev) => ({
      ...prev,
      [route]: Math.max(0, val),
    }));
  };

  const handleSetReferenceScenarioSplit = () => {
    if (!analysis) return;
    setAllocations({
      'Vendor Return': 24,
      'Refurbish': 16,
      'Restock': 0,
      'Liquidation': 0,
      'Scrap': 0,
    });
  };

  const handleCreateAction = async () => {
    if (!analysis || !splitSimulation || !splitSimulation.is_valid) return;
    try {
      const actionType =
        splitSimulation.route_breakdowns.length > 1
          ? 'SPLIT_BATCH_RECOVERY'
          : `${splitSimulation.route_breakdowns[0]?.route.toUpperCase().replace(/\s+/g, '_')}_RECOVERY`;

      const res = await api.createAction({
        action_type: actionType,
        related_return_ids: analysis.return_id ? [analysis.return_id] : [],
        proposed_quantity: splitSimulation.total_allocated,
        estimated_recovery: splitSimulation.total_net_recovery,
        explanation: splitSimulation.trade_off_explanation,
        evidence: {
          sku: analysis.sku,
          batch: analysis.supplier_batch,
          incremental_gain: splitSimulation.incremental_gain_over_liquidation,
        },
        risks_and_assumptions: {
          weighted_time_to_cash: splitSimulation.weighted_time_to_cash_days,
          baseline_liquidation: splitSimulation.all_liquidation_recovery,
        },
      });

      setActionSuccess(`Simulated Proposed Action #${res.id} created! Redirecting to Approval Center...`);
      setTimeout(() => {
        navigate('/approvals');
      }, 1500);
    } catch (err: any) {
      alert(`Error creating action: ${err.message}`);
    }
  };

  const totalAllocated = Object.values(allocations).reduce((a, b) => a + b, 0);

  if (loading && !analysis) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-3 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-semibold text-slate-500">Loading recovery decision matrix...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Bar / Batch Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="p-1.5 bg-teal-50 text-teal-700 rounded-lg border border-teal-200">
              <Scale className="w-4 h-4" />
            </span>
            <h1 className="text-xl font-black text-slate-900 tracking-tight">Recovery Decision Center</h1>
          </div>
          <p className="text-xs text-slate-500">
            Compare all 5 eligible routes, evaluate trade-offs, and simulate split-batch quantity allocations.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <label className="text-xs font-bold text-slate-700">Select Return/Batch:</label>
          <select
            value={selectedReturnId || ''}
            onChange={(e) => setSelectedReturnId(Number(e.target.value))}
            className="px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-800 bg-white focus:ring-2 focus:ring-teal-500"
          >
            {returnsList.map((ret) => (
              <option key={ret.id} value={ret.id}>
                #{ret.id} - {ret.product_name} ({ret.quantity}x, Batch: {ret.supplier_batch})
              </option>
            ))}
          </select>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-4 bg-emerald-50 border border-emerald-300 text-emerald-800 rounded-xl text-xs font-bold flex items-center space-x-2 animate-pulse">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {analysis && (
        <>
          {/* Header Summary of Selected Item */}
          <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-5 text-white shadow-md flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-500/20 text-teal-300 border border-teal-500/40">
                  {analysis.supplier_name}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40 font-mono">
                  Batch: {analysis.supplier_batch}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  Grade {analysis.grade}
                </span>
              </div>
              <h2 className="text-lg font-black text-white">{analysis.product_name}</h2>
              <p className="text-xs text-slate-300">
                Batch Size: <span className="font-bold text-teal-400">{analysis.quantity} units</span> | Retail Price: ₹{analysis.selling_price} | Cost Price: ₹{analysis.cost_price} | Age: {analysis.days_waiting} days
              </p>
            </div>

            <div className="bg-slate-800/90 p-4 rounded-xl border border-slate-700 space-y-1 md:text-right">
              <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Engine Recommendation</span>
              <div className="text-base font-extrabold text-teal-400">
                {analysis.recommended_route}
              </div>
              <p className="text-[11px] text-slate-300 max-w-sm">
                +₹{analysis.incremental_recovery_over_liquidation.toLocaleString('en-IN')} gain over full liquidation
              </p>
            </div>
          </div>

          {/* 5-Route Side-by-Side Comparison Cards */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center space-x-1.5">
              <span>All 5 Recovery Routes Evaluated</span>
              <span className="text-[10px] text-slate-400 font-normal">(Deterministic calculation)</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              {Object.entries(analysis.routes).map(([name, route]) => {
                const isRec = name === analysis.recommended_route || (analysis.recommended_route === 'Split-Batch' && ['Vendor Return', 'Refurbish'].includes(name));
                return (
                  <div
                    key={name}
                    className={`p-4 rounded-xl border flex flex-col justify-between transition ${
                      route.is_eligible
                        ? isRec
                          ? 'bg-teal-50/50 border-teal-500 shadow-sm'
                          : 'bg-white border-slate-200'
                        : 'bg-slate-50 border-slate-200 opacity-60'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900">{name}</span>
                        {route.is_eligible ? (
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${isRec ? 'bg-teal-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
                            {isRec ? 'Recommended' : 'Eligible'}
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-red-100 text-red-700">
                            Ineligible
                          </span>
                        )}
                      </div>

                      <div>
                        <div className="text-lg font-black text-slate-900">
                          {route.is_eligible ? `₹${route.net_recovery.toLocaleString('en-IN')}` : '₹0'}
                        </div>
                        <span className="text-[10px] text-slate-400 font-medium">
                          ₹{route.recovery_per_unit}/unit net
                        </span>
                      </div>

                      <div className="space-y-1 pt-2 border-t border-slate-100 text-[10px] text-slate-600">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Processing:</span>
                          <span className="font-semibold">₹{route.processing_costs}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Time-to-cash:</span>
                          <span className="font-semibold">{route.time_to_cash_days}d</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Demand fit:</span>
                          <span className="font-semibold text-slate-700 truncate max-w-[90px]" title={route.demand_fit}>
                            {route.demand_fit}
                          </span>
                        </div>
                      </div>
                    </div>

                    {route.ineligibility_reason && (
                      <div className="mt-2 text-[10px] text-red-600 bg-red-50 p-1.5 rounded">
                        {route.ineligibility_reason}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* INTERACTIVE SPLIT-BATCH PLANNER */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-slate-200 gap-3">
              <div>
                <span className="text-[10px] font-bold text-teal-600 uppercase tracking-wider">
                  Interactive Optimization Tool
                </span>
                <h3 className="text-base font-black text-slate-900">
                  Split-Batch Allocation Planner
                </h3>
                <p className="text-xs text-slate-500">
                  Adjust quantities across feasible routes. The engine recalculates recovery values, checks eligibility constraints, and guards against value destruction.
                </p>
              </div>

              {analysis.supplier_batch === 'HB-09' && (
                <button
                  onClick={handleSetReferenceScenarioSplit}
                  className="px-3 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-lg text-xs font-bold transition flex items-center space-x-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                  <span>Pre-fill Reference Plan (24 RTV + 16 Refurb)</span>
                </button>
              )}
            </div>

            {/* Sliders / Input Controls */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {['Vendor Return', 'Refurbish', 'Restock', 'Liquidation', 'Scrap'].map((route) => {
                const routeInfo = analysis.routes[route];
                const qty = allocations[route] || 0;
                return (
                  <div key={route} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-800">{route}</span>
                      <span className="text-[10px] font-mono text-slate-500">
                        ₹{routeInfo?.recovery_per_unit || 0}/u
                      </span>
                    </div>

                    <div className="flex items-center space-x-2">
                      <input
                        type="number"
                        min="0"
                        max={analysis.quantity}
                        value={qty}
                        onChange={(e) => handleAllocationChange(route, Number(e.target.value))}
                        className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs font-bold text-slate-900 bg-white focus:ring-2 focus:ring-teal-500"
                      />
                      <span className="text-[10px] text-slate-500">units</span>
                    </div>

                    <div className="text-[10px] text-slate-500 flex justify-between">
                      <span>Subtotal:</span>
                      <span className="font-bold text-slate-800">
                        ₹{(qty * (routeInfo?.recovery_per_unit || 0)).toLocaleString('en-IN')}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Allocation Meter & Validation */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-slate-700">
                  Total Allocated: <span className="font-bold text-slate-900">{totalAllocated}</span> of <span className="font-bold">{analysis.quantity}</span> units
                </span>
                <span className={`text-[11px] font-bold ${
                  totalAllocated > analysis.quantity ? 'text-red-600' :
                  totalAllocated === analysis.quantity ? 'text-emerald-600' : 'text-amber-600'
                }`}>
                  {totalAllocated > analysis.quantity ? 'OVER-ALLOCATED' :
                   totalAllocated === analysis.quantity ? '100% ALLOCATED' :
                   `${analysis.quantity - totalAllocated} UNALLOCATED`}
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden flex">
                <div
                  style={{ width: `${Math.min(100, (totalAllocated / analysis.quantity) * 100)}%` }}
                  className={`h-full transition-all ${
                    totalAllocated > analysis.quantity ? 'bg-red-500' :
                    totalAllocated === analysis.quantity ? 'bg-teal-500' : 'bg-amber-500'
                  }`}
                />
              </div>

              {/* Simulation Validation Errors */}
              {splitSimulation && !splitSimulation.is_valid && splitSimulation.validation_errors.length > 0 && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 space-y-1">
                  <div className="font-bold flex items-center space-x-1.5">
                    <AlertTriangle className="w-4 h-4 text-red-600" />
                    <span>Allocation Validation Issues:</span>
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                    {splitSimulation.validation_errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Financial Results of Proposed Plan */}
            {splitSimulation && splitSimulation.is_valid && (
              <div className="p-5 bg-teal-50/70 border border-teal-200 rounded-xl space-y-4">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">
                      Simulated Financial Outcome
                    </span>
                    <h4 className="text-lg font-black text-teal-900">
                      Total Net Recovery: ₹{splitSimulation.total_net_recovery.toLocaleString('en-IN')}
                    </h4>
                    <p className="text-xs text-teal-800">
                      Weighted time-to-cash: <span className="font-bold">{splitSimulation.weighted_time_to_cash_days} days</span>
                    </p>
                  </div>

                  <div className="bg-white p-3.5 rounded-lg border border-teal-200 text-right">
                    <span className="text-[10px] text-slate-500 uppercase font-semibold">Value Saved Over Full Liquidation</span>
                    <div className="text-xl font-black text-emerald-600">
                      +₹{splitSimulation.incremental_gain_over_liquidation.toLocaleString('en-IN')}
                    </div>
                    <span className="text-[10px] text-slate-400">
                      (Baseline 100% liquidation: ₹{splitSimulation.all_liquidation_recovery.toLocaleString('en-IN')})
                    </span>
                  </div>
                </div>

                <p className="text-xs text-slate-700 bg-white/80 p-3 rounded-lg border border-teal-100 leading-relaxed">
                  {splitSimulation.trade_off_explanation}
                </p>

                <div className="flex justify-end pt-2">
                  <button
                    onClick={handleCreateAction}
                    className="px-5 py-2.5 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold transition flex items-center space-x-2 shadow-sm"
                  >
                    <span>Submit Proposed Action for Human Approval</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
