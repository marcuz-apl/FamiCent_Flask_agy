"""Integration tests for view routes and template context processors."""
from __future__ import annotations


def test_docs_route_requires_login(client):
    """Verify that accessing /docs without login redirects to /login."""
    response = client.get("/docs")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_docs_route_authenticated(auth_client):
    """Verify that authenticated users can access /docs successfully."""
    response = auth_client.get("/docs")
    assert response.status_code == 200
    assert b"Documentation" in response.data
    assert b"Secure Family Finance Manager" in response.data


def test_version_context_processor(auth_client):
    """Verify that the application version is successfully injected into the context."""
    from famicent import __version__
    response = auth_client.get("/docs")
    assert response.status_code == 200
    expected_version = f"v{__version__}".encode("utf-8")
    assert expected_version in response.data
