import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ExecutiveDashboard } from './pages/ExecutiveDashboard';
import { ReturnsWorkbench } from './pages/ReturnsWorkbench';
import { RecoveryDecisionCenter } from './pages/RecoveryDecisionCenter';
import { SupplierIntelligence } from './pages/SupplierIntelligence';
import { ActionApprovalCenter } from './pages/ActionApprovalCenter';
import { CopilotChat } from './pages/CopilotChat';
import { DataAndSettings } from './pages/DataAndSettings';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ExecutiveDashboard />} />
          <Route path="returns" element={<ReturnsWorkbench />} />
          <Route path="recovery" element={<RecoveryDecisionCenter />} />
          <Route path="suppliers" element={<SupplierIntelligence />} />
          <Route path="approvals" element={<ActionApprovalCenter />} />
          <Route path="copilot" element={<CopilotChat />} />
          <Route path="settings" element={<DataAndSettings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
