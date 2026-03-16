#!/usr/bin/env python3
"""
Generate manifest.<environment>.json files from a /pages directory using `.page` markers,
but output each page entry in the nested "Option 1" style:

{
  "route": "/research",
  "files": {
    "articles": {
      "ai-document-insights": {
        "article": "...",
        "metadata": "..."
      }
    }
  }
}

Key rules:
- A directory is a route IFF it contains a `.page` file.
- Any directory named exactly "generated" is ignored (anywhere).
- A file is environment-specific if: <name>.<environment>.<ext> (e.g., config.testing.json).
  Otherwise it is included for all environments (default).
- For the same "key path", environment-specific overrides default.
- Nested structure mirrors the folder structure beneath the route directory.
- Leaf key name = filename with environment + extension removed, converted to camelCase.
  Parent directory keys are kept as-is (including hyphens), mirroring folders.

Outputs:
- manifest.<environment>.json for every environment in site.json["environments"]
  (fallback: [site.json["currentenvironment"]] if "environments" is missing)

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
from typing import Dict, List, Optional, Set, Tuple


PAGE_MARKER = ".page"


def find_repo_root(start: Path) -> Path:
    """
    Find repo root by walking up until we find site.json and pages/.
    This lets you run the script from anywhere (e.g. inside .github/).
    """
    p = start.resolve()
    for _ in range(30):
        if (p / "site.json").exists() and (p / "pages").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise FileNotFoundError("Could not find repo root (expected site.json and pages/).")


REPO_ROOT = find_repo_root(Path(__file__).parent)
SITE_JSON = REPO_ROOT / "site.json"
PAGES_DIR = REPO_ROOT / "pages"


@dataclass(frozen=True)
class FileChoice:
    default_path: Optional[str]        # rel to /pages
    environment_paths: Dict[str, str]         # environment -> rel to /pages


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def to_camel_case(s: str) -> str:
    """
    Convert 'hero.title' or 'architecture-extract-descriptions' to camelCase.
    """
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", s) if p]
    if not parts:
        return s
    first = parts[0].lower()
    rest = [(p[:1].upper() + p[1:]) if p else "" for p in parts[1:]]
    return first + "".join(rest)


def load_site_json(path: Path) -> Dict:
    if not path.exists():
        raise FileNotFoundError(f"site.json not found at {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_environments(site: Dict) -> List[str]:
    environments = site.get("environments")
    if isinstance(environments, list) and environments and all(isinstance(m, str) for m in environments):
        return environments
    cm = site.get("currentenvironment")
    if isinstance(cm, str) and cm:
        return [cm]
    raise ValueError('site.json must contain "environments": [...] or "currentenvironment": "..."')


def parse_filename(filename: str, environments: List[str]) -> Tuple[str, Optional[str]]:
    """
    Return (basename_without_environment_or_ext, environment_or_None).
    Recognizes <name>.<environment>.<ext>.
    """
    parts = filename.split(".")
    if len(parts) >= 3 and parts[-2] in environments:
        environment = parts[-2]
        base = ".".join(parts[:-2])
        return base, environment
    base = ".".join(parts[:-1]) if len(parts) > 1 else filename
    return base, None


def route_from_dir(route_dir: Path) -> str:
    rel = route_dir.relative_to(PAGES_DIR)
    if str(rel) in (".", ""):
        return "/"
    return "/" + "/".join(rel.parts)


def rel_to_pages(p: Path) -> str:
    return str(p.relative_to(PAGES_DIR)).replace(os.sep, "/")


def find_route_dirs() -> Set[Path]:
    """
    Find all directories under /pages that contain `.page`, ignoring generated/.
    """
    route_dirs: Set[Path] = set()

    for root, dirs, files in os.walk(PAGES_DIR):
        root_path = Path(root)

        if PAGE_MARKER in files:
            route_dirs.add(root_path)

    return route_dirs


def collect_files_for_route(route_dir: Path, route_dirs: Set[Path]) -> List[Path]:
    """
    Collect all files under a route_dir recursively, excluding:
    - `.page`
    - hidden files
    - anything under generated/
    - any subtree that is itself a route directory (has its own `.page`)
    """
    out: List[Path] = []
    for root, dirs, files in os.walk(route_dir):
        root_path = Path(root)

        # stop at nested route dirs
        if root_path != route_dir and root_path in route_dirs:
            dirs[:] = []
            continue

        for f in files:
            if f == PAGE_MARKER or f.startswith("."):
                continue
            fp = root_path / f
            if fp.is_file():
                out.append(fp)
    return out


def keypath_for_file(route_dir: Path, file_path: Path, environments: List[str]) -> Tuple[Tuple[str, ...], Optional[str]]:
    """
    Convert a file path to a nested key path under "files".

    Parent directory keys mirror folder names (kept as-is).
    Leaf key = camelCase(filename-without-environment-and-ext).
    """
    rel = file_path.relative_to(route_dir)  # e.g. articles/ai-x/metadata.json
    parent_parts = list(rel.parent.parts) if rel.parent != Path(".") else []

    base, environment = parse_filename(rel.name, environments)
    leaf_key = to_camel_case(base)

    # Keep directory names as-is (to mirror folders)
    return tuple(parent_parts + [leaf_key]), environment


def set_nested(obj: Dict, keys: Tuple[str, ...], value: str) -> None:
    """
    Set obj[keys[0]]...[keys[-1]] = value, creating dicts as needed.
    Raises if there's a type collision (e.g. trying to put children under a string).
    """
    cur = obj
    for k in keys[:-1]:
        if k not in cur:
            cur[k] = {}
        if not isinstance(cur[k], dict):
            raise ValueError(f"Key collision: '{k}' is already a non-object, cannot nest under it.")
        cur = cur[k]
    last = keys[-1]
    # If last exists and is a dict, collision (file vs folder)
    if last in cur and isinstance(cur[last], dict):
        raise ValueError(f"Key collision: '{last}' is already an object, cannot overwrite with a file path.")
    cur[last] = value


def build_index(route_dirs: Set[Path], environments: List[str]) -> Dict[str, Dict[Tuple[str, ...], FileChoice]]:
    """
    route -> keypath(tuple) -> FileChoice(default, per-environment)
    """
    index: Dict[str, Dict[Tuple[str, ...], FileChoice]] = {}

    for route_dir in route_dirs:
        route = route_from_dir(route_dir)
        files = collect_files_for_route(route_dir, route_dirs)

        default_map: Dict[Tuple[str, ...], str] = {}
        environment_map: Dict[Tuple[str, ...], Dict[str, str]] = {}

        for fp in files:
            keypath, environment = keypath_for_file(route_dir, fp, environments)
            path_from_pages = rel_to_pages(fp)

            if environment is None:
                # If multiple defaults map to same keypath, keep the first deterministically
                default_map.setdefault(keypath, path_from_pages)
            else:
                environment_map.setdefault(keypath, {})[environment] = path_from_pages

        route_entries: Dict[Tuple[str, ...], FileChoice] = {}
        for kp in set(list(default_map.keys()) + list(environment_map.keys())):
            route_entries[kp] = FileChoice(
                default_path=default_map.get(kp),
                environment_paths=environment_map.get(kp, {}),
            )

        index[route] = route_entries

    return index


def build_page_files_for_environment(
    environment: str,
    route_entries: Dict[Tuple[str, ...], FileChoice],
) -> Dict:
    """
    Build the nested "files" object for one route and one environment.
    """
    files_obj: Dict = {}

    # deterministic ordering for stable diffs
    for keypath in sorted(route_entries.keys()):
        choice = route_entries[keypath]
        if environment in choice.environment_paths:
            set_nested(files_obj, keypath, choice.environment_paths[environment])
        elif choice.default_path is not None:
            set_nested(files_obj, keypath, choice.default_path)

    return files_obj


def build_manifest(environment: str, version: str, index: Dict[str, Dict[Tuple[str, ...], FileChoice]]) -> Dict:
    pages: List[Dict] = []
    for route in sorted(index.keys()):
        files_obj = build_page_files_for_environment(environment, index[route])
        if files_obj:
            pages.append({"route": route, "files": files_obj})
    return {"version": version, "environment": environment, "pages": pages}


def main() -> None:
    site = load_site_json(SITE_JSON)
    environments = get_environments(site)

    current_environment = site.get("currentenvironment")
    if isinstance(current_environment, str) and current_environment and current_environment not in environments:
        raise ValueError(f'currentenvironment "{current_environment}" is not in environments {environments}')

    route_dirs = find_route_dirs()
    index = build_index(route_dirs, environments)

    version = utc_iso()
    for environment in environments:
        manifest = build_manifest(environment, version, index)
        out_path = REPO_ROOT / f"manifest.{environment}.json"
        out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {out_path.relative_to(REPO_ROOT)}")

    print("Done.")


if __name__ == "__main__":
    main()