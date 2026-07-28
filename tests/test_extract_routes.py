"""Tests for extract_routes, including include_router nesting."""

import os
import sys

from click.testing import CliRunner
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from generate_fastapi_typed_routes import extract_routes, main

# Ensure tests directory is in path so we can import sample modules
sys.path.append(os.path.dirname(__file__))


def test_extract_routes_includes_nested_include_router():
    """Routes registered via include_router must be extracted.

    FastAPI >= 0.137.0 keeps include_router mounts as a tree of
    _IncludedRouter nodes; extract_routes must walk them via
    iter_route_contexts (required by fastapi>=0.137.0).
    """
    app = FastAPI()
    router = APIRouter(prefix="/v1")

    @router.get("/items", name="list_items")
    def list_items():
        return []

    app.include_router(router)

    names = {r.name for r in extract_routes(app)}
    assert "list_items" in names


def test_app_routes_contain_included_router_not_flat_apiroute():
    """Nested routes are not top-level APIRoute under fastapi>=0.137.0."""
    app = FastAPI()
    router = APIRouter()

    @router.get("/x", name="nested_x")
    def nested_x():
        return {}

    app.include_router(router)

    top_level_api_routes = [r for r in app.routes if isinstance(r, APIRoute)]
    assert all(getattr(r, "name", None) != "nested_x" for r in top_level_api_routes)

    included = [r for r in app.routes if type(r).__name__ == "_IncludedRouter"]
    assert len(included) >= 1


def test_extract_routes_direct_and_included():
    app = FastAPI()

    @app.get("/direct", name="direct")
    def direct():
        return {"ok": True}

    router = APIRouter()

    @router.get("/nested", name="nested")
    def nested():
        return {"ok": True}

    app.include_router(router)

    names = {r.name for r in extract_routes(app)}
    assert names >= {"direct", "nested"}


def test_extract_routes_respects_include_prefix():
    app = FastAPI()
    router = APIRouter()

    @router.get("/users", name="users")
    def users():
        return []

    app.include_router(router, prefix="/api")

    routes = {r.name: r.path for r in extract_routes(app)}
    assert routes["users"] == "/api/users"


def test_extract_routes_multi_level_include():
    leaf = APIRouter()

    @leaf.get("/deep", name="deep")
    def deep():
        return {}

    mid = APIRouter(prefix="/mid")
    mid.include_router(leaf)

    app = FastAPI()
    app.include_router(mid, prefix="/outer")

    names = {r.name for r in extract_routes(app)}
    assert "deep" in names

    routes = {r.name: r.path for r in extract_routes(app)}
    assert routes["deep"] == "/outer/mid/deep"


def test_extract_routes_after_include_still_visible():
    """Routes added to a router after include_router must still be found."""
    app = FastAPI()
    router = APIRouter()
    app.include_router(router)

    @router.get("/late", name="late_route")
    def late():
        return {}

    names = {r.name for r in extract_routes(app)}
    assert "late_route" in names


def test_generate_typed_module_includes_nested_route_names(tmp_path):
    """End-to-end: generated overloads include include_router route names."""
    app_dir = tmp_path / "nested_app"
    app_dir.mkdir()
    (app_dir / "__init__.py").touch()
    (app_dir / "main.py").write_text(
        """\
from fastapi import APIRouter, FastAPI

app = FastAPI()
api = APIRouter(prefix="/internal/v1")

@api.get("/users", name="user_list")
def user_list():
    return []

@api.get("/health", name="healthcheck")
def healthcheck():
    return {"ok": True}

app.include_router(api)

@app.get("/top", name="top_level")
def top_level():
    return {"top": True}
"""
    )

    runner = CliRunner()
    output_file = "routes.py"
    result = runner.invoke(
        main,
        [
            "--app-module",
            "main:app",
            "--output",
            output_file,
            "--directory",
            str(app_dir),
        ],
    )

    if result.exit_code != 0:
        print(result.output)

    assert result.exit_code == 0
    content = (app_dir / output_file).read_text()
    assert 'Literal["user_list"]' in content
    assert 'Literal["healthcheck"]' in content
    assert 'Literal["top_level"]' in content
