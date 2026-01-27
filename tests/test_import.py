"""Test generate-fastapi-typed-routes."""

import generate_fastapi_typed_routes


def test_import() -> None:
    """Test that the  can be imported."""
    assert isinstance(generate_fastapi_typed_routes.__name__, str)