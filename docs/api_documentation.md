# MedIntel: API Documentation & Developer Guide

MedIntel is an agentic clinical medication intelligence platform that converts multi-variable healthcare operational signals into proactive, explainable risk intelligence.

---

## 1. Overview & Base URLs

- **Local API Base URL**: `http://localhost:8000/api`
- **Root Endpoints**: Also available at `http://localhost:8000/`
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **Interactive ReDoc**: `http://localhost:8000/redoc`

---

## 2. API Endpoints Reference

### 🏥 System & Health
#### `GET /health`
Returns system status, active snapshot date, and monitored entity counts.
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "data_status": "loaded",
  "snapshot_date": "2026-08-31",
  "medications_count": 75,
  "locations_count": 7,
  "assessed_skus_count": 525
}
```

---

### 💊 Formulary & Facilities
#### `GET /medications`
Returns master medication records with optional filtering.
- **Query Parameters**:
  - `therapeutic_class`: e.g. `Vasopressor`, `Antibiotic`
  - `criticality`: `High`, `Medium`, `Low`
  - `search`: Generic name or ID search
  - `limit`, `offset`: Pagination controls

#### `GET /locations`
Returns healthcare facilities across the health network.
- **Query Parameters**:
  - `location_type`: e.g. `Academic Medical Center`, `Trauma Center`
  - `region`: e.g. `Central Metro`, `Northern Valley`

---

### 🚨 Risk Intelligence
#### `GET /risks`
Returns ranked medication risk assessments sorted descending by risk score.
- **Query Parameters**:
  - `risk_level`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
  - `location_id`: Filter by facility (e.g. `LOC006`)
  - `medication_id`: Filter by drug (e.g. `MED001`)
  - `min_risk_score`: Filter by minimum score (e.g. `70.0`)

#### `GET /risks/{medication_id}`
Returns deep-dive diagnostic intelligence for a drug across all facilities, including:
- Physical on-hand stock and Days of Supply
- 7-day and 30-day utilization velocity
- Inbound purchase orders with carrier arrival horizons
- Near-expiry batches
- Sister facility surplus inventory matrix
- Primary driving signals, contributing factors, mitigating factors, and recommended clinical/supply actions.

---

### 📦 Inventory & Utilization
#### `GET /inventory`
Returns real-time inventory valuations, reorder levels, and days of supply.
- **Query Parameters**: `location_id`, `medication_id`, `min_dos`, `max_dos`, `limit`, `offset`.

#### `GET /utilization/{medication_id}`
Returns 365-day historical dispensing curves formatted for charting.
- **Query Parameters**: `location_id`, `start_date`, `end_date`.

---

### 🚚 Supplier Intelligence
#### `GET /suppliers`
Returns distributor metrics, standard vs. current lead times, reliability ratings, and active disruption holds.
- **Query Parameters**: `medication_id`, `supplier_id`, `delayed_only`.

---

### ☀️ Daily Intelligence Brief
#### `GET /daily-intelligence`
Returns the daily 4-quadrant executive briefing:
- **`ACT`**: High-priority immediate interventions (e.g. Norepinephrine acute shortage).
- **`WATCH`**: Emerging demand surges and acceleration trends (e.g. Meropenem +76% burn rate).
- **`OPPORTUNITY`**: Inter-facility lateral transfer pairs & expiry salvage.
- **`LEARN`**: Clinical operational pattern insights.

---

### ⚡ Interactive What-If Simulator
#### `POST /what-if`
Performs **non-destructive** scenario simulations on in-memory clones.
- **Request Body**:
```json
{
  "medication_id": "MED022",
  "location_id": "LOC002",
  "demand_change_percent": 50.0,
  "supplier_delay_days": 5.0,
  "inventory_change_percent": -30.0,
  "inventory_transfer_units": 0.0
}
```
- **Response**:
```json
{
  "simulation_id": "SIM-7C91D4A2",
  "medication_id": "MED022",
  "location_id": "LOC002",
  "baseline": {
    "generic_name": "Meropenem",
    "days_of_supply": 14.3,
    "risk_score": 48.0,
    "risk_level": "MEDIUM",
    "days_to_stockout": 12.9
  },
  "scenario": {
    "projected_days_of_supply": 6.7,
    "projected_risk_score": 78.5,
    "projected_risk_level": "HIGH",
    "projected_days_to_stockout": 6.7
  },
  "impact": {
    "delta_days_of_supply": -7.6,
    "delta_risk_score": 30.5,
    "risk_level_transition": "MEDIUM → HIGH",
    "stockout_status_change": "Stockout Accelerated by 6.2 days",
    "explanation": "Demand change of +50.0% shifts burn rate from 44.0 to 66.0 units/day. Days of Supply changes by -7.6 days, moving risk score by +30.5 points (MEDIUM → HIGH)."
  }
}
```

---

### 🔄 Opportunities & Rebalancing
#### `GET /opportunities`
Returns all lateral rebalancing pairs (surplus vs. deficit) and near-expiry write-off salvage opportunities with estimated cost avoidance dollars.

---

### 📊 Executive Metrics & KPIs
#### `GET /metrics`
Returns systemwide executive KPIs: monitored counts, critical shortages, emerging surges, potential stockouts, expiry waste dollars, and risk breakdown.

---

### 🤖 Gemini Copilot ("Ask MedIntel")
#### `POST /chat`
Submits a natural-language query to the MedIntel Copilot.
- **Request Body**:
```json
{
  "prompt": "Why is Norepinephrine high risk today?"
}
```
- **Response**: Returns grounded Markdown response with citations, executed tool metadata (`tools_used`), and suggested follow-up questions.
