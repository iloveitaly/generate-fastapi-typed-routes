# Type-Safe Route URL Generator for FastAPI

Stop guessing route names. This tool analyzes your FastAPI application and generates a typed wrapper for `url_path_for`, giving you instant autocompletion and catching typos before they hit production.

## Installation

```bash
uv add generate-fastapi-typed-routes --dev
uvx generate-fastapi-typed-routes@latest
```

## Usage

Point the tool at your FastAPI app and tell it where to save the generated code:

```bash
uvx generate-fastapi-typed-routes@latest --app-module myapp.main:app --output myapp/routes.py
```

Now, instead of using the raw `app.url_path_for`, import your generated function:

```python
from myapp.routes import app_url_path_for

# Complete with IDE autocompletion and type checking!
url = app_url_path_for("get_user_profile", user_id=123)
```

### CLI Arguments

*   `--app-module`: The import path to your FastAPI app instance (e.g., `src.main:app`). You can pass this multiple times to generate helpers for multiple apps in one file.
*   `--output`: The file path where the generated Python code will be saved.
*   `--prefix`: (Optional) Custom prefix for the generated function. Defaults to the app variable name (e.g., `app` becomes `app_url_path_for`). Use this if you have multiple apps to keep things distinct.
*   `--directory` / `-d`: (Optional) The directory containing the application module (default: current directory). Use this if your app is not in the current working directory.

## Features

*   **Zero Runtime Overhead:** The generated code is just type hints and a simple wrapper.
*   **IDE Autocompletion:** Never type a route name manually again. Your editor will list every available route name defined in your app.
*   **Refactoring Safe:** Change a route name in your app, and your type checker (mypy, pyright) will flag every place usage that needs updating.
*   **Multi-App Support:** Easily manage routes for projects with multiple FastAPI instances.

# [MIT License](LICENSE.md)
