import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.server as server


class ServerAuthenticationTests(unittest.TestCase):
    def test_packaged_api_requires_token_and_health_never_echoes_it(self):
        token = "a" * 64
        with patch.object(server, "INSTANCE_TOKEN", token), TestClient(server.app) as client:
            self.assertEqual(client.get("/api/health").status_code, 401)
            self.assertEqual(
                client.get(
                    "/api/health", headers={server.AUTH_HEADER: "wrong"}
                ).status_code,
                401,
            )
            response = client.get(
                "/api/health", headers={server.AUTH_HEADER: token}
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["instance_authenticated"])
        self.assertNotIn(token, response.text)

    def test_browser_only_development_remains_compatible_without_token(self):
        with patch.object(server, "INSTANCE_TOKEN", ""), TestClient(server.app) as client:
            response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["instance_authenticated"])

    def test_cors_preflight_does_not_require_actual_token_header(self):
        with patch.object(server, "INSTANCE_TOKEN", "secret"), TestClient(server.app) as client:
            response = client.options(
                "/api/health",
                headers={
                    "Origin": "http://localhost:1420",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": server.AUTH_HEADER,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:1420",
        )


if __name__ == "__main__":
    unittest.main()
