import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.main as main


def _sample_snapshot():
    return [
        {
            "target": "https://example.com",
            "up": True,
            "last_latency_ms": 123.45,
            "status_code": 200,
            "checked_at": "2026-04-08T12:00:00+00:00",
        }
    ]


class AppTests(unittest.TestCase):
    def test_dashboard_renders_snapshot(self):
        snapshot = _sample_snapshot()

        with patch.object(main.settings, "ENABLE_BACKGROUND_MONITOR", False), patch(
            "app.main.get_snapshot",
            return_value=snapshot,
        ):
            with TestClient(main.app) as client:
                response = client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Site Monitor", response.text)
        self.assertIn("https://example.com", response.text)
        self.assertIn("123.45 ms", response.text)

    def test_targets_refresh_runs_live_check(self):
        snapshot = _sample_snapshot()

        with patch.object(main.settings, "ENABLE_BACKGROUND_MONITOR", False), patch(
            "app.main.get_snapshot",
            return_value=[],
        ), patch(
            "app.main.run_checks",
            new=AsyncMock(return_value=snapshot),
        ):
            with TestClient(main.app) as client:
                response = client.get("/targets?refresh=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], snapshot)

    def test_api_check_requires_secret_when_configured(self):
        with patch.object(main.settings, "ENABLE_BACKGROUND_MONITOR", False), patch.object(
            main.settings,
            "CRON_SECRET",
            "super-secret",
        ):
            with TestClient(main.app) as client:
                response = client.get("/api/check")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
