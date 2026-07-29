[![Release Notes](https://img.shields.io/github/release/iloveitaly/generate-fastapi-typed-routes)](https://github.com/iloveitaly/generate-fastapi-typed-routes/releases)
[![Downloads](https://static.pepy.tech/badge/generate-fastapi-typed-routes/month)](https://pepy.tech/project/generate-fastapi-typed-routes)
![GitHub CI Status](https://github.com/iloveitaly/generate-fastapi-typed-routes/actions/workflows/build_and_publish.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# Type-Safe Route URL Generator for FastAPI

Stop guessing route names. This tool analyzes your FastAPI application and generates a typed wrapper for `url_path_for`, giving you instant autocompletion and catching typos before they hit production.

[Here's an example project](https://github.com/iloveitaly/python-starter-template
) which uses it (checkout `just py_generate`)

## Installation

```bash
uv add generate-fastapi-typed-routes --dev
```

## Usage

Point the tool at your FastAPI app and tell it where to save the generated code:

```bash
generate-fastapi-typed-routes --app-module myapp.main:app --output myapp/routes.py
```

Note that since this tool needs to import an app modules you cannot run it via uvx, which runs outside of your venv.

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

### Duplicate Route Names

When multiple routes in the same FastAPI app share a route name, the generated
helper uses their FastAPI unique IDs instead:

```python
app_url_path_for("list_items_first_items_get")
app_url_path_for("list_items_second_items_get")
```

Routes whose names are already unique keep their shorter names. If FastAPI's
unique IDs still cannot distinguish the conflicting routes, generation fails
with an error listing the colliding routes and does not write the output file.

## Features

*   **Minimal Runtime Overhead:** Unique route names delegate directly to FastAPI; only automatically qualified duplicate names require route lookup.
*   **IDE Autocompletion:** Never type a route name manually again. Your editor will list every available route name defined in your app.
*   **Refactoring Safe:** Change a route name in your app, and your type checker (mypy, pyright) will flag every place usage that needs updating.
*   **Multi-App Support:** Easily manage routes for projects with multiple FastAPI instances.

# [MIT License](LICENSE.md)

---

*This project was created from [iloveitaly/python-package-template](https://github.com/iloveitaly/python-package-template)*
