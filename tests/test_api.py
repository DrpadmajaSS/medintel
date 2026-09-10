"""
Comprehensive Test Suite for MedIntel FastAPI Backend & Interactive What-If Simulation API.
"""

import pytest
from fastapi.testclient import TestClient

from medintel_api.main import app
from medintel_api.services.data_service import DataService

client = TestClient(app)


def test_health_endpoint():
    """Verify GET /health returns application status, version, and snapshot data."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["data_status"] == "loaded"
    assert data["medications_count"] >= 70
    assert data["locations_count"] == 7
    assert data["assessed_skus_count"] >= 490


def test_medications_endpoint_and_filters():
    """Verify GET /medications with therapeutic class, criticality, and search filtering."""
    # All medications
    res = client.get("/medications")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 70
    assert len(data["items"]) > 0

    # Filter by therapeutic class
    res_vaso = client.get("/medications?therapeutic_class=Vasopressor")
    assert res_vaso.status_code == 200
    vaso_data = res_vaso.json()
    assert vaso_data["total"] >= 1
    assert all("Vasopressor" in m["therapeutic_class"] for m in vaso_data["items"])

    # Filter by search
    res_search = client.get("/medications?search=Norepinephrine")
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["total"] >= 1
    assert any("Norepinephrine" in m["generic_name"] for m in search_data["items"])


def test_locations_endpoint():
    """Verify GET /locations returns all 7 healthcare facilities."""
    res = client.get("/locations")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 7
    assert len(data["items"]) == 7
    loc_ids = [l["location_id"] for l in data["items"]]
    assert "LOC001" in loc_ids
    assert "LOC006" in loc_ids


def test_risks_endpoint_sorting_and_filtering():
    """Verify GET /risks is sorted descending by risk_score and supports risk_level filtering."""
    res = client.get("/risks?limit=50")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 490
    items = data["items"]
    assert len(items) > 0

    # Verify descending sort order
    scores = [i["risk_score"] for i in items]
    assert scores == sorted(scores, reverse=True)

    # Filter by CRITICAL risk level
    res_crit = client.get("/risks?risk_level=CRITICAL")
    assert res_crit.status_code == 200
    crit_items = res_crit.json()["items"]
    assert all(i["risk_level"] == "CRITICAL" for i in crit_items)


def test_medication_risk_detail_and_404():
    """Verify GET /risks/{medication_id} returns detailed intelligence and 404 for invalid ID."""
    # Valid lookup (Norepinephrine)
    res = client.get("/risks/MED001")
    assert res.status_code == 200
    data = res.json()
    assert data["medication_id"] == "MED001"
    assert "Norepinephrine" in data["generic_name"]
    assert len(data["facilities"]) == 7

    # Validate facility fields
    fac0 = data["facilities"][0]
    assert "risk_score" in fac0
    assert "days_of_supply" in fac0
    assert "primary_risk_factors" in fac0
    assert "recommended_review" in fac0

    # Invalid lookup -> 404 Not Found
    res_404 = client.get("/risks/MED999999")
    assert res_404.status_code == 404


def test_inventory_and_utilization():
    """Verify GET /inventory and GET /utilization endpoints."""
    # Inventory
    res_inv = client.get("/inventory?limit=20")
    assert res_inv.status_code == 200
    inv_data = res_inv.json()
    assert inv_data["total"] >= 490
    assert inv_data["total_value_usd"] > 0

    # Utilization
    res_util = client.get("/utilization/MED001?location_id=LOC006")
    assert res_util.status_code == 200
    util_data = res_util.json()
    assert util_data["medication_id"] == "MED001"
    assert len(util_data["time_series"]) >= 300
    assert util_data["total_dispensed"] > 0


def test_suppliers_endpoint():
    """Verify GET /suppliers returns lead time surge and reliability metrics."""
    res = client.get("/suppliers")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 10
    sup0 = data["items"][0]
    assert "standard_lead_time_days" in sup0
    assert "current_lead_time_days" in sup0
    assert "reliability_score" in sup0


def test_daily_intelligence_brief():
    """Verify GET /daily-intelligence returns ACT, WATCH, OPPORTUNITY, and LEARN sections."""
    res = client.get("/daily-intelligence")
    assert res.status_code == 200
    brief = res.json()
    assert "headline" in brief
    assert len(brief["act"]) > 0
    assert len(brief["watch"]) > 0
    assert len(brief["opportunity"]) > 0
    assert len(brief["learn"]) > 0
    assert all(item["category"] == "ACT" for item in brief["act"])
    assert all(item["category"] == "WATCH" for item in brief["watch"])


def test_opportunities_and_metrics():
    """Verify GET /opportunities and GET /metrics endpoints."""
    # Opportunities
    res_opp = client.get("/opportunities")
    assert res_opp.status_code == 200
    opp_data = res_opp.json()
    assert opp_data["total_opportunities_count"] > 0
    assert opp_data["total_value_at_stake_usd"] > 0

    # Metrics
    res_met = client.get("/metrics")
    assert res_met.status_code == 200
    met_data = res_met.json()
    assert met_data["medications_monitored"] >= 70
    assert met_data["locations_monitored"] == 7
    assert met_data["critical_risks"] >= 1
    assert "risk_level_breakdown" in met_data


# ==========================================================================
# What-If Simulation Tests
# ==========================================================================

def test_whatif_demand_surge_decreases_dos():
    """Verify What-If Scenario: +50% demand surge decreases DOS and accelerates stockout."""
    # Meropenem at North Suburban (MED022 @ LOC002)
    payload = {
        "medication_id": "MED022",
        "location_id": "LOC002",
        "demand_change_percent": 50.0,
        "supplier_delay_days": 0.0,
        "inventory_change_percent": 0.0,
        "inventory_transfer_units": 0.0
    }
    res = client.post("/what-if", json=payload)
    assert res.status_code == 200
    data = res.json()

    base = data["baseline"]
    sim = data["scenario"]
    impact = data["impact"]

    assert sim["projected_daily_usage"] > base["average_daily_usage"]
    assert sim["projected_days_of_supply"] < base["days_of_supply"]
    assert impact["delta_days_of_supply"] < 0.0
    assert sim["projected_days_to_stockout"] <= base["days_to_stockout"]


def test_whatif_supplier_delay_increases_risk():
    """Verify What-If Scenario: Supplier delay increases risk score."""
    # Insulin Glargine at Metro Memorial (MED057 @ LOC003)
    payload = {
        "medication_id": "MED057",
        "location_id": "LOC003",
        "demand_change_percent": 0.0,
        "supplier_delay_days": 15.0,
        "inventory_change_percent": 0.0,
        "inventory_transfer_units": 0.0
    }
    res = client.post("/what-if", json=payload)
    assert res.status_code == 200
    data = res.json()

    base = data["baseline"]
    sim = data["scenario"]

    assert sim["projected_supplier_lead_time_days"] == base["supplier_lead_time_days"] + 15.0
    assert sim["projected_risk_score"] >= base["risk_score"]


def test_whatif_inventory_transfer_eliminates_stockout():
    """Verify What-If Scenario: Lateral stock transfer of 150 units reduces risk from HIGH to LOW."""
    # Dexmedetomidine at Westside Community (MED008 @ LOC005)
    payload = {
        "medication_id": "MED008",
        "location_id": "LOC005",
        "demand_change_percent": 0.0,
        "supplier_delay_days": 0.0,
        "inventory_change_percent": 0.0,
        "inventory_transfer_units": 150.0,
        "transfer_source_location_id": "LOC001"
    }
    res = client.post("/what-if", json=payload)
    assert res.status_code == 200
    data = res.json()

    base = data["baseline"]
    sim = data["scenario"]
    impact = data["impact"]

    assert base["risk_level"] in ["HIGH", "CRITICAL"]
    assert sim["projected_quantity_on_hand"] >= 150.0
    assert sim["projected_risk_level"] in ["LOW", "MEDIUM"]
    assert impact["delta_days_of_supply"] > 0
    assert len(impact["affected_locations"]) == 1
    assert impact["affected_locations"][0]["location_id"] == "LOC001"


def test_whatif_immutability():
    """Verify What-If simulation is strictly non-destructive and does not mutate cached data."""
    ds = DataService.get_instance()
    initial_base = ds.assessments_by_sku[("MED001", "LOC006")]["risk_score"]

    # Run extreme perturbation
    payload = {
        "medication_id": "MED001",
        "location_id": "LOC006",
        "demand_change_percent": 150.0,
        "supplier_delay_days": 30.0,
        "inventory_change_percent": -90.0,
        "inventory_transfer_units": 500.0
    }
    res = client.post("/what-if", json=payload)
    assert res.status_code == 200

    # Verify baseline in cache is completely unmodified
    post_base = ds.assessments_by_sku[("MED001", "LOC006")]["risk_score"]
    assert initial_base == post_base


def test_whatif_error_handling():
    """Verify What-If returns 404 for invalid medication/location and 422 for invalid types."""
    # Invalid medication ID
    res_404 = client.post("/what-if", json={
        "medication_id": "MED_INVALID",
        "location_id": "LOC001"
    })
    assert res_404.status_code == 404

    # Invalid parameter types
    res_422 = client.post("/what-if", json={
        "medication_id": "MED001",
        "location_id": "LOC001",
        "demand_change_percent": "NOT_A_NUMBER"
    })
    assert res_422.status_code == 422


def test_chat_copilot():
    """Verify POST /chat returns grounded clinical answers and tool execution metadata."""
    res = client.post("/chat", json={
        "prompt": "Why is Norepinephrine high risk today?"
    })
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert "Norepinephrine" in data["response"]
    assert len(data["suggested_followups"]) > 0
