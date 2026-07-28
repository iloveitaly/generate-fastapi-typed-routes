"""Tests for extract_routes, including include_router nesting."""

from fastapi import APIRouter, FastAPI

from generate_fastapi_typed_routes import extract_routes


def test_extract_routes_includes_nested_include_router():
    """Routes registered via include_router must be extracted.

    On FastAPI >= 0.137.0, app.routes is a tree of _IncludedRouter nodes
    rather than a flat list of APIRoute. extract_routes must still find
    nested route names (pin fastapi<0.137.0 until that walk is fixed).
    """
    app = FastAPI()
    router = APIRouter(prefix="/v1")

    @router.get("/items", name="list_items")
    def list_items():
        return []

    app.include_router(router)

    names = {r.name for r in extract_routes(app)}
    assert "list_items" in names


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
