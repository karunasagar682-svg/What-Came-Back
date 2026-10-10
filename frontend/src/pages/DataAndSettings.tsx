import React, { useState, useEffect, useRef } from 'react';
import {
  Upload,
  Download,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Cpu,
  Database,
  FileText,
  Save,
  HelpCircle
} from 'lucide-react';
import { api } from '../services/api';
import { SystemSettings } from '../types';

export const DataAndSettings: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [templates, setTemplates] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [savingSettings, setSavingSettings] = useState<boolean>(false);
  const [seedingDemo, setSeedingDemo] = useState<boolean>(false);

  // CSV Import State
  const [selectedEntity, setSelectedEntity] = useState<string>('returns');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<any | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [toast, setToast] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [sets, tmpls] = await Promise.all([api.getSettings(), api.getTemplates()]);
      setSettings(sets);
      setTemplates(tmpls);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    setSavingSettings(true);
    try {
      await api.updateSettings(settings);
      setToast('System thresholds updated successfully.');
    } catch (err: any) {
      alert(`Error saving settings: ${err.message}`);
    } finally {
      setSavingSettings(false);
      setTimeout(() => setToast(null), 3000);
    }
  };

  const handleSeedDemo = async () => {
    // Demo seeding may reset existing database data. Require explicit confirmation.
    const confirmed = window.confirm(
      'Load the demo scenario? This may replace/reset existing project data. Export or back up important data before continuing.'
    );
    if (!confirmed) return;

    setSeedingDemo(true);
    try {
      await api.seedDemoScenario();
      setToast('Demo scenario reset and re-seeded successfully (Batch HB-09 loaded).');
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setSeedingDemo(false);
      setTimeout(() => setToast(null), 4000);
    }
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setUploadResult(null);
    try {
      const res = await api.uploadCsv(selectedEntity, selectedFile);
      setUploadResult(res);
      setToast(`Import complete: ${res.successful_rows} succeeded, ${res.failed_rows} failed.`);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setUploading(false);
      setTimeout(() => setToast(null), 4000);
    }
  };

  const downloadTemplate = (entity: string) => {
    const content = templates[entity] || '';
    const blob = new Blob([content], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sample_${entity}_template.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
  };

  if (loading || !settings) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-3 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-semibold text-slate-500">Loading system settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Data & System Settings</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage data ingestion, sample CSV templates, business thresholds, and AI provider integrations.
          </p>
        </div>

        {/* Load Demo Button */}
        <button
          onClick={handleSeedDemo}
          disabled={seedingDemo}
          className="flex items-center space-x-2 px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold transition shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${seedingDemo ? 'animate-spin' : ''}`} />
          <span>{seedingDemo ? 'Seeding...' : 'Load Demo Scenario'}</span>
        </button>
      </div>

      {toast && (
        <div className="p-4 bg-teal-50 border border-teal-300 text-teal-800 rounded-xl text-xs font-bold flex items-center space-x-2 animate-pulse">
          <CheckCircle2 className="w-4 h-4 text-teal-600" />
          <span>{toast}</span>
        </div>
      )}

      {/* CSV Ingestion Section */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <Upload className="w-5 h-5 text-teal-600" />
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                CSV Dataset Ingestion & Validation
              </h2>
              <p className="text-xs text-slate-500">
                Upload historical data. Invalid rows are identified and reported with exact reasons.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => downloadTemplate(selectedEntity)}
              className="text-xs font-semibold text-slate-600 hover:text-teal-700 bg-slate-50 hover:bg-teal-50 border border-slate-200 px-3 py-1.5 rounded-lg transition flex items-center space-x-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download {selectedEntity} Template</span>
            </button>
          </div>
        </div>

        <form onSubmit={handleFileUpload} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Entity Dataset:</label>
              <select
                value={selectedEntity}
                onChange={(e) => setSelectedEntity(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white text-slate-800 focus:ring-2 focus:ring-teal-500"
              >
                <option value="returns">Returns</option>
                <option value="products">Products</option>
                <option value="inventory">Inventory</option>
                <option value="vendor_terms">Vendor Terms</option>
                <option value="refurbishment">Refurbishment Rules</option>
                <option value="liquidation">Liquidation Rules</option>
                <option value="sales">Sales History</option>
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-slate-700 mb-1">CSV File:</label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-teal-50 hover:file:text-teal-700"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!selectedFile || uploading}
              className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition flex items-center space-x-2 disabled:opacity-40"
            >
              <span>{uploading ? 'Validating & Importing...' : 'Validate & Import CSV'}</span>
            </button>
          </div>
        </form>

        {/* Upload Results Summary */}
        {uploadResult && (
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
            <div className="flex items-center justify-between font-bold">
              <span className="text-slate-800">Import Summary: {uploadResult.entity}</span>
              <span className="text-teal-700">
                {uploadResult.successful_rows} successful / {uploadResult.total_rows} total rows
              </span>
            </div>

            {uploadResult.failed_rows > 0 && (
              <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 space-y-1">
                <span className="font-bold flex items-center space-x-1">
                  <AlertTriangle className="w-3.5 h-3.5 text-red-600" />
                  <span>Validation Errors ({uploadResult.failed_rows} rows rejected):</span>
                </span>
                <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                  {uploadResult.errors.map((err: string, i: number) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Configurable Business Thresholds */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
        <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-100">
          <Sliders className="w-5 h-5 text-teal-600" />
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Operational Detection Thresholds
            </h2>
            <p className="text-xs text-slate-500">
              Tune parameters for aging detection, expiring warranty windows, and supplier defect alerts.
            </p>
          </div>
        </div>

        <form onSubmit={handleSaveSettings} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-800">
                Returns Aging Threshold (Days):
              </label>
              <input
                type="number"
                min="1"
                value={settings.aging_threshold_days}
                onChange={(e) =>
                  setSettings({ ...settings, aging_threshold_days: Number(e.target.value) })
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-teal-500"
              />
              <span className="text-[10px] text-slate-400">
                Returns unrouted beyond this threshold are flagged as aging.
              </span>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-800">
                Vendor Window Expiry Warning (Days):
              </label>
              <input
                type="number"
                min="1"
                value={settings.expiring_window_threshold_days}
                onChange={(e) =>
                  setSettings({ ...settings, expiring_window_threshold_days: Number(e.target.value) })
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-teal-500"
              />
              <span className="text-[10px] text-slate-400">
                Alerts manager when vendor deadline is approaching.
              </span>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-800">
                High-Value Return Cutoff (₹):
              </label>
              <input
                type="number"
                min="100"
                value={settings.high_value_threshold}
                onChange={(e) =>
                  setSettings({ ...settings, high_value_threshold: Number(e.target.value) })
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-teal-500"
              />
              <span className="text-[10px] text-slate-400">
                Threshold for prioritizing aging items by recoverable capital.
              </span>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-800">
                Supplier Defect Anomaly Threshold (%):
              </label>
              <input
                type="number"
                min="5"
                max="100"
                value={settings.defect_anomaly_percentage}
                onChange={(e) =>
                  setSettings({ ...settings, defect_anomaly_percentage: Number(e.target.value) })
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-teal-500"
              />
              <span className="text-[10px] text-slate-400">
                Return rate exceeding this triggers supplier quality alert.
              </span>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-800">
                Excess Inventory Coverage Threshold (Days):
              </label>
              <input
                type="number"
                min="15"
                value={settings.excess_inventory_days}
                onChange={(e) =>
                  setSettings({ ...settings, excess_inventory_days: Number(e.target.value) })
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-teal-500"
              />
              <span className="text-[10px] text-slate-400">
                Days of existing stock that triggers demand cannibalization warning for refurbishment.
              </span>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={savingSettings}
              className="px-5 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold transition flex items-center space-x-2 shadow-sm disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{savingSettings ? 'Saving...' : 'Save Configuration'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* AI Integration Status */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-3">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <Cpu className="w-5 h-5 text-purple-600" />
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                AI Reasoning Integration Status
              </h2>
              <p className="text-xs text-slate-500">
                Configured model and deterministic fallback status.
              </p>
            </div>
          </div>
          <span
            className={`px-3 py-1 rounded-full text-xs font-bold ${
              settings.openai_configured
                ? 'bg-teal-100 text-teal-800'
                : 'bg-emerald-100 text-emerald-800'
            }`}
          >
            {settings.openai_configured ? 'OpenAI API Connected' : 'Deterministic Core Active'}
          </span>
        </div>

        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
          <div className="flex justify-between">
            <span className="text-slate-500">Model Name:</span>
            <span className="font-mono font-bold text-slate-800">{settings.openai_model}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Execution Mode:</span>
            <span className="font-semibold text-slate-800">
              {settings.openai_configured
                ? 'OpenAI Tool Calling (with deterministic financial calculation)'
                : 'Deterministic Reasoning Engine (Zero external dependencies)'}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 pt-1 border-t border-slate-200">
            Note: All financial calculations are executed by the deterministic Python backend engine regardless of model choice.
          </p>
        </div>
      </div>
    </div>
  );
};
