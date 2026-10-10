# WHAT CAME BACK
### AI-Powered Returns Recovery and Supplier Intelligence Platform
**Business**: Gadgetbay — E-commerce Returns Recovery Centre  
**Hackathon**: CYPHER 4.0 — Challenge 10

---

## 1. Overview
**What Came Back** is an enterprise-grade AI returns recovery platform designed to answer the core business question:
> *"What should we do with today's returns, and what are they telling us about our products and suppliers?"*

Instead of treating returns as an unorganized cost sink or sending items to hasty liquidation, **What Came Back** executes a **deterministic financial calculation engine** across 5 recovery channels (**Restock**, **Refurbish**, **Vendor Return (RTV)**, **Liquidation**, and **Scrap**), detects 5 mandatory operational problems, evaluates demand risk against warehouse stock, enables split-batch recovery planning, and drives human-approved simulated actions through an interactive **Action Approval Center** and **Recovery Copilot**.

---

## 2. Core Implemented Features

### 1. Deterministic Financial Recovery Engine
- **Zero Financial Hallucinations**: All monetary proceeds, route processing costs, disposal fees, and net recovery values are calculated in deterministic Python code.
- **5 Routes Evaluated**:
  - **Restock**: Grade A pristine items (full MSRP, ₹50 inspection fee, 1-7 days cash).
  - **Refurbish**: Grade B/C items (75% resale price, ₹250 repair cost, factoring 60-day stock coverage).
  - **Vendor Return (RTV)**: 60% MSRP vendor credit, 30-day window deadline tracking, zero repair risk.
  - **Liquidation**: 35% of product cost, 3-day rapid settlement.
  - **Scrap**: Certified disposal fee (₹20), zero proceeds, strictly last resort.

### 2. 5 Mandatory Problem Detectors
1. **High-Value Returns Waiting Too Long**: Flags items waiting > 7 days by urgency and decaying capital.
2. **Items Headed for Liquidation That Could Earn More**: Prevents value destruction by highlighting incremental gains from RTV or refurbishment.
3. **Vendor Return Windows About to Close**: Detects batches with $\le 7$ days remaining before RTV credit is forfeited.
4. **Unusually High Returns by SKU or Supplier Batch**: Detects concentrated defect clusters (e.g. Batch HB-09 with 70% audio failures vs 5% baseline) and issues supplier quality alerts.
5. **Refurbishing What Nobody Wants / Demand Mismatch**: Warns against sinking repair capital into categories where new stock already exceeds 45–60 days of demand.

### 3. Split-Batch Allocation Planner
- Allows managers to split a single batch across multiple routes (e.g., returning 24 units to the vendor for guaranteed credit while refurbishing the remaining 16 units).
- Enforces strict quantity conservation: $\sum \text{allocated} \le \text{batch\_quantity}$.
- Enforces route eligibility per slice (e.g., cannot exceed vendor RTV quota).
- Real-time delta comparison against full liquidation (+₹42,400 gain).

### 4. Gadgetbay Recovery Copilot
- Conversational business assistant powered by the OpenAI Python SDK with function calling tools (`get_daily_priorities`, `analyze_supplier_batch`, `compare_recovery_routes`, `create_proposed_action`).
- **Resilient Deterministic Fallback**: Operates seamlessly even when no OpenAI API key is configured or offline.
- Factual citations: Every answer provides issue, evidence, financial impact, next step, and assumptions.

### 5. Action Approval Center & Activity Log
- Full human-in-the-loop governance: Proposed actions require human approval.
- Duplicate approval prevention and rejection handling.
- Audit trail logging actor, action, timestamp, and simulated status.

### 6. CSV Data Ingestion & Settings
- Upload CSV datasets for Returns, Products, Suppliers, and Inventory.
- Row-by-row validation with error reporting (never silently discards invalid rows).
- Sample CSV template download links.
- Configurable thresholds for aging, windows, and defect spikes.
- 1-click **Load Demo Scenario** button.

---

## 3. Technology Stack
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, React Router v7, Recharts, Lucide React.
- **Backend**: Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic.
- **Database**: SQLite (default local zero-setup) and PostgreSQL compatible.
- **AI**: OpenAI Python SDK (`gpt-4o`) + Deterministic Fallback Reasoning Engine.
- **Testing**: Pytest, Asyncio test runner (20 tests passed).

---

## 4. Folder Structure
```text
what-came-back/
├── backend/
│   ├── app/
│   │   ├── agent/             # Copilot agent, tool calling, and fallback engine
│   │   ├── api/               # REST API endpoints (dashboard, returns, recovery, etc.)
│   │   ├── core/              # Config, database setup, environment settings
│   │   ├── engine/            # Deterministic calculation engine & split planner
│   │   ├── intelligence/      # 5 Problem detectors & batch intelligence
│   │   ├── models/            # SQLAlchemy database models
│   │   ├── schemas/           # Pydantic validation schemas
│   │   ├── seed/              # Seed generator (Batch HB-09 reference scenario)
│   │   └── main.py            # FastAPI application entrypoint
│   ├── tests/                 # 20 pytest test cases
│   ├── requirements.txt       # Python dependencies
│   └── .env.example           # Environment template
├── frontend/
│   ├── src/
│   │   ├── components/        # Layout, Sidebar, Navbar, Toast
│   │   ├── pages/             # 7 Application pages
│   │   │   ├── ExecutiveDashboard.tsx
│   │   │   ├── ReturnsWorkbench.tsx
│   │   │   ├── RecoveryDecisionCenter.tsx
│   │   │   ├── SupplierIntelligence.tsx
│   │   │   ├── ActionApprovalCenter.tsx
│   │   │   ├── CopilotChat.tsx
│   │   │   └── DataAndSettings.tsx
│   │   ├── services/          # Typed API client
│   │   └── types/             # TypeScript data interfaces
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── start.bat                  # 1-Click Windows Batch launcher
├── start.ps1                  # 1-Click PowerShell launcher
└── README.md
```

---

## 5. Quick Start Instructions (Windows)

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### Method A: 1-Click Launch (Recommended)
Simply double-click:
```cmd
start.bat
```
*(Or run `.\start.ps1` in PowerShell)*

### Method B: Manual Launch
1. **Start Backend**:
   ```powershell
   cd backend
   pip install -r requirements.txt
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. **Start Frontend**:
   ```powershell
   cd frontend
   npm install
   npm run dev -- --host 127.0.0.1 --port 5173
   ```

### Local URLs
- **Web Application**: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- **FastAPI Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **API Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## 6. Running Automated Tests
Run pytest in the backend directory:
```powershell
cd backend
python -m pytest -v
```

### Test Suite Results:
```text
tests/test_actions.py::test_action_approval_lifecycle PASSED             [  5%]
tests/test_actions.py::test_action_rejection PASSED                      [ 10%]
tests/test_calculator.py::test_restock_eligibility_grade_a PASSED        [ 15%]
tests/test_calculator.py::test_restock_ineligibility_grade_b PASSED      [ 20%]
tests/test_calculator.py::test_refurbish_calculation PASSED              [ 25%]
tests/test_calculator.py::test_liquidation_calculation PASSED            [ 30%]
tests/test_calculator.py::test_vendor_return_window_expired PASSED       [ 35%]
tests/test_copilot_fallback.py::test_copilot_fallback_daily_priorities PASSED [ 40%]
tests/test_copilot_fallback.py::test_copilot_fallback_batch_hb09 PASSED  [ 45%]
tests/test_copilot_fallback.py::test_copilot_fallback_generate_split_action PASSED [ 50%]
tests/test_csv_import.py::test_csv_import_returns_valid_and_invalid[asyncio] PASSED [ 55%]
tests/test_csv_import.py::test_csv_import_missing_columns[asyncio] PASSED [ 60%]
tests/test_detectors.py::test_problem_1_detect_aging_returns PASSED      [ 65%]
tests/test_detectors.py::test_problem_2_detect_liquidation_loss PASSED   [ 70%]
tests/test_detectors.py::test_problem_3_detect_expiring_vendor_windows PASSED [ 75%]
tests/test_detectors.py::test_problem_4_detect_batch_hb09_anomaly PASSED [ 80%]
tests/test_detectors.py::test_batch_hb09_intelligence_detail PASSED      [ 85%]
tests/test_detectors.py::test_problem_5_detect_refurb_demand_mismatch PASSED [ 90%]
tests/test_reference_scenario.py::test_reference_40_headphone_scenario PASSED [ 95%]
tests/test_reference_scenario.py::test_split_plan_over_allocation_rejected PASSED [100%]

======================= 20 passed in 2.65s ========================
```

---

## 7. Step-by-Step Judge Demonstration Flow

Follow these 10 steps to demonstrate the complete system to evaluators:

1. **Step 1: Open Executive Dashboard**
   - Navigate to [http://127.0.0.1:5173/](http://127.0.0.1:5173/).
   - Inspect the **"WHAT NEEDS YOUR ATTENTION TODAY?"** priority cards showing high-impact aging, liquidation value destruction, and expiring vendor deadlines.
2. **Step 2: Ask the Recovery Copilot**
   - Click **"Recovery Copilot"** on the sidebar or click **"Launch Copilot Briefing"**.
   - Click the prompt pill: *"What needs my attention today?"*
   - Verify that the Copilot runs backend tools deterministically and returns facts without hallucinations.
3. **Step 3: Investigate Batch HB-09**
   - Click the prompt pill: *"Why is batch HB-09 flagged?"* (or navigate to **Supplier Intelligence**).
   - See the 70% defect cluster ("Audio Driver Hiss / Bluetooth Drop") for SoundWave Dynamics headphones, and observe that 24 units are eligible for RTV credit.
4. **Step 4: Review Route Economics in Recovery Decision Center**
   - Navigate to **"Recovery Decision Center"**.
   - Observe the side-by-side comparison of Restock (Ineligible for Grade B), Refurbish (₹1,625 net), Vendor Return (₹1,500 net), and Liquidation (₹490 net).
5. **Step 5: Inspect Demand Saturation Risk**
   - Observe the demand warning: warehouse has 60 days of new stock coverage (`WH-1000XM-B`), so refurbished units risk shelf stagnation.
6. **Step 6: Execute Split-Batch Allocation**
   - Click **"Pre-fill Reference Plan (24 RTV + 16 Refurb)"**.
   - Notice immediate live recalculation:
     - 24 units $\times$ ₹1,500 vendor credit = ₹36,000 (guaranteed, zero demand risk).
     - 16 units $\times$ ₹1,625 refurb net = ₹26,000.
     - Total Net Recovery = **₹62,000**.
     - Value created over full liquidation ($40 \times 490 = 19,600$) is **+₹42,400 (+216%)**.
7. **Step 7: Submit Proposed Action**
   - Click **"Submit Proposed Action for Human Approval"**.
8. **Step 8: Approve Action in Action Approval Center**
   - Navigate to **"Action Approval Center"**.
   - Review Action `#1` with financial impact, risk notes, and justification.
   - Click **"Approve (Simulated)"**.
   - Notice the status updates to `Approved (Simulated)`, reviewer name is recorded, and repeat approvals are prevented.
9. **Step 9: Review Activity Log Audit Trail**
   - Scroll down to the **Activity Log & Audit Trail** to view the simulated action event with actor, timestamp, and payload.
10. **Step 10: Test CSV Data & Settings**
    - Navigate to **"Data & Settings"**.
    - Download sample CSV templates, adjust aging threshold sliders, and verify that the system runs 100% offline without external ERP dependencies.
