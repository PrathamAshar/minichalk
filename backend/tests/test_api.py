from fastapi.testclient import TestClient

from app.main import create_app


def test_end_to_end_and_persistence(tmp_path):
    path = str(tmp_path / "demo.sqlite3")
    with TestClient(create_app(path)) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.get("/api/stats").json()["query_count"] == 0
        assert client.get("/api/stats").json()["median_ms"] is None
        features = client.get("/api/features").json()
        assert len(features) == 9
        assert client.get("/api/features/user.fraud_score/graph").status_code == 200
        body = {"entity_id": "usr_nova", "features": ["user.fraud_score"]}
        response = client.post("/api/query", json=body)
        assert response.status_code == 200
        trace = response.json()
        assert trace["status"] == "success"
        assert 70 < trace["results"]["user.fraud_score"] <= 100
        assert len(trace["spans"]) == 9
        first = trace["query_id"]
        assert client.get(f"/api/traces/{first}").json() == trace
        warm = client.post("/api/query", json=body).json()
        assert all(s["cache"] == "hit" for s in warm["spans"])
        normal = client.post("/api/query", json={**body, "entity_id": "usr_ada"}).json()
        assert normal["results"]["user.fraud_score"] < trace["results"]["user.fraud_score"]
        stats = client.get("/api/stats").json()
        assert stats["query_count"] == 3 and stats["cache_hit_rate"] > 0
        invalidated = client.post(
            "/api/cache/invalidate",
            json={
                "feature": "user.unique_devices_7d",
                "entity_id": "usr_nova",
            },
        ).json()
        assert invalidated["affected_features"] == [
            "user.device_risk",
            "user.fraud_score",
            "user.unique_devices_7d",
        ]
        assert invalidated["removed"] == 3
        timeout = client.post(
            "/api/query", json={**body, "bypass_cache": True, "timeout_seconds": 0.001}
        ).json()
        assert timeout["status"] == "timeout"
        assert client.get("/api/traces/not-real").status_code == 404
        assert client.get("/api/features/not-real").status_code == 404
        assert client.post("/api/query", json={**body, "features": ["missing"]}).status_code == 422
        assert client.post("/api/query", json={**body, "features": []}).status_code == 422
        assert client.post("/api/query", json={**body, "entity_id": "missing"}).status_code == 404
        assert client.post("/api/query", json={**body, "timeout_seconds": -1}).status_code == 422
        assert client.get("/openapi.json").json()["openapi"].startswith("3.")
    with TestClient(create_app(path)) as client:
        assert client.get(f"/api/traces/{first}").status_code == 200
