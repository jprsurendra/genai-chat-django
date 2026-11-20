"""Upload / download fixes: R2 (download route), R5 (dedup), M4 (chunk_count), file cleanup."""
import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from chat.models import UploadedDocument

pytestmark = pytest.mark.django_db


def _upload(client, content=b"hello world, this is a test document", name="test.txt"):
    return client.post("/api/upload", {"file": SimpleUploadedFile(name, content)}, format="multipart")


def test_upload_saves_real_chunk_count_and_hash(client_a, fake_llm, user):
    resp = _upload(client_a)
    assert resp.status_code == 200, resp.data
    doc = UploadedDocument.objects.get(id=resp.data["document_id"])
    assert doc.chunk_count == 3          # M4: real count, not "1"
    assert len(doc.file_hash) == 64
    assert "file_url" not in resp.data   # no public /media/ link any more


def test_duplicate_upload_returns_409(client_a, fake_llm):
    first = _upload(client_a)
    second = _upload(client_a, name="renamed.txt")  # same content, different name
    assert second.status_code == 409
    assert second.data["document_id"] == first.data["document_id"]
    assert UploadedDocument.objects.count() == 1


def test_same_file_by_different_users_is_allowed(client_a, client_b, fake_llm):
    assert _upload(client_a).status_code == 200
    assert _upload(client_b).status_code == 200


def test_empty_index_result_is_rejected_and_cleaned_up(client_a, fake_llm, media_root):
    fake_llm.upload_result = ("File is empty or could not be read.", 0)
    resp = _upload(client_a)
    assert resp.status_code == 422
    assert UploadedDocument.objects.count() == 0
    files = [f for _, _, fs in os.walk(media_root) for f in fs]
    assert files == []  # file removed from disk too


def test_processing_error_removes_file_from_disk(client_a, fake_llm, media_root):
    fake_llm.upload_error = RuntimeError("embedding server down")
    resp = _upload(client_a)
    assert resp.status_code == 500
    assert UploadedDocument.objects.count() == 0
    assert [f for _, _, fs in os.walk(media_root) for f in fs] == []


def test_download_route_exists_for_owner(client_a, fake_llm):
    doc_id = _upload(client_a).data["document_id"]
    resp = client_a.get(f"/api/download/{doc_id}")
    assert resp.status_code == 200      # R2: was 404 because the route was missing
    assert b"".join(resp.streaming_content) == b"hello world, this is a test document"


def test_download_is_owner_only(client_a, client_b, fake_llm):
    doc_id = _upload(client_a).data["document_id"]
    assert client_b.get(f"/api/download/{doc_id}").status_code == 404


def test_download_requires_auth(client_a, fake_llm):
    from rest_framework.test import APIClient
    doc_id = _upload(client_a).data["document_id"]
    assert APIClient().get(f"/api/download/{doc_id}").status_code == 401
