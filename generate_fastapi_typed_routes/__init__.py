"""Auto-generated typed url_path_for functions for FastAPI apps."""

import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import ModuleType

import click
from fastapi import FastAPI
from fastapi.routing import APIRoute, iter_route_contexts
from jinja2 import Template
from pydantic import BaseModel
from structlog_config import configure_logger

from .version import __version__

log = configure_logger()

MODULE_TEMPLATE = '''\
"""Auto-generated typed url_path_for functions for FastAPI apps."""

from typing import overload, Literal
from fastapi.routing import APIRoute, iter_route_contexts
from starlette.routing import NoMatchFound
{% for app_info in apps %}
from {{ app_info.import_path }} import {{ app_info.name }}
{% endfor %}

{% for app_info in apps %}
# Routes for {{ app_info.name }}
{% for route in app_info.routes %}
@overload
def {{ app_info.prefix }}_url_path_for(name: Literal["{{ route.generated_name }}"], **path_params) -> str: ...
{% endfor %}

_{{ app_info.prefix }}_route_aliases = {
{% for route in app_info.routes if route.uses_unique_id %}
    "{{ route.generated_name }}": "{{ route.unique_id }}",
{% endfor %}
}

def {{ app_info.prefix }}_url_path_for(name: str, **path_params) -> str:
    """Type-safe wrapper around {{ app_info.name }}.url_path_for() with overloads for all routes."""
    route_unique_id = _{{ app_info.prefix }}_route_aliases.get(name)
    if route_unique_id is not None:
        for route_context in iter_route_contexts({{ app_info.name }}.routes):
            route = route_context.original_route
            if (
                isinstance(route, APIRoute)
                and route_context.unique_id == route_unique_id
            ):
                return route_context.url_path_for(route.name, **path_params)
        raise NoMatchFound(name, path_params)

    return {{ app_info.name }}.url_path_for(name, **path_params)

{% endfor %}
'''


class RouteInfo(BaseModel):
    name: str
    path: str
    unique_id: str
    generated_name: str
    uses_unique_id: bool = False


class AppInfo(BaseModel):
    import_path: str
    name: str
    prefix: str
    routes: list[RouteInfo]


class DuplicateGeneratedRouteNameError(ValueError):
    """Raised when FastAPI route metadata cannot produce unique typed names."""


def _assign_generated_route_names(routes: list[RouteInfo]) -> list[RouteInfo]:
    """Use FastAPI unique IDs only when route names are ambiguous."""
    name_counts = Counter(route.name for route in routes)
    resolved_routes = []
    for route in routes:
        uses_unique_id = name_counts[route.name] > 1
        generated_name = route.unique_id if uses_unique_id else route.name
        if uses_unique_id:
            log.warning(
                "duplicate_route_name_using_unique_id",
                route_name=route.name,
                path=route.path,
                generated_name=generated_name,
            )
        resolved_routes.append(
            route.model_copy(
                update={
                    "generated_name": generated_name,
                    "uses_unique_id": uses_unique_id,
                }
            )
        )

    routes_by_generated_name: dict[str, list[RouteInfo]] = defaultdict(list)
    for route in resolved_routes:
        routes_by_generated_name[route.generated_name].append(route)

    collisions = {
        name: conflicting_routes
        for name, conflicting_routes in routes_by_generated_name.items()
        if len(conflicting_routes) > 1
    }
    if not collisions:
        return resolved_routes

    details = ["Unable to generate unique typed route names:"]
    for generated_name, conflicting_routes in sorted(collisions.items()):
        if all(route.uses_unique_id for route in conflicting_routes):
            details.append(f"Duplicate FastAPI unique ID '{generated_name}':")
        else:
            details.append(f"Generated route name collision '{generated_name}':")
        for route in sorted(conflicting_routes, key=lambda item: item.path):
            details.append(f"  - {route.name}: {route.path}")

    raise DuplicateGeneratedRouteNameError("\n".join(details))


def extract_routes(app: FastAPI) -> list[RouteInfo]:
    """Extract route information from a FastAPI app.

    Walks nested include_router trees via FastAPI's public iter_route_contexts
    (required since FastAPI 0.137.0, where app.routes is no longer a flat list
    of APIRoute objects).
    """
    routes: list[RouteInfo] = []

    for route_context in iter_route_contexts(app.routes):
        route = route_context.original_route
        if not isinstance(route, APIRoute):
            continue

        if not route.name:
            continue

        routes.append(
            RouteInfo(
                name=route.name,
                # Prefer effective path (includes prefixes from include_router)
                path=route_context.path or route.path,
                unique_id=route_context.unique_id,
                generated_name=route.name,
            )
        )

    # Sort for consistent output
    routes.sort(key=lambda route: (route.name, route.path, route.unique_id))
    routes = _assign_generated_route_names(routes)

    log.info("extracted_routes", count=len(routes))
    return routes


def load_app(app_module: str, prefix: str | None) -> AppInfo:
    """Load a FastAPI app and extract its information."""
    try:
        if ":" not in app_module:
            raise ValueError(f"Invalid format '{app_module}', expected 'module:app'")

        module_path, app_name = app_module.split(":")
        module: ModuleType = __import__(module_path, fromlist=[app_name])

        if not hasattr(module, app_name):
            raise AttributeError(
                f"Module '{module_path}' has no attribute '{app_name}'"
            )

        app = getattr(module, app_name)

        if not isinstance(app, FastAPI):
            raise TypeError(f"{app_module} is not a FastAPI app")

        log.info("app_loaded", module=module_path, app=app_name)

        routes = extract_routes(app)

        # Determine prefix - default to app_name if not provided
        if prefix is None:
            prefix = app_name
            log.info("using_default_prefix", prefix=prefix)

        return AppInfo(
            import_path=module_path,
            name=app_name,
            prefix=prefix,
            routes=routes,
        )
    except (ImportError, AttributeError, ValueError, TypeError) as e:
        raise click.ClickException(
            f"Error loading application '{app_module}': {e}"
        ) from e


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
@click.version_option(version=__version__, prog_name="generate-fastapi-typed-routes")
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

    # Add directory to sys.path so we can import the app
    sys.path.insert(0, str(directory.resolve()))

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

        # Load all apps
        apps_info = []
        for app_mod, app_prefix in zip(app_module, prefixes, strict=True):
            app_info = load_app(app_mod, app_prefix)
            apps_info.append(app_info)

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
        log.exception("generation_failed", error=str(e))
        # If it's already a ClickException, just raise it
        if isinstance(e, click.ClickException):
            raise
        raise click.ClickException(str(e)) from e
