"""API-тесты: CRUD товаров, валидация, сохранение данных."""

from __future__ import annotations

from app.models.product import Product


class TestProductCrud:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_create_product(self, client, auth_headers):
        response = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "name": "Наушники X",
                "marketplace": "ozon",
                "category": "электроника",
                "sku": "SKU-1",
                "description": "До 30 часов работы.",
                "attributes": {"battery_life_hours": 30},
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["name"] == "Наушники X"
        assert payload["marketplace"] == "ozon"
        assert payload["attributes"] == {"battery_life_hours": 30}

    def test_product_is_persisted_and_visible_after_reload(self, client, auth_headers):
        created = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={"name": "Сохраняемый товар", "marketplace": "demo"},
        ).json()
        listing = client.get("/api/v1/products", headers=auth_headers).json()
        assert any(item["id"] == created["id"] for item in listing)
        fetched = client.get(f"/api/v1/products/{created['id']}", headers=auth_headers)
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Сохраняемый товар"

    def test_update_product(self, client, auth_headers, product):
        response = client.patch(
            f"/api/v1/products/{product['id']}",
            headers=auth_headers,
            json={"name": "Обновлённое название", "attributes": {"weight_g": 300}},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Обновлённое название"
        assert response.json()["attributes"] == {"weight_g": 300}

    def test_delete_product(self, client, auth_headers, product):
        response = client.delete(f"/api/v1/products/{product['id']}", headers=auth_headers)
        assert response.status_code == 204
        assert (
            client.get(f"/api/v1/products/{product['id']}", headers=auth_headers).status_code
            == 404
        )

    def test_search_products(self, client, auth_headers, product):
        response = client.get(
            "/api/v1/products", headers=auth_headers, params={"search": "Тестовый"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestProductValidation:
    def test_name_is_required(self, client, auth_headers):
        response = client.post(
            "/api/v1/products", headers=auth_headers, json={"name": "   "}
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "message" in body["error"]

    def test_name_length_is_limited(self, client, auth_headers):
        response = client.post(
            "/api/v1/products", headers=auth_headers, json={"name": "x" * 300}
        )
        assert response.status_code == 422

    def test_invalid_marketplace_is_rejected(self, client, auth_headers):
        response = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={"name": "Товар", "marketplace": "avito"},
        )
        assert response.status_code == 422

    def test_error_response_has_no_traceback(self, client, auth_headers):
        response = client.post("/api/v1/products", headers=auth_headers, json={})
        body = response.json()
        assert "Traceback" not in response.text
        assert "sql" not in response.text.lower()
        assert set(body.keys()) == {"error"}
        assert set(body["error"].keys()) >= {"code", "message", "details"}


class TestAuthentication:
    def test_products_require_token(self, client):
        assert client.get("/api/v1/products").status_code == 401

    def test_invalid_token_is_rejected(self, client):
        response = client.get(
            "/api/v1/products", headers={"Authorization": "Bearer nonsense"}
        )
        assert response.status_code == 401

    def test_register_and_login(self, client):
        registration = client.post(
            "/api/v1/auth/register",
            json={
                "email": "seller@example.com",
                "password": "very-secret-1",
                "display_name": "Продавец",
                "workspace_name": "Карточки WB",
            },
        )
        assert registration.status_code == 201, registration.text
        token = registration.json()["access_token"]

        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "seller@example.com"

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "seller@example.com", "password": "very-secret-1"},
        )
        assert login.status_code == 200

    def test_duplicate_registration_conflicts(self, client):
        payload = {
            "email": "dup@example.com",
            "password": "very-secret-1",
            "workspace_name": "Рабочее пространство",
        }
        assert client.post("/api/v1/auth/register", json=payload).status_code == 201
        assert client.post("/api/v1/auth/register", json=payload).status_code == 409

    def test_wrong_password_is_rejected(self, client):
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong@example.com",
                "password": "very-secret-1",
                "workspace_name": "Рабочее пространство",
            },
        )
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "incorrect"},
        )
        assert response.status_code == 401
