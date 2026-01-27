# generate-fastapi-typed-routes

Auto-generated typed `url_path_for` functions for FastAPI apps.

This tool generates a Python module containing a type-safe wrapper around `FastAPI.url_path_for`, providing autocompletion and type checking for your route names.

## Installation

```bash
uv tool install generate-fastapi-typed-routes
```

## Usage

```bash
generate-fastapi-typed-routes --app-module myapp.main:app --output myapp/routes.py
```

### Arguments

*   `--app-module`: Python module path to your FastAPI app (e.g., `myapp.main:app`). Can be specified multiple times to include routes from multiple apps.
*   `--output`: Output path for the generated module.
*   `--prefix`: (Optional) Prefix for the generated function names. Defaults to the app variable name (e.g., `app_url_path_for`).

### Example

Given a FastAPI app:

```python
# myapp/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}", name="get_item")
def read_item(item_id: int):
    ...
```

Run the generator:

```bash
generate-fastapi-typed-routes --app-module myapp.main:app --output myapp/routes.py
```

The generated `myapp/routes.py` will contain:

```python
from typing import overload, Literal
from myapp.main import app

@overload
def app_url_path_for(name: Literal["get_item"], **path_params) -> str: ...

def app_url_path_for(name: str, **path_params) -> str:
    """Type-safe wrapper around app.url_path_for() with overloads for all routes."""
    return app.url_path_for(name, **path_params)
```

Now you can use it in your code with type safety:

```python
from myapp.routes import app_url_path_for

url = app_url_path_for("get_item", item_id=42)
```

## Development

This project uses `uv` for dependency management and `just` for command running.

```bash
just setup
just test
just lint
```
