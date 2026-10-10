import React, { useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  PackageSearch,
  Scale,
  ShieldAlert,
  CheckCircle2,
  Sparkles,
  Sliders,
  RefreshCw,
  Cpu,
  ArrowRight
} from 'lucide-react';
import { api } from '../services/api';

export const Layout: React.FC = () => {
  const navigate = useNavigate();
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [aiConfigured, setAiConfigured] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const summary = await api.getDashboardSummary();
      setPendingCount(summary.pending_approvals_count);
      const health = await api.getHealth();
      setAiConfigured(health.ai_configured);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleLoadDemo = async () => {
    setIsResetting(true);
    try {
      await api.seedDemoScenario();
      setToastMessage("Demo Scenario Loaded: 40 Grade-B headphones & Batch HB-09 active.");
      await fetchStatus();
      navigate('/');
    } catch (err: any) {
      setToastMessage(`Error: ${err.message}`);
    } finally {
      setIsResetting(false);
      setTimeout(() => setToastMessage(null), 4000);
    }
  };

  const navItems = [
    { to: '/', label: 'Executive Dashboard', icon: LayoutDashboard },
    { to: '/returns', label: 'Returns Workbench', icon: PackageSearch },
    { to: '/recovery', label: 'Recovery Decision Center', icon: Scale },
    { to: '/suppliers', label: 'Supplier Intelligence', icon: ShieldAlert },
    { 
      to: '/approvals', 
      label: 'Action Approval Center', 
      icon: CheckCircle2,
      badge: pendingCount > 0 ? pendingCount : null 
    },
    { to: '/copilot', label: 'Chat with AI', icon: Sparkles, highlight: true },
    { to: '/settings', label: 'Data & Settings', icon: Sliders },
  ];

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-slate-200 flex flex-col justify-between shrink-0 shadow-xl border-r border-slate-800">
        <div>
          {/* Logo / Header */}
          <div className="p-5 border-b border-slate-800/80">
            <div className="flex items-center space-x-2.5">
              <div className="w-9 h-9 rounded-lg bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-400 font-bold text-lg shadow-inner">
                ↩
              </div>
              <div>
                <h1 className="font-extrabold text-white tracking-wide text-base leading-tight">WHAT CAME BACK</h1>
                <p className="text-[11px] text-teal-400 font-medium">Gadgetbay Recovery Centre</p>
              </div>
            </div>
            <div className="mt-3 px-2 py-1 bg-slate-800/80 rounded text-[10px] text-slate-400 flex items-center justify-between">
              <span>CYPHER 4.0 — Challenge 10</span>
              <span className="text-teal-400 font-semibold">v1.0</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-teal-600 text-white shadow-md'
                        : item.highlight
                        ? 'text-teal-300 hover:bg-slate-800/80 hover:text-white'
                        : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
                    }`
                  }
                >
                  <div className="flex items-center space-x-3">
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{item.label}</span>
                  </div>
                  {item.badge !== null && item.badge !== undefined && (
                    <span className="bg-amber-500 text-slate-950 text-[10px] font-bold px-1.5 py-0.5 rounded-full shadow-sm">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950/40 space-y-3">
          {/* Quick Demo Seed Button */}
          <button
            onClick={handleLoadDemo}
            disabled={isResetting}
            className="w-full flex items-center justify-center space-x-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-teal-300 hover:text-teal-200 border border-slate-700 rounded-lg text-xs font-semibold transition shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
            <span>{isResetting ? 'Loading...' : 'Load Demo Scenario'}</span>
          </button>

          {/* AI Engine Status Indicator */}
          <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800 text-[11px] space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center space-x-1.5">
                <Cpu className="w-3.5 h-3.5 text-teal-400" />
                <span>AI Reasoning:</span>
              </span>
              <span className={`font-semibold ${aiConfigured ? 'text-teal-400' : 'text-emerald-400'}`}>
                {aiConfigured ? 'OpenAI (gpt-4o)' : 'Deterministic Core'}
              </span>
            </div>
            <p className="text-[10px] text-slate-500 leading-tight">
              {aiConfigured ? 'Hybrid tools + LLM reasoning' : 'Deterministic fallback active & ready'}
            </p>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0 shadow-sm">
          <div className="flex items-center space-x-4">
            <h2 className="text-base font-bold text-slate-800">
              E-commerce Returns Recovery Intelligence
            </h2>
            <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-teal-50 text-teal-700 border border-teal-200">
              Deterministic Financial Calculations Guaranteed
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/copilot')}
              className="flex items-center space-x-2 text-xs font-semibold text-teal-700 hover:text-teal-800 bg-teal-50 hover:bg-teal-100 border border-teal-200 px-3 py-1.5 rounded-lg transition"
            >
              <Sparkles className="w-3.5 h-3.5 text-teal-600" />
              <span>Chat with AI</span>
              <ArrowRight className="w-3 h-3 text-teal-500" />
            </button>
          </div>
        </header>

        {/* Page Content Body */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 bg-slate-900 text-white text-xs px-4 py-3 rounded-lg shadow-xl border border-teal-500 flex items-center space-x-2 animate-bounce">
          <CheckCircle2 className="w-4 h-4 text-teal-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
};
