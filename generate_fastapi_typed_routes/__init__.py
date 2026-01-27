"""Auto-generated typed url_path_for functions for FastAPI apps."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import click
from jinja2 import Template
from pydantic import BaseModel
from structlog_config import configure_logger

log = configure_logger()

MODULE_TEMPLATE = '''\
"""Auto-generated typed url_path_for functions for FastAPI apps."""

from typing import overload, Literal
{% for app_info in apps %}
from {{ app_info.import_path }} import {{ app_info.name }}
{% endfor %}

{% for app_info in apps %}
# Routes for {{ app_info.name }}
{% for route in app_info.routes %}
@overload
def {{ app_info.prefix }}_url_path_for(name: Literal["{{ route.name }}"], **path_params) -> str: ...
{% endfor %}

def {{ app_info.prefix }}_url_path_for(name: str, **path_params) -> str:
    """Type-safe wrapper around {{ app_info.name }}.url_path_for() with overloads for all routes."""
    return {{ app_info.name }}.url_path_for(name, **path_params)

{% endfor %}
'''

EXTRACTOR_SCRIPT = """
import sys
import json
import importlib
from fastapi import FastAPI
from fastapi.routing import APIRoute

def extract_routes(app_module_str):
    try:
        if ":" not in app_module_str:
             raise ValueError(f"Invalid format '{app_module_str}', expected 'module:app'")
        module_path, app_name = app_module_str.split(":")
        
        # Ensure we can import the module
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            # Try adding current directory to path if not found, though PYTHONPATH should handle this
            print(f"ImportError importing {module_path}: {e}", file=sys.stderr)
            raise

        if not hasattr(module, app_name):
            raise AttributeError(f"Module '{module_path}' has no attribute '{app_name}'")
            
        app = getattr(module, app_name)
    except Exception as e:
        # Print error but don't exit yet if we want to handle others? 
        # For now fail fast.
        print(f"Error loading {app_module_str}: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(app, FastAPI):
        print(f"{app_module_str} is not a FastAPI app", file=sys.stderr)
        sys.exit(1)

    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute) and route.name:
            routes.append({
                "name": route.name,
                "path": route.path
            })
    # Sort by name
    routes.sort(key=lambda x: x["name"])
    
    return {
        "import_path": module_path,
        "name": app_name,
        "routes": routes
    }

def main():
    app_modules = sys.argv[1:]
    results = []
    for app_mod in app_modules:
        info = extract_routes(app_mod)
        results.append(info)
    
    print(json.dumps(results))

if __name__ == "__main__":
    main()
"""


class RouteInfo(BaseModel):
    name: str
    path: str


class AppInfo(BaseModel):
    import_path: str
    name: str
    prefix: str
    routes: list[RouteInfo]


def get_apps_info(
    app_modules: tuple[str, ...], prefixes: list[str | None], directory: Path
) -> list[AppInfo]:
    """Load FastAPI apps and extract information using a subprocess."""

    # Prepare environment for subprocess
    env = os.environ.copy()
    # Add directory to PYTHONPATH so imports work
    current_pythonpath = env.get("PYTHONPATH", "")
    directory_str = str(directory.resolve())
    env["PYTHONPATH"] = (
        f"{directory_str}{os.pathsep}{current_pythonpath}"
        if current_pythonpath
        else directory_str
    )

    cmd = [sys.executable, "-c", EXTRACTOR_SCRIPT, *app_modules]

    log.info(
        "running_subprocess",
        cmd=cmd,
        directory=directory_str,
    )

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=False,  # We handle return code manually
        )
    except Exception as e:
        raise click.ClickException(f"Failed to execute extractor subprocess: {e}")

    if result.returncode != 0:
        error_msg = result.stderr.strip()
        log.error("subprocess_failed", exit_code=result.returncode, stderr=error_msg)

        msg = f"Failed to extract routes.\nError: {error_msg}"
        if "ModuleNotFoundError" in error_msg or "ImportError" in error_msg:
            msg += "\n\nHint: It looks like the application module could not be found or imported."
            msg += "\nIf you are running this tool via 'uvx' or 'pipx', the application dependencies might not be available."
            msg += "\nTry running inside your project environment (e.g., 'uv run generate-fastapi-typed-routes ...')."

        raise click.ClickException(msg)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        log.error("json_decode_failed", stdout=result.stdout)
        raise click.ClickException(
            f"Failed to parse output from extractor: {result.stdout}"
        )

    apps_info = []
    for i, app_data in enumerate(data):
        import_path = app_data["import_path"]
        name = app_data["name"]
        routes_data = app_data["routes"]

        # Determine prefix
        prefix = prefixes[i]
        if prefix is None:
            prefix = name
            log.info("using_default_prefix", prefix=prefix)

        routes = [RouteInfo(**r) for r in routes_data]

        apps_info.append(
            AppInfo(
                import_path=import_path,
                name=name,
                prefix=prefix,
                routes=routes,
            )
        )

    log.info("apps_loaded", count=len(apps_info))
    return apps_info


def generate_typed_module(apps_info: list[AppInfo], output_path: Path) -> None:
    """Generate Python module with typed url_path_for functions."""

    log.info(
        "generating_module", output_path=str(output_path), app_count=len(apps_info)
    )

    # Render the template
    template = Template(MODULE_TEMPLATE)
    output = template.render(apps=apps_info)

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(output)

    total_routes = sum(len(app.routes) for app in apps_info)
    log.info(
        "module_generated", output_path=str(output_path), total_routes=total_routes
    )


@click.command()
@click.option(
    "--app-module",
    multiple=True,
    required=True,
    help="Python module path to FastAPI app (e.g., 'myapp.main:api_app'). Can be specified multiple times.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output path for the generated module (required)",
)
@click.option(
    "--prefix",
    multiple=True,
    default=None,
    help="Prefix for the generated function (default: uses app variable name). Should match order of --app-module.",
)
@click.option(
    "--directory",
    "-d",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=".",
    help="Directory containing the application module (default: current directory).",
)
def main(
    app_module: tuple[str, ...],
    output: Path,
    prefix: tuple[str, ...] | None,
    directory: Path,
) -> None:
    """Generate typed url_path_for functions for FastAPI applications."""

    log.info(
        "starting_generation",
        app_modules=app_module,
        output=str(output),
        directory=str(directory),
    )

    # Resolve output path relative to directory
    # Note: If directory is provided, output path is likely meant to be relative to it,
    # OR it's an absolute path.
    # The original implementation did: output = directory / output
    # We will preserve that behavior for consistency.
    output = directory / output

    try:
        # Parse prefixes - if provided, must match number of apps
        prefixes: list[str | None] = (
            list(prefix) if prefix else [None] * len(app_module)
        )

        if len(prefixes) != len(app_module):
            raise click.ClickException(
                f"Number of prefixes ({len(prefixes)}) must match number of app modules ({len(app_module)})"
            )

        # Load all apps and extract routes using subprocess
        apps_info = get_apps_info(app_module, prefixes, directory)

        # Generate module
        generate_typed_module(apps_info, output)

        # Post-generation formatting with Ruff
        ruff_path = shutil.which("ruff")
        if ruff_path:
            click.secho(f"Reformatting {output} with Ruff...", fg="green")
            subprocess.run(
                [ruff_path, "format", str(output)], check=False, capture_output=True
            )
            subprocess.run(
                [ruff_path, "check", "--fix", str(output)],
                check=False,
                capture_output=True,
            )

        click.secho(f"Successfully generated typed routes at: {output}", fg="green")

    except Exception as e:
        log.error("generation_failed", error=str(e), exc_info=True)
        # If it's already a ClickException, just raise it
        if isinstance(e, click.ClickException):
            raise
        raise click.ClickException(str(e))
