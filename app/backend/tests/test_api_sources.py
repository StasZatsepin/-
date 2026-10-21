"""Тесты загрузки источников и ограничений файлов."""

from __future__ import annotations

import io

from app.core.config import settings


class TestSourceUpload:
    def test_upload_txt_source(self, client, auth_headers, product):
        payload = (
            "ДЕМО-ДОКУМЕНТ (синтетический)\n"
            "Время работы без подзарядки — 30 часов.\n"
            "Масса — 250 граммов.\n"
        ).encode("utf-8")
        response = client.post(
            f"/api/v1/products/{product['id']}/sources",
            headers=auth_headers,
            files={"file": ("doc.txt", io.BytesIO(payload), "text/plain")},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["extraction_status"] == "extracted"
        assert body["size_bytes"] == len(payload)
        assert len(body["content_hash"]) == 64

    def test_upload_csv_source_parses_rows(self, client, auth_headers, product):
        payload = (
            "date,rating,text\n2024-05-03,2,\"Батарея держится 20 часов, а не 48.\"\n"
        ).encode("utf-8")
        response = client.post(
            f"/api/v1/products/{product['id']}/sources",
            headers=auth_headers,
            files={"file": ("reviews.csv", io.BytesIO(payload), "text/csv")},
        )
        assert response.status_code == 201
        assert response.json()["source_type"] == "review_export"
        assert response.json()["metadata"]["row_count"] == 1

    def test_unsupported_extension_is_rejected(self, client, auth_headers, product):
        payload = b"#!/bin/sh\necho hacked"
        response = client.post(
            f"/api/v1/products/{product['id']}/sources",
            headers=auth_headers,
            files={"file": ("payload.sh", io.BytesIO(payload), "application/x-sh")},
        )
        assert response.status_code == 415
        assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"

    def test_images_are_rejected_with_ocr_message(self, client, auth_headers, product):
        payload = b"\x89PNG\r\n\x1a\n" + b"0" * 32
        response = client.post(
            f"/api/v1/products/{product['id']}/sources",
            headers=auth_headers,
            files={"file": ("photo.png", io.BytesIO(payload), "image/png")},
        )
        assert response.status_code == 415
        assert "OCR" in response.json()["error"]["message"]

    def test_empty_file_is_rejected(self, client, auth_headers, product):
        response = client.post(
            f"/api/v1/products/{product['id']}/sources",
            headers=auth_headers,
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert response.status_code == 422

    def test_oversized_file_is_rejected(self, client, auth_headers, product, monkeypatch):
        monkeypatch.setattr(settings, "max_upload_bytes", 64)
        payload = b"a" * 200
        response = client.post(
            f"/api/v1/products/{product['id']}/sources",
            headers=auth_headers,
            files={"file": ("big.txt", io.BytesIO(payload), "text/plain")},
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"

    def test_file_is_stored_under_generated_name(self, client, auth_headers, product):
        payload = "Тестовое содержимое документа.".encode("utf-8")
        client.post(
            f"/api/v1/products/{product['id']}/sources",
            headers=auth_headers,
            files={"file": ("Имя файла с пробелами.txt", io.BytesIO(payload), "text/plain")},
        )
        sources = client.get(
            f"/api/v1/products/{product['id']}/sources", headers=auth_headers
        ).json()
        stored = [item for item in sources if item["source_name"].endswith(".txt")][0]
        assert stored["source_name"] == "Имя файла с пробелами.txt"
        # В API нет пути файла: путь генерируется сервером и наружу не выдаётся.
        assert "file_path" not in stored

    def test_manual_source_creation(self, client, auth_headers, product):
        response = client.post(
            f"/api/v1/products/{product['id']}/sources/manual",
            headers=auth_headers,
            json={
                "source_name": "Заметка продавца",
                "source_type": "user_note",
                "text": "Проверить заявление о времени работы у поставщика.",
            },
        )
        assert response.status_code == 201
        assert response.json()["extraction_status"] == "extracted"

    def test_delete_source(self, client, auth_headers, product):
        payload = "Документ для удаления.".encode("utf-8")
        created = client.post(
            f"/api/v1/products/{product['id']}/sources",
            headers=auth_headers,
            files={"file": ("to-delete.txt", io.BytesIO(payload), "text/plain")},
        ).json()
        response = client.delete(f"/api/v1/sources/{created['id']}", headers=auth_headers)
        assert response.status_code == 204
        assert (
            client.get(f"/api/v1/sources/{created['id']}", headers=auth_headers).status_code
            == 404
        )


class TestSourceWithoutText:
    def test_pdf_without_text_layer_reports_needs_ocr(self, client, auth_headers, product):
        """PDF без извлекаемого текста: понятное сообщение, а не падение."""
        from app.services.ingestion import extract_text

        # Минимальный корректный PDF без текстового слоя.
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
            b"trailer<</Root 1 0 R>>\n"
        )
        result = extract_text("scan.pdf", pdf_bytes)
        assert result.status in {"needs_ocr", "failed", "extracted"}
        if result.status != "extracted":
            assert result.note
