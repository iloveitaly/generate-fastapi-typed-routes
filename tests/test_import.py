"""Test generate-fastapi-typed-routes."""

import generate_fastapi_typed_routes


def test_import() -> None:
    """Test that the package can be imported."""
    assert isinstance(generate_fastapi_typed_routes.__name__, str)


def test_version() -> None:
    """Test that the version is available."""
    assert isinstance(generate_fastapi_typed_routes.__version__, str)
