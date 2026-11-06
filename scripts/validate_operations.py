#!/usr/bin/env python3
"""Validate this deploy without building it: operation signatures and asset references."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Search uv and pipx environments when pyinfra is not on sys.path.
TOOL_VENV_LIBS = (
    Path.home() / ".local/share/uv/tools/pyinfra/lib",
    Path.home() / ".local/share/pipx/venvs/pyinfra/lib",
    Path.home() / ".local/pipx/venvs/pyinfra/lib",
)


def _ensure_pyinfra_importable() -> None:
    """Make pyinfra importable however this script was invoked."""
    try:
        import pyinfra  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        return

    candidates = sorted(
        path for lib in TOOL_VENV_LIBS for path in lib.glob("python*/site-packages")
    )
    if not candidates:
        sys.exit(
            "pyinfra is not importable and no uv/pipx tool install was found.\n"
            "Install it with: uv tool install 'pyinfra>=3.10,<4'"
        )
    sys.path.insert(0, str(candidates[-1]))


_ensure_pyinfra_importable()

import jinja2  # noqa: E402
from jinja2 import meta as jinja2_meta  # noqa: E402
from pyinfra import operations  # noqa: E402
from pyinfra.api.arguments import all_global_arguments  # noqa: E402

TARGETS = [
    *sorted((REPO_ROOT / "modules").glob("*.py")),
    REPO_ROOT / "deploy.py",
    REPO_ROOT / "packages/repos.py",
]

# Whether each file operation also validates template variables.
ASSET_OPS = {"put": False, "template": True}


def _global_argument_names() -> set[str]:
    names = {"name"}
    for group in all_global_arguments():
        names |= set(group)
    return names


def _operation_calls(tree: ast.AST):
    """Yield (module_name, operation_name, node) for each `mod.op(...)` call."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "install_packages":
            yield "dnf", "packages", node
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            yield func.value.id, func.attr, node


def _literal_kwarg(node: ast.Call, name: str) -> str | None:
    """Return the value of a string-literal keyword argument, or None if absent/dynamic."""
    for kw in node.keywords:
        if kw.arg != name or not isinstance(kw.value, ast.Constant):
            continue
        if isinstance(kw.value.value, str):
            return kw.value.value
    return None


def _check_asset(
    node: ast.Call,
    op_name: str,
    params,
    global_args: set[str],
    rel,
    errors: list[str],
) -> None:
    """Check a files.put/files.template call's src exists and template vars are provided."""
    src = _literal_kwarg(node, "src")
    if src is None:  # non-literal src (none in this repo); nothing to resolve statically
        return

    src_path = REPO_ROOT / src
    if not src_path.is_file():
        errors.append(f"{rel}:{node.lineno}: files.{op_name}() src not found: {src}")
        return

    if not ASSET_OPS[op_name]:  # files.put — no template variables to validate
        return

    referenced = jinja2_meta.find_undeclared_variables(
        jinja2.Environment().parse(src_path.read_text())
    )
    named = {p.name for p in params.values() if p.kind is not inspect.Parameter.VAR_KEYWORD}
    provided = {
        kw.arg
        for kw in node.keywords
        if kw.arg and kw.arg not in named and kw.arg not in global_args
    }
    missing = sorted(referenced - provided)
    if missing:
        errors.append(
            f"{rel}:{node.lineno}: template {src} references variable(s) {missing} "
            f"not passed by files.template(); provided: {sorted(provided)}"
        )


def main() -> int:
    global_args = _global_argument_names()
    errors: list[str] = []
    checked = 0
    assets_checked = 0

    for path in TARGETS:
        tree = ast.parse(path.read_text(), str(path))
        rel = path.relative_to(REPO_ROOT)

        for module_name, op_name, node in _operation_calls(tree):
            module = getattr(operations, module_name, None)
            if module is None:
                continue

            operation = getattr(module, op_name, None)
            if operation is None:
                errors.append(f"{rel}:{node.lineno}: no operation {module_name}.{op_name}")
                continue

            params = inspect.signature(getattr(operation, "_inner", operation)).parameters
            checked += 1

            if module_name == "files" and op_name in ASSET_OPS:
                _check_asset(node, op_name, params, global_args, rel, errors)
                assets_checked += 1

            if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
                continue

            unknown = sorted(
                kw.arg
                for kw in node.keywords
                if kw.arg and kw.arg not in params and kw.arg not in global_args
            )
            if unknown:
                errors.append(
                    f"{rel}:{node.lineno}: {module_name}.{op_name}() "
                    f"unknown argument(s) {unknown}; valid: {list(params)}"
                )

    print(
        f"checked {checked} operation calls "
        f"({assets_checked} with file/template sources) across {len(TARGETS)} files"
    )
    for error in errors:
        print(f"  {error}")
    print("FAILED" if errors else "all operation calls and asset references valid")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
