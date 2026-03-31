"""
Phase 5 Backend — API Test Suite
=================================
Tests all API endpoints: health, auth, emissions, credits, trading,
blockchain, analytics.
"""
import os
import sys
import pytest

# Add project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "phase5_deployment", "backend")
sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def get_token(username="admin", password="admin123"):
    """Login and return Authorization header."""
    resp = client.post("/api/v1/auth/login", json={
        "username": username, "password": password,
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════
#  HEALTH
# ═══════════════════════════════════════════════════════════════════

class TestHealth:
    def test_health_endpoint(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_metrics_endpoint(self):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "carbon_request_total" in resp.text


# ═══════════════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════════════

class TestAuth:
    def test_login_success(self):
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "admin123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_fail(self):
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "wrong",
        })
        assert resp.status_code == 401

    def test_register_and_login(self):
        resp = client.post("/api/v1/auth/register", json={
            "username": "testuser99", "password": "testpass123",
            "full_name": "Test User", "role": "viewer",
        })
        assert resp.status_code == 200
        assert resp.json()["success"]

    def test_me_endpoint(self):
        headers = get_token()
        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"

    def test_unauthorized_without_token(self):
        resp = client.get("/api/v1/emissions/summary")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
#  EMISSIONS
# ═══════════════════════════════════════════════════════════════════

class TestEmissions:
    def test_submit_reading(self):
        headers = get_token()
        reading = {
            "facility_id": "TEST_001",
            "facility_type": "chemical_manufacturing",
            "co2_ppm": 420.0,
            "ch4_ppm": 1.8,
            "nox_ppb": 50.0,
            "fuel_rate": 15.0,
            "energy_kwh": 100.0,
        }
        resp = client.post("/api/v1/emissions/readings", json=reading, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"]
        assert "co2e_emission" in data["data"]
        assert "blockchain_hash" in data["data"]

    def test_submit_batch(self):
        headers = get_token()
        readings = [
            {
                "facility_id": f"TEST_{i:03d}",
                "facility_type": "power_generation",
                "co2_ppm": 400 + i * 10,
                "ch4_ppm": 1.5,
                "nox_ppb": 45.0,
                "fuel_rate": 12.0,
                "energy_kwh": 90.0,
            }
            for i in range(5)
        ]
        resp = client.post("/api/v1/emissions/readings/batch", json=readings, headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 5

    def test_get_readings(self):
        headers = get_token()
        resp = client.get("/api/v1/emissions/readings", headers=headers)
        assert resp.status_code == 200

    def test_get_summary(self):
        headers = get_token()
        resp = client.get("/api/v1/emissions/summary", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_readings" in data

    def test_get_facilities(self):
        headers = get_token()
        resp = client.get("/api/v1/emissions/facilities", headers=headers)
        assert resp.status_code == 200

    def test_viewer_cannot_submit(self):
        headers = get_token("viewer", "viewer123")
        reading = {
            "facility_id": "X", "facility_type": "power_generation",
            "co2_ppm": 400, "ch4_ppm": 1.5, "nox_ppb": 40,
            "fuel_rate": 10, "energy_kwh": 80,
        }
        resp = client.post("/api/v1/emissions/readings", json=reading, headers=headers)
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════
#  CREDITS
# ═══════════════════════════════════════════════════════════════════

class TestCredits:
    def test_get_balance(self):
        headers = get_token()
        resp = client.get("/api/v1/credits/balance/TEST_001", headers=headers)
        assert resp.status_code == 200
        assert "balance" in resp.json()["data"]

    def test_get_all_balances(self):
        headers = get_token()
        resp = client.get("/api/v1/credits/balances", headers=headers)
        assert resp.status_code == 200

    def test_get_supply(self):
        headers = get_token()
        resp = client.get("/api/v1/credits/supply", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_supply" in data
        assert data["symbol"] == "CCT"


# ═══════════════════════════════════════════════════════════════════
#  TRADING
# ═══════════════════════════════════════════════════════════════════

class TestTrading:
    def test_place_order(self):
        headers = get_token()
        order = {
            "participant_id": "TEST_001",
            "side": "sell",
            "quantity": 1.0,
            "price": 25.0,
            "order_type": "limit",
        }
        resp = client.post("/api/v1/trading/orders", json=order, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "placed"

    def test_get_orderbook(self):
        headers = get_token()
        resp = client.get("/api/v1/trading/orderbook", headers=headers)
        assert resp.status_code == 200

    def test_get_price(self):
        headers = get_token()
        resp = client.get("/api/v1/trading/price", headers=headers)
        assert resp.status_code == 200
        assert "current_price" in resp.json()["data"]


# ═══════════════════════════════════════════════════════════════════
#  BLOCKCHAIN
# ═══════════════════════════════════════════════════════════════════

class TestBlockchain:
    def test_get_status(self):
        headers = get_token()
        resp = client.get("/api/v1/blockchain/status", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["chain_length"] > 0
        assert data["is_valid"]

    def test_get_blocks(self):
        headers = get_token()
        resp = client.get("/api/v1/blockchain/blocks?limit=5", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) <= 5

    def test_verify_chain(self):
        headers = get_token()
        resp = client.get("/api/v1/blockchain/verify", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["is_valid"]


# ═══════════════════════════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════════════════════════

class TestAnalytics:
    def test_dashboard_overview(self):
        headers = get_token()
        resp = client.get("/api/v1/analytics/overview", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_emissions" in data
        assert "blockchain_blocks" in data

    def test_forecast(self):
        headers = get_token()
        resp = client.get("/api/v1/analytics/forecast", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "forecast_prices" in data
        assert len(data["forecast_prices"]) > 0

    def test_comparison(self):
        headers = get_token()
        resp = client.get("/api/v1/analytics/comparison", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "proposed" in data
        assert "traditional_ets" in data

    def test_emission_trend(self):
        headers = get_token()
        resp = client.get("/api/v1/analytics/emissions/trend", headers=headers)
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
