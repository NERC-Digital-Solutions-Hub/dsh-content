#!/usr/bin/env python3
"""
Generate manifest.<environment>.json files from a /pages directory using `.page` markers.

Output shape:

{
  "schemaVersion": 1,
  "version": "2026-05-08T10:47:25Z",
  "generatedAt": "2026-05-08T10:47:25Z",
  "environment": "development",
  "pages": {
    "uprn-service": {
      "route": "/apps/uprn-service",
      "assets": {
        "introduction": {
          "path": "apps/uprn-service/introduction.development.md",
          "type": "markdown"
        },
        "generated.csv.config.datasets": {
          "path": "apps/uprn-service/generated/csv/config/datasets.csv",
          "type": "csv"
        }
      }
    }
  }
}

Key rules:
- A directory is a route IFF it contains a `.page` file.
- `.page` may be empty, or may contain JSON such as: { "id": "uprn-service" }.
- Hidden files are ignored.
- Nested route directories are not included in the parent route's assets.
- A file is environment-specific if: <name>.<environment>.<ext>
  e.g. config.testing.json.
- Otherwise it is included for all environments.
- For the same asset key, environment-specific files override default files.
- Asset key = relative path under the route directory, without environment and extension,
  converted to dot notation.
  Examples:
    introduction.development.md
      -> introduction
    generated/csv/config/datasets.csv
      -> generated.csv.config.datasets
        svgs/bootstrap/info-circle.svg
            -> svgs.bootstrap.info-circle
- Each asset is emitted as:
    {
      "path": "...",
      "type": "markdown" | "json" | "csv" | "svg" | ...
    }

Outputs:
- manifest.<environment>.json for every environment in site.json["environments"]
  fallback: [site.json["currentenvironment"]] if "environments" is missing.

Run:
  python generate_manifests.py
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


PAGE_MARKER = ".page"
SCHEMA_VERSION = 1

# Keep this empty if generated assets should appear in the manifest.
# If you really want to ignore generated directories, set: {"generated"}
IGNORED_DIR_NAMES: Set[str] = set()


@dataclass(frozen=True)
class AssetDescriptor:
    path: str
    type: str


@dataclass(frozen=True)
class FileChoice:
    default_asset: Optional[AssetDescriptor]
    environment_assets: Dict[str, AssetDescriptor]


def find_repo_root(start: Path) -> Path:
    """
    Find repo root by walking up until we find site.json and pages/.
    This lets you run the script from anywhere.
    """
    p = start.resolve()

    for _ in range(30):
        if (p / "site.json").exists() and (p / "pages").is_dir():
            return p

        if p.parent == p:
            break

        p = p.parent

    raise FileNotFoundError("Could not find repo root. Expected site.json and pages/.")


REPO_ROOT = find_repo_root(Path(__file__).parent)
SITE_JSON = REPO_ROOT / "site.json"
PAGES_DIR = REPO_ROOT / "pages"


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_site_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"site.json not found at {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_environments(site: Dict[str, Any]) -> List[str]:
    environments = site.get("environments")

    if isinstance(environments, list) and environments and all(isinstance(env, str) for env in environments):
        return environments

    current_environment = site.get("currentenvironment")

    if isinstance(current_environment, str) and current_environment:
        return [current_environment]

    raise ValueError('site.json must contain "environments": [...] or "currentenvironment": "..."')


def parse_filename(filename: str, environments: List[str]) -> Tuple[str, Optional[str], str]:
    """
    Return:
      basename_without_environment_or_ext,
      environment_or_None,
      extension_without_dot

    Recognizes:
      <name>.<environment>.<ext>

    Examples:
      introduction.development.md -> ("introduction", "development", "md")
      settings.json -> ("settings", None, "json")
      archive.tar.gz -> ("archive.tar", None, "gz")
    """
    parts = filename.split(".")

    if len(parts) >= 3 and parts[-2] in environments:
        environment = parts[-2]
        base = ".".join(parts[:-2])
        extension = parts[-1]
        return base, environment, extension

    if len(parts) > 1:
        base = ".".join(parts[:-1])
        extension = parts[-1]
        return base, None, extension

    return filename, None, ""


def to_kebab_case(value: str) -> str:
    """
    Convert a path or filename segment into lowercase kebab-case for manifest asset keys.
    """
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value)

    return value.strip("-").lower() or "asset"


def infer_asset_type(extension: str) -> str:
    """
    Map file extensions to generic manifest asset types.
    Keep this intentionally broad and content-oriented.
    """
    ext = extension.lower().lstrip(".")

    mapping = {
        "md": "markdown",
        "mdx": "markdown",
        "json": "json",
        "csv": "csv",
        "svg": "svg",
        "png": "png",
        "jpg": "jpg",
        "jpeg": "jpg",
        "webp": "webp",
        "gif": "gif",
        "xlsx": "xlsx",
        "xls": "xls",
        "txt": "text",
        "html": "html",
        "xml": "xml",
        "pdf": "pdf",
    }

    return mapping.get(ext, ext or "binary")


def route_from_dir(route_dir: Path) -> str:
    rel = route_dir.relative_to(PAGES_DIR)

    if str(rel) in (".", ""):
        return "/"

    return "/" + "/".join(rel.parts)


def rel_to_pages(path: Path) -> str:
    return str(path.relative_to(PAGES_DIR)).replace(os.sep, "/")


def read_page_marker(route_dir: Path) -> Dict[str, Any]:
    """
    `.page` can be:
    - empty
    - arbitrary non-JSON marker text
    - JSON metadata, for example:
        { "id": "uprn-service" }

    Non-JSON content is ignored for backwards compatibility.
    """
    marker = route_dir / PAGE_MARKER

    if not marker.exists():
        return {}

    text = marker.read_text(encoding="utf-8").strip()

    if not text:
        return {}

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}

    if not isinstance(data, dict):
        return {}

    return data


def page_id_from_route(route: str) -> str:
    """
    Default page id derivation.

    Examples:
      /                  -> home
      /research          -> research
      /apps/uprn-service -> uprn-service
      /research/articles -> articles

    If this causes collisions, add an explicit id to the route's `.page` file.
    """
    if route == "/":
        return "home"

    parts = [part for part in route.split("/") if part]

    if not parts:
        return "home"

    return parts[-1]


def page_id_for_route_dir(route_dir: Path) -> str:
    route = route_from_dir(route_dir)
    marker = read_page_marker(route_dir)

    explicit_id = marker.get("id")

    if explicit_id is not None:
        if not isinstance(explicit_id, str) or not explicit_id.strip():
            raise ValueError(f'Invalid "id" in {route_dir / PAGE_MARKER}. Expected a non-empty string.')

        return explicit_id.strip()

    return page_id_from_route(route)


def find_route_dirs() -> Set[Path]:
    """
    Find all directories under /pages that contain `.page`.
    """
    route_dirs: Set[Path] = set()

    for root, dirs, files in os.walk(PAGES_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIR_NAMES]

        root_path = Path(root)

        if PAGE_MARKER in files:
            route_dirs.add(root_path)

    return route_dirs


def collect_files_for_route(route_dir: Path, route_dirs: Set[Path]) -> List[Path]:
    """
    Collect all files under a route directory recursively, excluding:
    - `.page`
    - hidden files
    - ignored directory names
    - any subtree that is itself a route directory
    """
    out: List[Path] = []

    for root, dirs, files in os.walk(route_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIR_NAMES]

        root_path = Path(root)

        # Stop at nested route directories.
        if root_path != route_dir and root_path in route_dirs:
            dirs[:] = []
            continue

        for filename in files:
            if filename == PAGE_MARKER or filename.startswith("."):
                continue

            file_path = root_path / filename

            if file_path.is_file():
                out.append(file_path)

    return out

def asset_key_for_file(route_dir: Path, file_path: Path, environments: List[str]) -> Tuple[str, Optional[str], str]:
    rel = file_path.relative_to(route_dir)
    parent_parts = list(rel.parent.parts) if rel.parent != Path(".") else []

    base, environment, extension = parse_filename(rel.name, environments)

    key_parts = [to_kebab_case(part) for part in parent_parts + [base]]
    asset_key = ".".join(key_parts)

    return asset_key, environment, extension


def build_index(
    route_dirs: Set[Path],
    environments: List[str],
) -> Dict[str, Dict[str, FileChoice]]:
    """
    Build:
      page_id -> asset_key -> FileChoice(default, per-environment)
    """
    index: Dict[str, Dict[str, FileChoice]] = {}
    seen_page_ids: Dict[str, Path] = {}

    for route_dir in sorted(route_dirs):
        page_id = page_id_for_route_dir(route_dir)

        if page_id in seen_page_ids:
            previous = seen_page_ids[page_id]
            raise ValueError(
                f'Duplicate page id "{page_id}".\n'
                f"First:  {previous}\n"
                f"Second: {route_dir}\n"
                f"Add explicit unique ids to the .page files."
            )

        seen_page_ids[page_id] = route_dir

        files = collect_files_for_route(route_dir, route_dirs)

        default_map: Dict[str, AssetDescriptor] = {}
        environment_map: Dict[str, Dict[str, AssetDescriptor]] = {}

        for file_path in files:
            asset_key, environment, extension = asset_key_for_file(route_dir, file_path, environments)

            asset = AssetDescriptor(
                path=rel_to_pages(file_path),
                type=infer_asset_type(extension),
            )

            if environment is None:
                # If multiple defaults map to the same key, keep the first deterministically.
                default_map.setdefault(asset_key, asset)
            else:
                environment_map.setdefault(asset_key, {})[environment] = asset

        route_entries: Dict[str, FileChoice] = {}

        for asset_key in set(list(default_map.keys()) + list(environment_map.keys())):
            route_entries[asset_key] = FileChoice(
                default_asset=default_map.get(asset_key),
                environment_assets=environment_map.get(asset_key, {}),
            )

        index[page_id] = route_entries

    return index


def build_page_assets_for_environment(
    environment: str,
    route_entries: Dict[str, FileChoice],
) -> Dict[str, Dict[str, str]]:
    """
    Build the flat "assets" object for one page and one environment.
    """
    assets: Dict[str, Dict[str, str]] = {}

    for asset_key in sorted(route_entries.keys()):
        choice = route_entries[asset_key]

        if environment in choice.environment_assets:
            selected = choice.environment_assets[environment]
        elif choice.default_asset is not None:
            selected = choice.default_asset
        else:
            continue

        assets[asset_key] = {
            "path": selected.path,
            "type": selected.type,
        }

    return assets


def build_manifest(
    environment: str,
    version: str,
    index: Dict[str, Dict[str, FileChoice]],
) -> Dict[str, Any]:
    pages: Dict[str, Dict[str, Any]] = {}

    for page_id in sorted(index.keys()):
        route_dir = page_route_dir_from_page_id(page_id)
        route = route_from_dir(route_dir)

        assets = build_page_assets_for_environment(environment, index[page_id])

        if assets:
            pages[page_id] = {
                "route": route,
                "assets": assets,
            }

    return {
        "schemaVersion": SCHEMA_VERSION,
        "version": version,
        "generatedAt": version,
        "environment": environment,
        "pages": pages,
    }


# Internal route lookup populated by main/build setup.
_PAGE_ID_TO_ROUTE_DIR: Dict[str, Path] = {}


def page_route_dir_from_page_id(page_id: str) -> Path:
    try:
        return _PAGE_ID_TO_ROUTE_DIR[page_id]
    except KeyError as exc:
        raise KeyError(f'No route directory registered for page id "{page_id}".') from exc


def register_page_route_dirs(route_dirs: Set[Path]) -> None:
    _PAGE_ID_TO_ROUTE_DIR.clear()

    for route_dir in sorted(route_dirs):
        page_id = page_id_for_route_dir(route_dir)

        if page_id in _PAGE_ID_TO_ROUTE_DIR:
            previous = _PAGE_ID_TO_ROUTE_DIR[page_id]
            raise ValueError(
                f'Duplicate page id "{page_id}".\n'
                f"First:  {previous}\n"
                f"Second: {route_dir}\n"
                f"Add explicit unique ids to the .page files."
            )

        _PAGE_ID_TO_ROUTE_DIR[page_id] = route_dir


def main() -> None:
    site = load_site_json(SITE_JSON)
    environments = get_environments(site)

    current_environment = site.get("currentenvironment")

    if (
        isinstance(current_environment, str)
        and current_environment
        and current_environment not in environments
    ):
        raise ValueError(
            f'currentenvironment "{current_environment}" is not in environments {environments}'
        )

    route_dirs = find_route_dirs()
    register_page_route_dirs(route_dirs)

    index = build_index(route_dirs, environments)

    version = utc_iso()

    for environment in environments:
        manifest = build_manifest(environment, version, index)
        out_path = REPO_ROOT / f"manifest.{environment}.json"

        out_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        print(f"Wrote {out_path.relative_to(REPO_ROOT)}")

    print("Done.")


if __name__ == "__main__":
    main()