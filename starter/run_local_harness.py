"""Minimal local test harness to smoke-test documented StudyGraph interfaces."""

import argparse
import importlib
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(description="Study Sentinel Local Smoke-Test Harness")
    parser.add_argument("--module", default="stage1.atlas", help="Module containing StudyGraph and Atlas")
    parser.add_argument("--data", default="hackathon-data", help="Path to hackathon-data folder")
    parser.add_argument("--cut", type=int, default=None, help="Data cut to build (default: latest)")
    args = parser.parse_args()

    print(f"=== Study Sentinel Local Harness ===")
    print(f"Target Module : {args.module}")
    print(f"Data Path     : {args.data}")
    print(f"Requested Cut : {args.cut if args.cut is not None else 'latest'}")

    try:
        mod = importlib.import_module(args.module)
    except ModuleNotFoundError as e:
        print(f"ERROR: Could not import module '{args.module}': {e}", file=sys.stderr)
        sys.exit(1)

    if not hasattr(mod, "StudyGraph"):
        print(f"ERROR: Module '{args.module}' does not expose 'StudyGraph'", file=sys.stderr)
        sys.exit(1)

    StudyGraph = getattr(mod, "StudyGraph")

    print("\n1. Initializing StudyGraph...")
    try:
        graph = StudyGraph(data_dir=args.data)
        print(f"   Root Dir: {graph.root_dir}")
        print(f"   Data Dir: {graph.data_dir}")
        print(f"   Available Cuts in cuts.csv: {sorted(list(graph.cuts.keys()))}")
    except Exception as e:
        print(f"ERROR: Failed initializing StudyGraph: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n2. Building StudyGraph...")
    try:
        stats = graph.build(cut=args.cut)
    except Exception as e:
        print(f"ERROR: StudyGraph build failed: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n3. Build Results:")
    print(json.dumps(stats, indent=2))

    # Basic invariant assertions
    assert stats["subjects"] > 0, "No subjects found"
    assert stats["records"] > 0, "No records loaded"
    assert stats["protocol_version"] in (1, 2, 3), f"Invalid protocol version: {stats['protocol_version']}"

    print(f"\n[PASS] Smoke test completed successfully in {stats['build_time_ms']} ms.")


if __name__ == "__main__":
    main()
