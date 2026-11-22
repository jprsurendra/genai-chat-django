"""Phase A (010.2): self-hosted frontend libraries + Content-Security-Policy."""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command

TEMPLATES_DIR = Path(settings.BASE_DIR) / "templates"


@pytest.mark.parametrize("url", ["/login/", "/"])
def test_pages_send_strict_csp(client, url):
    resp = client.get(url)
    assert resp.status_code == 200
    csp = resp.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "unsafe-inline" not in csp
    assert "frame-ancestors 'none'" in csp


def test_templates_load_nothing_from_external_hosts():
    """All JS/CSS must come from static/vendor (no CDN = no supply-chain or availability risk)."""
    for tpl in TEMPLATES_DIR.rglob("*.html"):
        html = tpl.read_text()
        assert not re.search(r"""(src|href)=["']https?://""", html), f"external asset in {tpl}"


def test_templates_have_no_inline_scripts_or_styles():
    """Inline code would be blocked by the CSP, so it must not exist."""
    for tpl in TEMPLATES_DIR.rglob("*.html"):
        html = tpl.read_text()
        assert "<style" not in html, f"inline <style> in {tpl}"
        assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html), f"inline <script> in {tpl}"
        assert not re.search(r"""\sstyle=["']""", html), f"style attribute in {tpl}"
        assert not re.search(r"""\son[a-z]+=["']""", html), f"inline event handler in {tpl}"


def test_collectstatic_with_manifest_storage(settings, tmp_path):
    """Production storage must resolve every url()/sourceMappingURL reference in vendor files."""
    settings.STATIC_ROOT = tmp_path / "staticfiles"
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    call_command("collectstatic", interactive=False, verbosity=0)
    assert (tmp_path / "staticfiles" / "staticfiles.json").exists()
