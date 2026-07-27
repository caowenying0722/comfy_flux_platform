#!/usr/bin/env python3
"""Validate that a ComfyUI UI workflow only uses node types available in object_info."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow", help="Path to ComfyUI UI workflow JSON")
    parser.add_argument("object_info", help="Path to ComfyUI /object_info JSON")
    parser.add_argument(
        "--require",
        action="append",
        default=[],
        help="Additional node type that must exist in object_info",
    )
    args = parser.parse_args()

    workflow = json.loads(Path(args.workflow).read_text(encoding="utf-8"))
    object_info = json.loads(Path(args.object_info).read_text(encoding="utf-8"))

    node_types = sorted({node["type"] for node in workflow.get("nodes", [])})
    missing = [node_type for node_type in node_types if node_type not in object_info]
    missing_required = [node_type for node_type in args.require if node_type not in object_info]

    print("workflow:", args.workflow)
    print("node_types:", ", ".join(node_types))
    print("missing:", missing)
    print("missing_required:", missing_required)

    return 1 if missing or missing_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
