import sys
import os
from click.testing import CliRunner
from generate_fastapi_typed_routes import main

# Ensure tests directory is in path so we can import sample_app
sys.path.append(os.path.dirname(__file__))


def test_generate_routes(tmp_path):
    runner = CliRunner()
    output_file = tmp_path / "routes.py"
    tests_dir = os.path.dirname(__file__)

    # We use sample_app from the same directory
    # We must pass the directory so the subprocess can find it via PYTHONPATH
    result = runner.invoke(
        main,
        [
            "--app-module",
            "sample_app:app",
            "--output",
            str(output_file),
            "--directory",
            tests_dir,
        ],
    )

    if result.exit_code != 0:
        print(result.output)

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
    tests_dir = os.path.dirname(__file__)

    result = runner.invoke(
        main,
        [
            "--app-module",
            "sample_app:app",
            "--output",
            str(output_file),
            "--prefix",
            "my_api",
            "--directory",
            tests_dir,
        ],
    )

    if result.exit_code != 0:
        print(result.output)

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

    # Output path relative to app_dir
    output_filename = "routes_subdir.py"

    result = runner.invoke(
        main,
        [
            "--app-module",
            "my_app:app",
            "--output",
            output_filename,
            "--directory",
            str(app_dir),
        ],
    )

    if result.exit_code != 0:
        print(result.output)

    assert result.exit_code == 0

    # Check that file was created INSIDE app_dir
    expected_output = app_dir / output_filename
    assert expected_output.exists()

    content = expected_output.read_text()
    assert (
        'def app_url_path_for(name: Literal["test_route"], **path_params) -> str: ...'
        in content
    )
