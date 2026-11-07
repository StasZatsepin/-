"""Флаг STORE_ORIGINAL_FILES: оригиналы файлов на диск пишутся только при включённом флаге."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.core.config import settings
from app.services import ingestion

PAYLOAD = (
    "ДЕМО-ДОКУМЕНТ (синтетический)\n"
    "Время работы без подзарядки — 30 часов.\n"
    "Масса — 250 граммов.\n"
).encode("utf-8")


@pytest.fixture()
def storage(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path)
    return tmp_path


def _files_on_disk(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


class TestStoreFileFunction:
    def test_writes_file_when_enabled(self, storage, monkeypatch):
        monkeypatch.setattr(settings, "store_original_files", True)
        path = ingestion.store_file("product-1", ".txt", PAYLOAD)
        assert path is not None
        assert Path(path).read_bytes() == PAYLOAD
        assert len(_files_on_disk(storage)) == 1

    def test_writes_nothing_when_disabled(self, storage, monkeypatch):
        monkeypatch.setattr(settings, "store_original_files", False)
        assert ingestion.store_file("product-1", ".txt", PAYLOAD) is None
        assert _files_on_disk(storage) == []

    def test_delete_file_accepts_none(self):
        ingestion.delete_file(None)


class TestUploadApi:
    def _upload(self, client, auth_headers, product):
        return client.post(
            f"/api/v1/products/{product['id']}/sources",
            headers=auth_headers,
            files={"file": ("doc.txt", io.BytesIO(PAYLOAD), "text/plain")},
        )

    def test_upload_keeps_file_when_enabled(self, client, auth_headers, product, storage, monkeypatch):
        monkeypatch.setattr(settings, "store_original_files", True)
        response = self._upload(client, auth_headers, product)
        assert response.status_code == 201, response.text
        assert len(_files_on_disk(storage)) == 1

    def test_upload_without_disk_still_extracts_text(
        self, client, auth_headers, product, storage, monkeypatch
    ):
        monkeypatch.setattr(settings, "store_original_files", False)
        response = self._upload(client, auth_headers, product)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["extraction_status"] == "extracted"
        assert body["size_bytes"] == len(PAYLOAD)
        assert len(body["content_hash"]) == 64
        assert _files_on_disk(storage) == []

    def test_source_without_file_can_be_deleted(
        self, client, auth_headers, product, storage, monkeypatch
    ):
        monkeypatch.setattr(settings, "store_original_files", False)
        source_id = self._upload(client, auth_headers, product).json()["id"]
        response = client.delete(f"/api/v1/sources/{source_id}", headers=auth_headers)
        assert response.status_code == 204, response.text

    def test_analysis_works_without_stored_file(
        self, client, auth_headers, product, storage, monkeypatch
    ):
        monkeypatch.setattr(settings, "store_original_files", False)
        assert self._upload(client, auth_headers, product).status_code == 201
        response = client.post(
            f"/api/v1/products/{product['id']}/analysis-runs", headers=auth_headers
        )
        assert response.status_code == 201, response.text

    def test_settings_endpoint_reports_the_flag(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "store_original_files", False)
        body = client.get("/api/v1/settings/ai", headers=auth_headers).json()
        assert body["limits"]["store_original_files"] is False
