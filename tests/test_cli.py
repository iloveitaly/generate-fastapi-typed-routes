import sys
import os
from click.testing import CliRunner
from generate_fastapi_typed_routes import main

# Ensure tests directory is in path so we can import sample_app
sys.path.append(os.path.dirname(__file__))


def test_generate_routes(tmp_path):
    runner = CliRunner()
    output_file = tmp_path / "routes.py"

    # We use sample_app from the same directory
    # 'sample_app:app' assumes sample_app.py is in the python path.

    result = runner.invoke(
        main, ["--app-module", "sample_app:app", "--output", str(output_file)]
    )

    assert result.exit_code == 0
    assert output_file.exists()

    content = output_file.read_text()
    assert "from sample_app import app" in content
    assert (
        'def app_url_path_for(name: Literal["create_user"], **path_params) -> str: ...'
        in content
    )
    assert (
        'def app_url_path_for(name: Literal["get_item"], **path_params) -> str: ...'
        in content
    )


def test_generate_routes_with_prefix(tmp_path):
    runner = CliRunner()
    output_file = tmp_path / "routes_custom.py"

    result = runner.invoke(
        main,
        [
            "--app-module",
            "sample_app:app",
            "--output",
            str(output_file),
            "--prefix",
            "my_api",
        ],
    )

    assert result.exit_code == 0
    content = output_file.read_text()
    assert (
        'def my_api_url_path_for(name: Literal["create_user"], **path_params) -> str: ...'
        in content
    )


def test_generate_routes_custom_directory(tmp_path):
    runner = CliRunner()
    app_dir = tmp_path / "subdir"
    app_dir.mkdir()
    (app_dir / "__init__.py").touch()
    (app_dir / "my_app.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/test', name='test_route')\ndef test(): pass"
    )

    output_file = tmp_path / "routes_subdir.py"

    result = runner.invoke(
        main,
        [
            "--app-module",
            "my_app:app",
            "--output",
            str(output_file),
            "--directory",
            str(app_dir),
        ],
    )

    assert result.exit_code == 0
    content = output_file.read_text()
    assert (
        'def app_url_path_for(name: Literal["test_route"], **path_params) -> str: ...'
        in content
    )
