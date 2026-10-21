"""Тесты конвейера проверки: находки, статусы, история, отчёты."""

from __future__ import annotations

import io

DOCUMENT = (
    "ДЕМО-СЕРТИФИКАТ (синтетический документ)\n"
    "Документ: сертификат соответствия\n"
    "Номер: ТЕСТ-001\n"
    "Дата выдачи: 2024-03-15\n"
    "Область применения: наушники, модель TEST-1\n\n"
    "Технические характеристики по результатам испытаний:\n"
    "Время работы без подзарядки — 30 часов.\n"
    "Масса одного наушника — 250 граммов.\n"
)


def _upload_document(client, headers, product_id, name="doc.txt", text=DOCUMENT, **form):
    data = {key: str(value) for key, value in form.items()}
    response = client.post(
        f"/api/v1/products/{product_id}/sources",
        headers=headers,
        files={"file": (name, io.BytesIO(text.encode("utf-8")), "text/plain")},
        data=data or None,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _run_analysis(client, headers, product_id):
    response = client.post(
        f"/api/v1/products/{product_id}/analysis-runs", headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def _findings(client, headers, product_id, **params):
    response = client.get(
        f"/api/v1/products/{product_id}/findings", headers=headers, params=params or None
    )
    assert response.status_code == 200, response.text
    return response.json()


class TestNumericChecks:
    def test_same_value_and_unit_has_no_direct_conflict(self, client, auth_headers):
        product = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "name": "Совпадающие значения",
                "description": "Время работы 30 часов.",
                "attributes": {"battery_life_hours": 30},
            },
        ).json()
        run = _run_analysis(client, auth_headers, product["id"])
        conflicts = [
            finding
            for finding in _findings(client, auth_headers, product["id"])
            if finding["finding_type"] == "direct_conflict"
        ]
        assert conflicts == []
        assert run["status"] == "completed"

    def test_conflicting_values_produce_finding_with_both_sources(self, client, auth_headers):
        product = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "name": "Расхождение",
                "description": "До 48 часов работы без подзарядки.",
                "attributes": {"battery_life_hours": 30},
            },
        ).json()
        _run_analysis(client, auth_headers, product["id"])
        conflicts = [
            finding
            for finding in _findings(client, auth_headers, product["id"])
            if finding["finding_type"] == "direct_conflict"
        ]
        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert "48" in conflict["description"]
        assert "30" in conflict["description"]
        # Находка связана с источниками и содержит ограничение.
        assert conflict["source_refs"]
        assert conflict["limitations"]
        assert conflict["recommended_action"]

    def test_unit_conversion_is_applied(self, client, auth_headers):
        product = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "name": "Разные единицы",
                "description": "Вес наушников 0,3 кг.",
                "attributes": {"weight_g": 300},
            },
        ).json()
        _run_analysis(client, auth_headers, product["id"])
        conflicts = [
            finding
            for finding in _findings(client, auth_headers, product["id"])
            if finding["finding_type"] == "direct_conflict"
        ]
        assert conflicts == [], "0,3 кг и 300 г — одно и то же значение"

    def test_incompatible_units_are_not_compared(self, client, auth_headers):
        product = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "name": "Разные величины",
                "description": "Мощность 65 ватт, вес 250 граммов.",
                "attributes": {"power_w": 30, "weight_g": 250},
            },
        ).json()
        _run_analysis(client, auth_headers, product["id"])
        conflicts = [
            finding
            for finding in _findings(client, auth_headers, product["id"])
            if finding["finding_type"] == "direct_conflict"
        ]
        assert len(conflicts) == 1
        assert "65" in conflicts[0]["description"]

    def test_different_measurement_conditions_require_human_review(
        self, client, auth_headers
    ):
        product = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "name": "Разные условия испытаний",
                "description": (
                    "При температуре -10 °C время работы составляет 10 часов. "
                    "В остальных условиях время работы 30 часов."
                ),
                "attributes": {"battery_life_hours": 30},
            },
        ).json()
        _run_analysis(client, auth_headers, product["id"])
        findings = _findings(client, auth_headers, product["id"])
        assert not [
            finding
            for finding in findings
            if finding["finding_type"] == "direct_conflict"
        ]
        assert [
            finding
            for finding in findings
            if finding["finding_type"] == "needs_human_review"
        ]


class TestEvidenceAndSignals:
    def test_missing_document_gives_insufficient_evidence_not_accusation(
        self, client, auth_headers
    ):
        product = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "name": "Без документов",
                "description": "Сертификат соответствия ГОСТ Р приложен к карточке.",
                "attributes": {"model": "TEST-2"},
            },
        ).json()
        _run_analysis(client, auth_headers, product["id"])
        findings = _findings(client, auth_headers, product["id"])
        missing = [
            finding
            for finding in findings
            if finding["finding_type"] == "missing_evidence"
        ]
        assert missing, "Ожидается находка о нехватке подтверждения"
        assert "не является доказательством" in missing[0]["limitations"]
        # В тексте находки нет обвинительных формулировок.
        text = (missing[0]["description"] + missing[0]["title"]).lower()
        for forbidden in ("мошенник", "подделк", "недобросовест", "обман"):
            assert forbidden not in text

    def test_single_negative_review_is_a_signal_only(self, client, auth_headers):
        product = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "name": "Один негативный отзыв",
                "description": "До 48 часов работы без подзарядки.",
                "attributes": {"battery_life_hours": 30},
            },
        ).json()
        _upload_document(
            client,
            auth_headers,
            product["id"],
            name="reviews.csv",
            text=(
                "date,rating,text\n"
                '2024-05-03,2,"Батарея держится 20 часов, а не 48 как обещано."\n'
            ),
        )
        _run_analysis(client, auth_headers, product["id"])
        signals = [
            finding
            for finding in _findings(client, auth_headers, product["id"])
            if finding["finding_type"] == "review_signal"
        ]
        assert signals
        assert all("не является доказательством" in item["limitations"] for item in signals)

    def test_mixed_reviews_are_reported_as_mixed(self, client, auth_headers):
        product = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={"name": "Разные мнения", "description": "Описание товара."},
        ).json()
        _upload_document(
            client,
            auth_headers,
            product["id"],
            name="reviews.csv",
            text=(
                "date,rating,text\n"
                '2024-05-03,2,"Не соответствует описанию, заряд хватает ненадолго."\n'
                '2024-05-11,5,"Полностью соответствует описанию, рекомендую."\n'
            ),
        )
        _run_analysis(client, auth_headers, product["id"])
        findings = _findings(client, auth_headers, product["id"])
        assert any(
            finding["finding_type"] == "review_signal" for finding in findings
        )

    def test_document_for_another_model_is_flagged(self, client, auth_headers):
        product = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "name": "Документ другой модели",
                "description": "Описание товара.",
                "attributes": {"model": "TEST-1"},
            },
        ).json()
        _upload_document(
            client,
            auth_headers,
            product["id"],
            name="passport.txt",
            text="Документ: паспорт изделия\nОбласть применения: модель OTHER-9\n",
            applies_to_model="OTHER-9",
        )
        _run_analysis(client, auth_headers, product["id"])
        findings = _findings(client, auth_headers, product["id"])
        scope = [
            finding
            for finding in findings
            if finding["finding_type"] == "document_scope_mismatch"
        ]
        assert scope, "Ожидается предупреждение об области применения документа"
        assert "OTHER-9" in scope[0]["description"]

    def test_ambiguous_promise_is_flagged(self, client, auth_headers):
        product = client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "name": "Абсолютное обещание",
                "description": "Подходит всем и полностью безопасен для детей.",
            },
        ).json()
        _run_analysis(client, auth_headers, product["id"])
        findings = _findings(client, auth_headers, product["id"])
        assert any(
            finding["finding_type"] == "ambiguous_claim" for finding in findings
        )


class TestReviewWorkflow:
    def test_status_change_creates_history_entry(self, client, auth_headers, product):
        _run_analysis(client, auth_headers, product["id"])
        findings = _findings(client, auth_headers, product["id"])
        assert findings
        finding_id = findings[0]["id"]

        response = client.patch(
            f"/api/v1/findings/{finding_id}",
            headers=auth_headers,
            json={"status": "in_review", "comment": "Проверяем у поставщика"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "in_review"

        history = client.get(
            f"/api/v1/findings/{finding_id}/history", headers=auth_headers
        ).json()
        assert len(history) == 1
        assert history[0]["previous_status"] == "open"
        assert history[0]["new_status"] == "in_review"
        assert history[0]["comment"] == "Проверяем у поставщика"

    def test_invalid_status_is_rejected(self, client, auth_headers, product):
        _run_analysis(client, auth_headers, product["id"])
        finding_id = _findings(client, auth_headers, product["id"])[0]["id"]
        response = client.patch(
            f"/api/v1/findings/{finding_id}",
            headers=auth_headers,
            json={"status": "invented_status"},
        )
        assert response.status_code == 422

    def test_workspace_history_is_available(self, client, auth_headers, product):
        _run_analysis(client, auth_headers, product["id"])
        finding_id = _findings(client, auth_headers, product["id"])[0]["id"]
        client.patch(
            f"/api/v1/findings/{finding_id}",
            headers=auth_headers,
            json={"status": "resolved", "comment": "Исправлено"},
        )
        history = client.get("/api/v1/reviews/history", headers=auth_headers).json()
        assert history
        assert history[0]["new_status"] == "resolved"


class TestAnalysisRuns:
    def test_run_history_is_kept(self, client, auth_headers, product):
        _run_analysis(client, auth_headers, product["id"])
        _run_analysis(client, auth_headers, product["id"])
        runs = client.get(
            f"/api/v1/products/{product['id']}/analysis-runs", headers=auth_headers
        ).json()
        assert len(runs) == 2
        assert all(run["status"] == "completed" for run in runs)
        assert runs[0]["limitations"]

    def test_run_detail_contains_findings_and_summary(self, client, auth_headers, product):
        run = _run_analysis(client, auth_headers, product["id"])
        detail = client.get(f"/api/v1/analysis-runs/{run['id']}", headers=auth_headers).json()
        assert detail["product_name"] == product["name"]
        assert "findings_total" in detail["summary"]
        assert detail["summary"]["external_service_used"] is False

    def test_claims_can_be_edited_and_confirmed(self, client, auth_headers, product):
        _run_analysis(client, auth_headers, product["id"])
        claims = client.get(
            f"/api/v1/products/{product['id']}/claims", headers=auth_headers
        ).json()
        assert claims
        claim_id = claims[0]["id"]
        response = client.patch(
            f"/api/v1/claims/{claim_id}",
            headers=auth_headers,
            json={"claim_type": "numeric_performance", "user_confirmed": True},
        )
        assert response.status_code == 200
        assert response.json()["user_confirmed"] is True

    def test_evidence_is_linked_to_claims(self, client, auth_headers, product):
        _run_analysis(client, auth_headers, product["id"])
        evidence = client.get(
            f"/api/v1/products/{product['id']}/evidence", headers=auth_headers
        ).json()
        assert evidence
        assert all(item["excerpt"] for item in evidence)
        assert any(item["relation"] == "contradicts" for item in evidence)


class TestReport:
    def test_report_contains_disclaimer_and_sources(self, client, auth_headers, product):
        _upload_document(client, auth_headers, product["id"])
        run = _run_analysis(client, auth_headers, product["id"])
        response = client.get(
            f"/api/v1/products/{product['id']}/reports/{run['id']}", headers=auth_headers
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        body = response.text
        assert "не является юридическим заключением" in body
        assert "ДЕМО-СЕРТИФИКАТ" in body or "doc.txt" in body
        assert "Ограничения анализа" in body
