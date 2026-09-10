# MedIntel AI: Benchmark Scenario Reference Guide

This document details the 6 hidden test scenarios embedded within the MedIntel synthetic medication supply-chain platform. These scenarios benchmark MedIntel AI agents and risk detection algorithms against multi-variable operational challenges.

---

## Scenario Summary Matrix

| Scenario | Title | Medication | Target Facility | Root Cause Mechanism | Severity | Stockout Window |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Imminent Critical Stockout | Norepinephrine Bitartrate (`MED001`) | Valley Regional Trauma Center (`LOC006`) | ICU demand surge (+85%) coupled with active carrier delay (`EVT-1001`) stalling open PO | `CRITICAL` | < 48-72 hours |
| **2** | Emerging Demand Surge Risk | Meropenem (`MED022`) | North Suburban General Hospital (`LOC002`) | Accelerated patient admissions (+76% burn rate over 21 days); on-hand buffer safe today but will breach in ~8d | `MEDIUM` / `EMERGING` | 7-10 days |
| **3** | Inter-Facility Inventory Imbalance | Dexmedetomidine HCl (`MED008`) | Westside Community (`LOC005`) vs Central AMC (`LOC001`) | Severe depletion at LOC005 (< 2 days of supply) alongside major surplus at LOC001 (45+ days) | `HIGH` (at LOC005) | ~2 days |
| **4** | Near-Expiry Lot with Low Velocity | Alteplase (tPA) 100 mg (`MED039`) | South Ambulatory & Surgical Center (`LOC007`) | High-cost specialty drug (221 vials, $685k+) expiring in 35 days at low-volume day surgery center (~1,000+ days DOS) | `HIGH` (Financial / Waste) | Expiration Risk |
| **5** | Upstream Supplier Lead-Time Surge | Insulin Glargine (`MED057`) | Metro Memorial Health - Main (`LOC003`) | Primary supplier (`SUP008`) packaging line failure surges lead time from 4 to 25 days; exceeds local safety stock | `HIGH` | 12-14 days |
| **6** | False-Positive Alert Mitigation | Vancomycin HCl (`MED021`) | St. Jude Children's Pavilion (`LOC004`) | On-hand inventory is depleted (< 3 days), but confirmed inbound PO-20242 for 500 units arrives in < 24 hours | `LOW` (Protected) | Protected |

---

## Detailed Scenario Walkthroughs

### Scenario 1: Imminent Critical Stockout
* **Clinical Context**: Norepinephrine is the first-line vasopressor for septic shock and severe hemodynamic collapse in ICUs and trauma resuscitations.
* **Underlying Data Dynamics**:
  - `utilization_daily.csv`: In the final 30 days, trauma patient influx drives daily usage from 28 vials/day to 55+ vials/day.
  - `purchase_orders.csv`: Replenishment order `PO-20150` for 600 vials was placed on 2026-08-16 with standard lead time of 4 days (expected 2026-08-20).
  - `supplier_events.csv`: Event `EVT-1001` records a 12-day cold-chain logistics disruption, pushing actual delivery past the snapshot date (order is marked `Delayed`).
  - `inventory.csv`: On Day 365 (`2026-08-31`), on-hand stock is nearly exhausted (`days_of_supply` <= 2.0 days).
* **Expected Agent Action**: Immediately flag as `CRITICAL`, trigger emergency secondary supplier order (`SUP003`), and recommend intra-network stock transfer from Central AMC (`LOC001`).

---

### Scenario 2: Emerging Demand Surge Risk (Early Warning)
* **Clinical Context**: Meropenem is a broad-spectrum carbapenem antibiotic utilized for multidrug-resistant hospital-acquired infections.
* **Underlying Data Dynamics**:
  - `utilization_daily.csv`: Daily consumption accelerates from ~24 vials/day to ~44 vials/day (+76% acceleration) over the last 3 weeks due to rising critical care admissions.
  - `inventory.csv`: On Day 365, on-hand inventory has ~14.3 days of supply based on trailing 14-day average. A standard static threshold rule (e.g. 10 days) would evaluate this as healthy, but predictive trajectory models will show a buffer breach within 7-10 days.
* **Expected Agent Action**: Classify as `MEDIUM / EMERGING RISK`, dynamically adjust safety stock target upwards, and schedule an advance purchase order before stock drops below critical thresholds.

---

### Scenario 3: Inter-Facility Inventory Imbalance (Network Rebalancing)
* **Clinical Context**: Dexmedetomidine is an alpha-2 agonist sedative used in procedural sedation and ICU mechanical ventilation weaning.
* **Underlying Data Dynamics**:
  - `inventory.csv` at `LOC005` (Westside Community): Depleted stock of < 25 vials (`days_of_supply` <= 2.0 days).
  - `inventory.csv` at `LOC001` (Central AMC): Large surplus stockpile of ~1,756 vials (`days_of_supply` = 45.8 days).
* **Expected Agent Action**: Identify the regional inventory disparity and recommend an immediate intra-network transfer of 200 vials from `LOC001` to `LOC005`, eliminating the stockout without placing costly external spot purchase orders.

---

### Scenario 4: Impending Expiration with Low Local Velocity
* **Clinical Context**: Alteplase (tPA) is an ultra-high-cost thrombolytic ($3,100 per 100 mg vial) used in acute ischemic stroke and pulmonary embolism.
* **Underlying Data Dynamics**:
  - `inventory.csv` at `LOC007` (South Ambulatory Center): Low average daily usage (0.21 vials/day) with 221 vials on hand.
  - `expiry_lots.csv`: Lot `LOT-202409-TPA4` contains 221 vials with an expiration date of `2026-10-05` (35 days from snapshot date).
  - At current consumption rate, only ~7 vials will be dispensed before expiration, risking the total write-off of 214 vials (> $660,000 financial waste).
* **Expected Agent Action**: Detect expiry collision, prioritize local FIFO dispensing, and recommend transferring 200 vials to Metro Memorial Main (`LOC003`) where high stroke-team volume (3-4 vials/day) will consume the lot safely before October.

---

### Scenario 5: Upstream Supplier Lead-Time Surge
* **Clinical Context**: Insulin Glargine is a long-acting basal insulin essential for glycemic control across diabetic inpatients.
* **Underlying Data Dynamics**:
  - `suppliers.csv`: Primary supplier `SUP008` has standard lead time of 4 days, but `current_lead_time_days` is elevated to 25 days.
  - `supplier_events.csv`: Event `EVT-1002` documents an automated packaging machinery breakdown at `SUP008`.
  - `inventory.csv`: On-hand stock at `LOC003` is ~11-13 days of supply. Under normal conditions (4 days lead time) this is adequate, but under a 25-day lead time, placing an order today guarantees an unfilled 12-day stockout gap.
* **Expected Agent Action**: Flag high-severity supply chain vulnerability and recommend re-allocating purchase orders to certified secondary supplier `SUP005` (Evergreen Therapeutics) who maintains a 5-day lead time.

---

### Scenario 6: False Alarm Mitigation (Inbound Buffer Protection)
* **Clinical Context**: Vancomycin is a core glycopeptide antibiotic for MRSA and serious Gram-positive bacteremia.
* **Underlying Data Dynamics**:
  - `inventory.csv`: On-hand stock at `LOC004` (St. Jude Children's) is low (`days_of_supply` <= 2.5 days), which would trigger a naive red alert.
  - `purchase_orders.csv`: Purchase order `PO-20242` for 500 vials was placed on 2026-08-28 with supplier `SUP002` (reliability score 0.96) and status `In Transit`, with confirmed expected delivery on `2026-09-01` (tomorrow).
* **Expected Agent Action**: Suppress urgent shortage panic; downgrade severity to `LOW / MONITOR`, recognizing that confirmed pipeline inventory will arrive before stockout occurs.
