"""
Integration tests for MedIntel Conversational Routing & Intelligence Layer.
Tests the exact 7-query conversation flow, intent classification priority,
pronoun resolution, context overrides, and ambiguous What-If clarification.
"""

import pytest
from fastapi.testclient import TestClient
from medintel_api.main import app

client = TestClient(app)


def test_full_7_step_conversation_orchestration():
    """
    Tests the exact 7-step conversation sequence:
    1. What should I worry about today? -> get_daily_brief
    2. Why is Norepinephrine at risk? -> get_inventory / risk investigation for MED001
    3. Can I transfer this from somewhere else? -> get_transfer_opportunities (resolves 'this' to MED001)
    4. Which risks are emerging? -> get_emerging_risks (Global scope, does NOT inherit MED001)
    5. Where do we have excess inventory? -> get_opportunities (Global scope)
    6. What happens if demand increases 20%? -> Clarification requested (does NOT guess silently)
    7. Tell me what to do first -> get_action_recommendation (#1 prioritized operational action)
    """
    history = []
    current_context_med_id = None

    # Step 1: "What should I worry about today?"
    resp1 = client.post("/api/chat", json={
        "prompt": "What should I worry about today?",
        "context_medication_id": current_context_med_id,
        "conversation_history": history
    })
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "get_daily_brief" in [t["tool_name"] for t in data1["tools_used"]]
    assert "ACT" in data1["response"]
    current_context_med_id = data1.get("mentioned_medication_id")
    assert current_context_med_id == "MED001"
    history.append({"role": "user", "content": "What should I worry about today?"})
    history.append({"role": "assistant", "content": data1["response"]})

    # Step 2: "Why is Norepinephrine at risk?"
    resp2 = client.post("/api/chat", json={
        "prompt": "Why is Norepinephrine at risk?",
        "context_medication_id": current_context_med_id,
        "conversation_history": history
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "get_inventory" in [t["tool_name"] for t in data2["tools_used"]]
    assert data2["mentioned_medication_id"] == "MED001"
    assert "Valley Regional Trauma Center" in data2["response"]
    current_context_med_id = data2.get("mentioned_medication_id")
    history.append({"role": "user", "content": "Why is Norepinephrine at risk?"})
    history.append({"role": "assistant", "content": data2["response"]})

    # Step 3: "Can I transfer this from somewhere else?"
    # MUST resolve 'this' -> MED001 and perform network transfer analysis
    resp3 = client.post("/api/chat", json={
        "prompt": "Can I transfer this from somewhere else?",
        "context_medication_id": current_context_med_id,
        "conversation_history": history
    })
    assert resp3.status_code == 200
    data3 = resp3.json()
    tool_names3 = [t["tool_name"] for t in data3["tools_used"]]
    assert "get_transfer_opportunities" in tool_names3
    assert data3["mentioned_medication_id"] == "MED001"
    assert "Norepinephrine" in data3["response"]
    assert "Transfer Quantity" in data3["response"] or "Lateral Transfer" in data3["response"]
    assert "$0 incremental" in data3["response"] or "Units" in data3["response"]
    current_context_med_id = data3.get("mentioned_medication_id")
    history.append({"role": "user", "content": "Can I transfer this from somewhere else?"})
    history.append({"role": "assistant", "content": data3["response"]})

    # Step 4: "Which risks are emerging?"
    # MUST perform global emerging risk analysis; MUST NOT inherit MED001!
    resp4 = client.post("/api/chat", json={
        "prompt": "Which risks are emerging?",
        "context_medication_id": current_context_med_id,
        "conversation_history": history
    })
    assert resp4.status_code == 200
    data4 = resp4.json()
    tool_names4 = [t["tool_name"] for t in data4["tools_used"]]
    assert "get_emerging_risks" in tool_names4
    assert "WATCH" in data4["response"] or "Demand Acceleration" in data4["response"]
    # Should feature emerging surges like Meropenem/Dobutamine rather than being constrained to Norepinephrine
    assert "Surge" in data4["response"] or "Velocity" in data4["response"]
    current_context_med_id = data4.get("mentioned_medication_id")
    history.append({"role": "user", "content": "Which risks are emerging?"})
    history.append({"role": "assistant", "content": data4["response"]})

    # Step 5: "Where do we have excess inventory?"
    resp5 = client.post("/api/chat", json={
        "prompt": "Where do we have excess inventory?",
        "context_medication_id": current_context_med_id,
        "conversation_history": history
    })
    assert resp5.status_code == 200
    data5 = resp5.json()
    tool_names5 = [t["tool_name"] for t in data5["tools_used"]]
    assert "get_opportunities" in tool_names5
    assert "Surplus" in data5["response"] or "Dexmedetomidine" in data5["response"]
    current_context_med_id = data5.get("mentioned_medication_id")
    history.append({"role": "user", "content": "Where do we have excess inventory?"})
    history.append({"role": "assistant", "content": data5["response"]})

    # Step 6: "What happens if demand increases 20%?"
    # MUST NOT silently pick a default medication! MUST ask for clarification!
    resp6 = client.post("/api/chat", json={
        "prompt": "What happens if demand increases 20%?",
        "context_medication_id": current_context_med_id,
        "conversation_history": history
    })
    assert resp6.status_code == 200
    data6 = resp6.json()
    assert len(data6["tools_used"]) == 0  # No tool executed yet because clarification is needed
    assert "Which medication would you like me to simulate" in data6["response"]
    assert "Norepinephrine" in data6["response"]
    assert "Meropenem" in data6["response"]
    history.append({"role": "user", "content": "What happens if demand increases 20%?"})
    history.append({"role": "assistant", "content": data6["response"]})

    # Step 7: "Tell me what to do first"
    # MUST synthesize the #1 prioritized operational action from ACT layer
    resp7 = client.post("/api/chat", json={
        "prompt": "Tell me what to do first",
        "context_medication_id": current_context_med_id,
        "conversation_history": history
    })
    assert resp7.status_code == 200
    data7 = resp7.json()
    tool_names7 = [t["tool_name"] for t in data7["tools_used"]]
    assert "get_action_recommendation" in tool_names7
    assert "Priority #1" in data7["response"] or "Highest-Priority Action" in data7["response"]
    assert "Immediate Action Required" in data7["response"]


def test_what_if_simulation_with_explicit_medication():
    """Tests What-If simulation when medication is explicitly named."""
    response = client.post("/api/chat", json={
        "prompt": "What happens if demand increases 20% for Meropenem at North Suburban?"
    })
    assert response.status_code == 200
    data = response.json()
    assert "run_what_if_simulation" in [t["tool_name"] for t in data["tools_used"]]
    assert "Meropenem" in data["response"]
    assert "Before vs. After" in data["response"]
    assert "Days of Supply" in data["response"]


def test_what_if_simulation_with_context_pronoun():
    """Tests What-If simulation when user refers to 'this medication' with active context."""
    response = client.post("/api/chat", json={
        "prompt": "What happens if demand for this medication increases 30%?",
        "context_medication_id": "MED022"  # Meropenem
    })
    assert response.status_code == 200
    data = response.json()
    assert "run_what_if_simulation" in [t["tool_name"] for t in data["tools_used"]]
    assert "Meropenem" in data["response"]


def test_supplier_disruptions_routing():
    """Tests supplier analysis intent."""
    response = client.post("/api/chat", json={
        "prompt": "Which suppliers have disruptions?"
    })
    assert response.status_code == 200
    data = response.json()
    assert "get_supplier_disruptions" in [t["tool_name"] for t in data["tools_used"]]
    assert "distributors" in data["response"].lower() or "supplier" in data["response"].lower()


def test_utilization_trends_routing():
    """Tests utilization acceleration trends intent."""
    response = client.post("/api/chat", json={
        "prompt": "Which medications have accelerating demand?"
    })
    assert response.status_code == 200
    data = response.json()
    assert "get_utilization_trends" in [t["tool_name"] for t in data["tools_used"]]
    assert "Velocity" in data["response"] or "accelerat" in data["response"].lower()


def test_recent_changes_routing():
    """Tests recent operational changes intent."""
    response = client.post("/api/chat", json={
        "prompt": "What changed recently across our supply network?"
    })
    assert response.status_code == 200
    data = response.json()
    assert "get_recent_changes" in [t["tool_name"] for t in data["tools_used"]]
    assert "Changes in the Last Assessment" in data["response"] or "Operational Shift" in data["response"]
