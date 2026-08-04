"""Swagger / OpenAPI spec parsing.

Fetches an OpenAPI (or Swagger 2.0) spec from a URL — YAML or JSON —
and converts it into structured markdown so endpoints, parameters,
request bodies and schemas become retrievable documentation.
"""

import json
from typing import Any

import httpx
import yaml
from llama_index.core import Document

# Methods we document as endpoints; everything else (e.g. "parameters") is skipped.
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _fetch_spec(url: str) -> dict[str, Any]:
    """Download and parse a spec URL into a dict (JSON or YAML)."""
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
    text = resp.text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return yaml.safe_load(text)


def _schema_name(ref: str | None) -> str | None:
    """Extract the last component of a `$ref` like '#/components/schemas/Pet'."""
    if not ref:
        return None
    return ref.split("/")[-1]


def openapi_to_markdown(spec: dict[str, Any]) -> str:
    """Convert a parsed OpenAPI spec dict into documentation markdown."""
    parts: list[str] = []

    # --- Header from the `info` block ---
    info = spec.get("info", {})
    parts.append(f"# {info.get('title', 'API Documentation')}\n")
    parts.append(f"**Version:** {info.get('version', 'unknown')}\n")
    if info.get("description"):
        parts.append(f"{info['description']}\n")

    # --- Paths / operations ---
    paths = spec.get("paths", {})
    if paths:
        parts.append("## Endpoints\n")
        for path, methods in paths.items():
            for method, details in methods.items():
                if method not in HTTP_METHODS or not isinstance(details, dict):
                    continue
                parts.append(f"### {method.upper()} `{path}`\n")
                if details.get("summary"):
                    parts.append(f"**Summary:** {details['summary']}\n")
                if details.get("description"):
                    parts.append(f"{details['description']}\n")

                # Path / query / header parameters.
                parameters = details.get("parameters", [])
                if parameters:
                    parts.append("**Parameters:**\n")
                    for p in parameters:
                        name = p.get("name", "?")
                        where = p.get("in", "?")
                        required = "required" if p.get("required") else "optional"
                        schema = p.get("schema", {})
                        ptype = schema.get("type", "any")
                        desc = p.get("description", "")
                        parts.append(f"- `{name}` ({where}, {ptype}, {required}): {desc}\n")

                # Request body (may reference a schema by $ref).
                request_body = details.get("requestBody", {})
                if request_body:
                    parts.append("**Request Body:**\n")
                    content = request_body.get("content", {})
                    for media_type, media_info in content.items():
                        ref = media_info.get("schema", {}).get("$ref")
                        schema_name = _schema_name(ref)
                        label = schema_name or "object"
                        parts.append(f"- Content-Type `{media_type}` → `{label}`\n")

                # Response codes + schema refs.
                responses = details.get("responses", {})
                if responses:
                    parts.append("**Responses:**\n")
                    for status, resp in responses.items():
                        desc = resp.get("description", "")
                        content = resp.get("content", {})
                        schema_label = ""
                        for media_info in content.values():
                            ref = media_info.get("schema", {}).get("$ref")
                            name = _schema_name(ref)
                            if name:
                                schema_label = f" → `{name}`"
                                break
                        parts.append(f"- `{status}`: {desc}{schema_label}\n")

    # --- Data models / schemas ---
    schemas = spec.get("components", {}).get("schemas", {})
    if not schemas:
        # Swagger 2.0 stores definitions at the top level.
        schemas = spec.get("definitions", {})
    if schemas:
        parts.append("## Data Models\n")
        for name, schema in schemas.items():
            parts.append(f"### {name}\n")
            if schema.get("description"):
                parts.append(f"{schema['description']}\n")
            properties = schema.get("properties", {})
            for prop_name, prop_info in properties.items():
                ptype = prop_info.get("type", "any")
                ref = _schema_name(prop_info.get("$ref"))
                ptype = ref or ptype
                required = "required" if prop_name in schema.get("required", []) else "optional"
                desc = prop_info.get("description", "")
                parts.append(f"- `{prop_name}` ({ptype}, {required}): {desc}\n")

    return "\n".join(parts)


def parse_openapi_url(url: str) -> tuple[Document, dict]:
    """Fetch and convert an OpenAPI spec into a single Document.

    Returns:
        (Document, stats) where stats records the endpoint count etc.
    """
    spec = _fetch_spec(url)
    markdown = openapi_to_markdown(spec)

    info = spec.get("info", {})
    title = info.get("title", url)
    endpoint_count = sum(
        1
        for methods in spec.get("paths", {}).values()
        for method in methods
        if method in HTTP_METHODS
    )

    document = Document(
        text=markdown,
        metadata={
            "file_path": url,
            "source_type": "openapi",
            "title": title,
            "spec_version": info.get("version", "unknown"),
        },
    )
    stats = {"title": title, "endpoints": endpoint_count}
    return document, stats
