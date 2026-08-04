"""Swagger / OpenAPI spec parsing.

Fetches an OpenAPI (or Swagger 2.0) spec from a URL — YAML or JSON —
and converts it into structured markdown so endpoints, parameters,
request bodies and schemas become retrievable documentation.
"""

import json
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml
from llama_index.core import Document

# Methods we document as endpoints; everything else (e.g. "parameters") is skipped.
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _validate_url(url: str) -> str:
    """Validate and normalise a URL, raising ValueError if invalid."""
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid URL scheme: {parsed.scheme or 'none'}. "
            "Only HTTP and HTTPS URLs are supported."
        )
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}. Missing domain.")
    return url


def _fetch_spec(url: str) -> dict[str, Any]:
    """Download and parse a spec URL into a dict (JSON or YAML).

    Raises:
        ValueError: For invalid URLs or unrecognisable spec formats.
        RuntimeError: For HTTP errors or parse failures.
    """
    _validate_url(url)
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 404:
            raise RuntimeError(
                f"Spec not found at: {url}. Check the URL and try again."
            ) from exc
        if status == 403:
            raise RuntimeError(
                f"Access denied for: {url}. The server may require authentication."
            ) from exc
        raise RuntimeError(
            f"HTTP {status} when fetching spec from: {url}"
        ) from exc
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Could not connect to: {url}. Check your network and the URL."
        ) from exc

    text = resp.text.strip()
    if not text:
        raise RuntimeError(f"Empty response from: {url}")

    # Try JSON first (more reliable for large specs), then YAML.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        result = yaml.safe_load(text)
        if not isinstance(result, dict):
            raise RuntimeError(
                f"Invalid YAML/JSON structure from: {url}. "
                "Expected an OpenAPI spec object."
            )
        return result
    except yaml.YAMLError as exc:
        raise RuntimeError(
            f"Could not parse spec from: {url}. Not valid JSON or YAML."
        ) from exc


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
            "file_type": "markdown",  # Converted content is markdown, not code.
            "source_type": "openapi",
            "title": title,
            "spec_version": info.get("version", "unknown"),
        },
    )
    stats = {"title": title, "endpoints": endpoint_count}
    return document, stats
