# MedIntel AI: Risk Intelligence Engine Methodology & Architecture

The **MedIntel Risk Intelligence Engine** is a deterministic, clinically informed, multi-signal medication supply-chain and operational risk assessment system.

It calculates medication risk scores, predicts stockout horizons, generates factor-level explainability, and formulates context-aware clinical and supply-chain review actions across all facility-medication SKUs.

---

## 1. System Architecture

```
                                  [ Raw Multi-Table Data ]
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      │                                      │                                      │
[ Daily Utilization ]              [ Suppliers & Events ]                   [ Expiry Lots ]
      │                                      │                                      │
      ▼                                      ▼                                      ▼
[ Utilization Signals ]             [ Supply Chain Signals ]             [ Batch Expiry Signals ]
 (ADU 7d/14d/30d, Trend, CV)         (Lead Time Surge, Delays)            (Shelf-life, Dollar Waste)
      │                                      │                                      │
      └──────────────────────────────────────┼──────────────────────────────────────┘
                                             │
                          [ Pipeline & Network Signals ]
                           (In-Transit POs, Sister Surplus)
                                             │
                                             ▼
                          [ 60-Day Stockout Predictor ]
                           (Forward Dynamic Simulation)
                                             │
                                             ▼
                         [ Explainable Risk Calculator ]
                          • Weighted Component Scoring
                          • Inbound PO & Surplus Discounts
                          • Criticality Weight Scaling
                                             │
                                             ▼
                        [ Structured Assessment Output ]
                          • risk_score (0.0 - 100.0)
                          • risk_level (CRITICAL/HIGH/MED/LOW)
                          • days_to_stockout & predicted_date
                          • primary / contributing / mitigating
                          • recommended_review
```

---

## 2. Feature & Signal Engineering

### A. Demand Velocity & Trend Signals
- **Rolling Moving Averages**:
  $$ADU_{7d} = \frac{1}{7} \sum_{k=0}^6 U_{t_0-k}, \quad ADU_{30d} = \frac{1}{30} \sum_{k=0}^{29} U_{t_0-k}$$
- **Velocity Trend Ratio**:
  $$\text{trend\_ratio} = \frac{ADU_{7d}}{\max(ADU_{30d}, 0.1)}$$
- **Demand Volatility (Coefficient of Variation)**:
  $$CV = \frac{\sigma(U_{30d})}{\max(ADU_{30d}, 0.1)}$$

### B. Upstream Supply Chain & Disruption Signals
- **Lead Time Surge**:
  $$\Delta LT = \max(0, LT_{\text{current}} - LT_{\text{standard}})$$
- **Active Supplier Delay**: Sum of $\text{delay\_days}$ from active disruptions in `supplier_events.csv` within 30 days.
- **Supplier Reliability**: Historical fulfillment reliability $R \in [0.0, 1.0]$.
- **Alternate Certified Suppliers**: Identification of secondary vendors certified for the medication maintaining standard lead times.

### C. Pipeline Inventory & In-Transit Tracking
- **Active Open POs**: Unfulfilled orders placed within the operational window with status `In Transit` or `Delayed`.
- **Delivery Proximity**: Days until nearest expected delivery $d_{\text{po}} = D_{\text{expected}} - t_0$.
- **Supersession Filtering**: Outdated delayed orders that have already been superseded by a subsequent delivered order are automatically filtered out.

### D. Regional Network Surplus (Inter-Facility Rebalancing)
- **Sister Facility Surplus**: Scans all facilities $l' \neq l$ for surplus stock ($DOS \ge 30$ days and $QOH \ge 500$ units).
- Identifies lateral transfer opportunities to resolve local shortages without placing emergency external spot purchases.

### E. Expiry & Shelf-Life Collision Analysis
- For lots with remaining shelf-life $DTE \le 60$ days:
  $$U_{\text{projected}} = DTE \times \max(ADU_{7d}, ADU_{30d}, 0.1)$$
  $$Q_{\text{waste}} = \max(0, Q_{\text{lot}} - U_{\text{projected}})$$
  $$\text{Loss}_{\text{projected}} = Q_{\text{waste}} \times \text{unit\_cost}$$

---

## 3. Stockout Forward Trajectory Simulation

A 60-day discrete-event forward trajectory is simulated for each SKU:
$$Inv(d) = Inv(d-1) - \hat{U}(d) + \sum_{\text{POs arriving on } d} Q_{\text{po}}$$
- $\hat{U}(d) = ADU_{7d}$ for $d \le 14$ days (capturing immediate trend surge), transitioning to $ADU_{30d}$ for longer horizons.
- First day $d^*$ where $Inv(d^*) \le 0$ determines:
  - $\text{days\_to\_stockout} = d^*$
  - $\text{predicted\_stockout\_date} = t_0 + d^* \text{ days}$

---

## 4. Explainable Scoring Formulation

### A. Raw Component Scores ($0 - 100$)
- **Days of Supply Score ($S_{\text{DOS}}$)**:
  - $DOS \le 2.0 \implies 100$
  - $DOS \le 5.0 \implies 75$
  - $DOS \le 10.0 \implies 45$
  - $DOS \le 15.0 \implies 20$
  - $DOS > 15.0 \implies 0$
- **Demand Trend Score ($S_{\text{trend}}$)**:
  - $\text{trend\_ratio} \ge 1.50 \implies 80$
  - $\text{trend\_ratio} \ge 1.25 \implies 55$
  - $\text{trend\_ratio} \ge 1.10 \implies 25$
- **Supply Chain Score ($S_{\text{supply}}$)**:
  - Active disruption delay $\implies 90$
  - Lead time surge $\Delta LT \ge 10 \implies 80$
  - Current lead time $> DOS$ with $DOS \le 15 \implies 50$
- **Expiry Risk Score ($S_{\text{expiry}}$)**:
  - Projected waste loss $>\$500\text{k} \implies 75$
  - Projected waste loss $>\$10\text{k}$ and $Q_{\text{waste}} > 10 \implies 65$

### B. Composite Synthesis & Criticality Weighting
$$\text{Base Score} = 0.40 S_{\text{DOS}} + 0.35 S_{\text{supply}} + 0.20 S_{\text{trend}} + 0.05 (CV \times 50)$$
$$\text{Final Score} = \min(100.0, \text{Base Score} \times w_{\text{crit}})$$

*Criticality Multipliers ($w_{\text{crit}}$)*: `High` = $1.30$, `Medium` = $1.00$, `Low` = $0.75$.

---

## 5. False Alarm & Mitigation Logic

1. **Inbound Purchase Order Protection (Scenario 6)**:
   - When on-hand inventory is depleted ($DOS \le 3.0$ days), but a verified `In Transit` PO from a high-reliability vendor ($R \ge 0.90$) is scheduled to arrive in $\le 1.5$ days, the engine suppresses the panic score to $\le 15.0$ and assigns `LOW / Protected`.
2. **Regional Network Rebalancing (Scenario 3)**:
   - When acute low inventory at one location is accompanied by large surplus at a sister facility within the network, the engine categorizes the issue as `HIGH (Imbalance)` and generates a lateral stock transfer recommendation.

---

## 6. Actionable Clinical & Operational Review Rules

The engine produces tailored, non-generic operational directives:
- **`CRITICAL` Shortage with Regional Surplus**: Declare acute shortage, expedite secondary vendor PO, and initiate urgent transfer of $N$ units from Sister Facility.
- **`HIGH` Lead-Time Surge**: Reroute replenishment orders to named certified alternate vendor with standard lead time.
- **`HIGH` Expiry Collision**: Prevent write-off of $\$X$: prioritize local FIFO dispensing and transfer $N$ units to high-volume comprehensive center.
- **`MEDIUM` Emerging Surge**: Dynamically adjust safety stock baseline upwards and trigger automated replenishment PO 5 days ahead of schedule.
- **`LOW` Protected / False Alarm**: No escalation required; inbound shipment confirmed on schedule with carrier tracking.
