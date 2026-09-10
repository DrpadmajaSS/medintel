# MedIntel AI Data Dictionary

This document describes the schema, field types, constraints, and business logic for all synthetic datasets in the MedIntel clinical medication supply-chain platform.

---

## 1. `medications.csv`
Master formulary catalog of clinical medications.

| Field Name | Data Type | Constraint | Description | Example Values |
| :--- | :--- | :--- | :--- | :--- |
| `medication_id` | `VARCHAR(10)` | **PK**, Not Null | Unique medication identifier | `MED001`, `MED022` |
| `generic_name` | `VARCHAR(100)` | Not Null | Standard generic clinical name of drug | `Norepinephrine Bitartrate`, `Meropenem` |
| `strength` | `VARCHAR(50)` | Not Null | Dosage strength and concentration | `4 mg/4 mL`, `1 g`, `100 units/mL` |
| `dosage_form` | `VARCHAR(50)` | Not Null | Physical formulation of medication | `Injectable Solution`, `IV Infusion` |
| `unit_of_measure` | `VARCHAR(20)` | Not Null | Primary dispensing unit | `vial`, `bag`, `syringe`, `ampule` |
| `therapeutic_class` | `VARCHAR(60)` | Not Null | Clinical pharmacological category | `Vasopressor / Inotrope`, `Carbapenem` |
| `unit_cost` | `DECIMAL(10,2)` | Not Null, > 0 | Synthetic acquisition cost per unit ($USD) | `14.50`, `85.00`, `3100.00` |
| `criticality` | `VARCHAR(20)` | `High` / `Medium` / `Low` | Clinical impact of shortage | `High` (life-critical), `Medium`, `Low` |

---

## 2. `locations.csv`
Master catalog of healthcare facilities and delivery network nodes.

| Field Name | Data Type | Constraint | Description | Example Values |
| :--- | :--- | :--- | :--- | :--- |
| `location_id` | `VARCHAR(10)` | **PK**, Not Null | Unique facility identifier | `LOC001`, `LOC006` |
| `location_name` | `VARCHAR(100)` | Not Null | Name of the hospital or clinical site | `Central Academic Medical Center` |
| `location_type` | `VARCHAR(50)` | Not Null | Facility operational archetype | `Academic Medical Center`, `Trauma Center` |
| `region` | `VARCHAR(50)` | Not Null | Geographic network region | `Central Metro`, `West Valley`, `South Metro` |

---

## 3. `suppliers.csv`
Pharmaceutical distributors, wholesalers, and supplier contract mappings.

| Field Name | Data Type | Constraint | Description | Example Values |
| :--- | :--- | :--- | :--- | :--- |
| `supplier_id` | `VARCHAR(10)` | **PK (Composite)**, Not Null | Unique supplier identifier | `SUP001`, `SUP008` |
| `supplier_name` | `VARCHAR(100)` | Not Null | Company name of supplier | `Apex Rx Distribution`, `Horizon Medical` |
| `medication_id` | `VARCHAR(10)` | **PK (Composite)**, **FK** -> `medications` | Medication supplied | `MED001` |
| `standard_lead_time_days` | `INTEGER` | Not Null, >= 1 | Contracted baseline lead time in days | `3`, `5`, `7` |
| `current_lead_time_days` | `INTEGER` | Not Null, >= 1 | Active dynamic lead time | `5` (normal), `25` (during disruption) |
| `reliability_score` | `DECIMAL(3,2)` | `0.00` to `1.00` | Historical on-time fulfillment score | `0.97`, `0.89` |

---

## 4. `inventory.csv`
Daily closed-loop inventory snapshots across all facilities and medications.

| Field Name | Data Type | Constraint | Description | Example Values |
| :--- | :--- | :--- | :--- | :--- |
| `inventory_id` | `VARCHAR(40)` | **PK**, Not Null | Snapshot identifier (`INV-YYYYMMDD-MEDxxx-LOCxxx`) | `INV-20260831-MED001-LOC006` |
| `medication_id` | `VARCHAR(10)` | **FK** -> `medications` | Medication identifier | `MED001` |
| `location_id` | `VARCHAR(10)` | **FK** -> `locations` | Location identifier | `LOC006` |
| `snapshot_date` | `DATE (YYYY-MM-DD)` | Not Null | Snapshot date | `2026-08-31` |
| `quantity_on_hand` | `INTEGER` | Not Null, >= 0 | Physical usable units in stock | `45`, `2200` |
| `reorder_level` | `INTEGER` | Not Null, >= 0 | Dynamically computed reorder threshold | `85`, `340` |
| `average_daily_usage` | `DECIMAL(8,2)` | Not Null, >= 0.1 | 14-day trailing average daily burn rate | `24.50`, `44.00` |
| `days_of_supply` | `DECIMAL(8,1)` | Not Null, >= 0.0 | Calculated buffer: `round(QOH / max(ADU, 0.1), 1)` | `1.8`, `14.3`, `62.9` |

---

## 5. `utilization_daily.csv`
Daily clinical medication dispensing and patient volume time-series.

| Field Name | Data Type | Constraint | Description | Example Values |
| :--- | :--- | :--- | :--- | :--- |
| `date` | `DATE (YYYY-MM-DD)` | **PK (Composite)**, Not Null | Transaction date | `2025-10-14`, `2026-08-31` |
| `medication_id` | `VARCHAR(10)` | **PK (Composite)**, **FK** -> `medications` | Dispensed medication | `MED001` |
| `location_id` | `VARCHAR(10)` | **PK (Composite)**, **FK** -> `locations` | Administering location | `LOC006` |
| `quantity_used` | `INTEGER` | Not Null, >= 0 | Total units dispensed/consumed on date | `32`, `55`, `0` |
| `patient_activity_index` | `DECIMAL(5,3)` | Not Null, > 0 | Facility census/acuity index | `1.042`, `1.215`, `0.780` |

---

## 6. `purchase_orders.csv`
Replenishment purchase orders placed with pharmaceutical distributors.

| Field Name | Data Type | Constraint | Description | Example Values |
| :--- | :--- | :--- | :--- | :--- |
| `po_id` | `VARCHAR(20)` | **PK**, Not Null | Purchase order number | `PO-10045` |
| `medication_id` | `VARCHAR(10)` | **FK** -> `medications` | Ordered medication | `MED001` |
| `location_id` | `VARCHAR(10)` | **FK** -> `locations` | Destination healthcare facility | `LOC006` |
| `supplier_id` | `VARCHAR(10)` | **FK** -> `suppliers` | Fulfilling supplier | `SUP001` |
| `order_date` | `DATE (YYYY-MM-DD)` | Not Null | Date purchase order was issued | `2026-08-16` |
| `expected_delivery_date` | `DATE (YYYY-MM-DD)` | Not Null, >= `order_date` | Contracted expected arrival date | `2026-08-20` |
| `actual_delivery_date` | `DATE (YYYY-MM-DD)` | Nullable | Actual arrival date (null if open/in transit) | `2026-08-21`, `NULL` |
| `quantity_ordered` | `INTEGER` | Not Null, > 0 | Total units requested | `600`, `1800` |
| `quantity_received` | `INTEGER` | Not Null, <= `quantity_ordered` | Total usable units received | `600`, `450`, `0` |
| `status` | `VARCHAR(30)` | Enumeration | Order lifecycle state | `Delivered`, `In Transit`, `Delayed`, `Partially Delivered` |

---

## 7. `supplier_events.csv`
Upstream pharmaceutical manufacturing and supply chain disruption events.

| Field Name | Data Type | Constraint | Description | Example Values |
| :--- | :--- | :--- | :--- | :--- |
| `event_id` | `VARCHAR(20)` | **PK**, Not Null | Event identifier | `EVT-1001` |
| `supplier_id` | `VARCHAR(10)` | **FK** -> `suppliers` | Affected supplier | `SUP001` |
| `medication_id` | `VARCHAR(10)` | **FK** -> `medications` | Affected medication | `MED001` |
| `event_date` | `DATE (YYYY-MM-DD)` | Not Null | Date incident was recorded | `2026-08-16` |
| `event_type` | `VARCHAR(50)` | Not Null | Disruption category | `Transportation Delay`, `Packaging Line Disruption` |
| `delay_days` | `INTEGER` | Not Null, >= 0 | Resulting delivery delay in days | `12`, `20` |
| `description` | `TEXT` | Not Null | Synthetic root cause summary | `"Cryogenic carrier line-haul bottleneck..."` |

---

## 8. `expiry_lots.csv`
Active physical inventory lot batches, manufacturing dates, and expiration milestones.

| Field Name | Data Type | Constraint | Description | Example Values |
| :--- | :--- | :--- | :--- | :--- |
| `lot_id` | `VARCHAR(30)` | **PK**, Not Null | Manufacturer batch lot number | `LOT-202409-TPA4` |
| `medication_id` | `VARCHAR(10)` | **FK** -> `medications` | Medication identifier | `MED039` |
| `location_id` | `VARCHAR(10)` | **FK** -> `locations` | Physical storage facility | `LOC007` |
| `quantity` | `INTEGER` | Not Null, > 0 | Remaining units in this lot | `221`, `450` |
| `manufacture_date` | `DATE (YYYY-MM-DD)` | Not Null | Release / manufacture date | `2024-09-15` |
| `expiry_date` | `DATE (YYYY-MM-DD)` | Not Null, > `manufacture_date` | Expiration date | `2026-10-05` |

---

## 9. `ground_truth.csv` *(Evaluation Benchmark Only)*
Ground truth benchmark scenarios used exclusively for testing MedIntel AI algorithms.

| Field Name | Data Type | Constraint | Description | Example Values |
| :--- | :--- | :--- | :--- | :--- |
| `scenario_id` | `VARCHAR(20)` | **PK**, Not Null | Unique test scenario ID | `SCENARIO-1` to `SCENARIO-6` |
| `medication_id` | `VARCHAR(10)` | **FK** -> `medications` | Target medication | `MED001` |
| `location_id` | `VARCHAR(10)` | **FK** -> `locations` | Target healthcare location | `LOC006` |
| `expected_issue` | `TEXT` | Not Null | Expected clinical/supply risk root cause | `Surging ICU utilization + supplier delay` |
| `expected_severity` | `VARCHAR(20)` | Not Null | Ground-truth severity classification | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `expected_stockout_window`| `VARCHAR(50)` | Not Null | Estimated time to inventory breach | `2-3 days`, `7-10 days`, `None` |
| `expected_recommendation`| `TEXT` | Not Null | Clinically sound mitigation action | `Expedite secondary PO & execute lateral transfer` |
