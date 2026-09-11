# MedIntel: Medication Intelligence for Proactive Healthcare Operations

**MedIntel** is an agentic clinical medication intelligence platform designed for healthcare supply-chain operations. It converts multi-variable operational signals (inventory velocity, demand acceleration, supplier disruption holds, in-transit purchase orders, and shelf-life collisions) into proactive, explainable decision intelligence.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/DrpadmajaSS/medintel)

---

## 🌟 Key Capabilities

1. **Deterministic Risk Intelligence**: Multi-signal scoring evaluates inventory buffers, 7d/30d burn rates, vendor lead-time surges, and inbound PO protections across 525 facility-medication SKUs.
2. **Interactive What-If Scenario Workbench**: Non-destructively test hypotheses for demand spikes, vendor delivery delays, and lateral inventory transfers with real-time before/after impact analytics.
3. **Daily Intelligence Briefing**: Prioritizes issues into **ACT** (acute shortages), **WATCH** (emerging demand surges), **OPPORTUNITY** (inter-facility rebalancing & expiry salvage), and **LEARN** (clinical operational insights).
4. **Grounded Gemini Copilot ("Ask MedIntel")**: Conversational AI assistant with tool-use capabilities to investigate root causes, find surplus stock, and run simulations.
5. **Modern Healthcare Web Dashboard**: Polished enterprise interface with Chart.js time-series charts, 6 scenario showcase cards, and instant filtering.

---

## 📁 Repository Structure

```text
medintel/
├── .venv/                         # Python virtual environment
├── requirements.txt               # Dependencies (FastAPI, Uvicorn, Pandas, Google-GenAI, Pytest)
├── pytest.ini                     # Pytest configuration
├── data/
│   └── raw/                       # 8 validated synthetic datasets (zero PHI)
├── src/
│   ├── medintel_datagen/          # Synthetic simulation generator
│   ├── medintel_engine/           # Explainable Multi-Signal Risk Intelligence Engine
│   │   ├── config.py              # Scoring weights & thresholds
│   │   ├── data_loader.py         # In-memory CSV dataset loader
│   │   ├── stockout_predictor.py  # 60-day discrete forward trajectory simulator
│   │   ├── risk_calculator.py     # Continuous scoring & factor attribution
│   │   ├── recommendations.py     # Context-aware clinical action rules
│   │   ├── engine.py              # Master orchestrator
│   │   └── signals/               # Feature extractors (utilization, supply, pipeline, inventory, expiry)
│   └── medintel_api/              # Production FastAPI Backend & Web App
│       ├── main.py                # App entry point & static file server
│       ├── config.py              # API runtime configuration
│       ├── schemas/               # Pydantic request & response models
│       ├── services/              # In-memory cache, What-If simulator, Gemini Copilot
│       ├── routers/               # 12 modular REST routers
│       └── static/                # Modern Web Dashboard (HTML, CSS, JS, Chart.js)
├── tests/                         # 32 automated tests (100% pass rate)
├── docs/                          # API documentation, methodology, data dictionary
└── scripts/                       # Dataset generation & benchmark evaluators
```

---

## ⚡ Quick Start: Running MedIntel

### 1. Activate Environment & Install Dependencies
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Automated Test Suite (32 Unit & API Tests)
```bash
export PYTHONPATH=src
pytest tests/ -v
```

### 3. Launch the MedIntel Application
```bash
export PYTHONPATH=src
uvicorn medintel_api.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:
- **Interactive Web Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🎯 Demonstrating the 6 Benchmark Scenarios

From the MedIntel web dashboard, click on any scenario showcase card to demonstrate:

1. **Norepinephrine Bitartrate (`MED001` @ `LOC006`)**:
   - *Problem*: Surging ICU admissions (+17%) + supplier disruption -> 0.0 Days of Supply.
   - *Resolution*: What-If simulation demonstrates transferring 150 units from Central AMC resolves the shortage.
2. **Meropenem (`MED022` @ `LOC002`)**:
   - *Problem*: Emerging demand acceleration (+38.8% to +76% burn rate). Current 14.3 DOS will breach in ~8 days.
   - *Resolution*: Proactive safety baseline increase and early replenishment reorder.
3. **Dexmedetomidine (`MED008` @ `LOC005`)**:
   - *Problem*: Westside Community has 0.0 DOS while Central AMC holds 1,756 units (45.8 DOS).
   - *Resolution*: Lateral intra-network transfer of 150 units eliminates shortage at $0 procurement cost.
4. **Alteplase tPA (`MED039` @ `LOC007`)**:
   - *Problem*: $638,600 worth of specialty thrombolytic expiring in 35 days at low-volume ambulatory center.
   - *Resolution*: Prioritized FIFO transfer to high-volume comprehensive stroke center.
5. **Insulin Glargine (`MED057` @ `LOC003`)**:
   - *Problem*: Primary distributor `SUP008` lead time surged from 4 to 25 days due to packaging line failure.
   - *Resolution*: Reroute upcoming orders to certified alternate vendor `SUP005` (5-day lead time).
6. **Vancomycin HCl (`MED021` @ `LOC004`)**:
   - *Problem*: On-hand inventory is 0 vials.
   - *Resolution*: MedIntel cross-references verified carrier tracking for `PO-20242` (500 vials arriving in <24h), suppressing false-alarm spot orders.

---

## 🤖 Gemini Copilot Setup

MedIntel includes both live Google Gemini integration and an offline deterministic reasoning engine:
- **Live Gemini API**: Set `export GEMINI_API_KEY="your-gemini-api-key"` in your shell.
- **Offline Mode**: If no API key is provided, MedIntel seamlessly falls back to a deterministic tool-execution engine, ensuring all demo queries function reliably.
