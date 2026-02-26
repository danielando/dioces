"""CLI entry point for local testing (Layer 1 only)."""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from policy_localiser.engine.models import SchoolRecord, ProcessingStatus
from policy_localiser.orchestrator.pipeline import LocalPipeline


def load_schools_from_json(json_path: Path):
    with open(json_path) as f:
        data = json.load(f)
    return [SchoolRecord(**s) for s in data]


def main():
    parser = argparse.ArgumentParser(description="Policy Localisation Engine — Local Runner")
    parser.add_argument(
        "--templates", type=Path, required=True,
        help="Path to directory containing .docx templates",
    )
    parser.add_argument(
        "--logos", type=Path, required=True,
        help="Path to directory containing school logo PNGs",
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Path to output directory",
    )
    parser.add_argument(
        "--schools-json", type=Path, required=True,
        help="Path to JSON file with school data",
    )
    parser.add_argument(
        "--school", nargs="*",
        help="Filter to specific school codes (e.g. --school STM HFC)",
    )
    parser.add_argument(
        "--policy", nargs="*",
        help="Filter to specific policy names without extension (e.g. --policy 'Sample_Policy')",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    schools = load_schools_from_json(args.schools_json)
    pipeline = LocalPipeline()

    results = pipeline.process_all(
        template_dir=args.templates,
        logo_dir=args.logos,
        output_dir=args.output,
        schools=schools,
        template_filter=args.policy,
        school_filter=args.school,
    )

    # Print results table
    print("\n" + "=" * 70)
    print(f"{'Status':<8} {'School':<8} {'Policy':<35} {'Time':>6}")
    print("-" * 70)
    for r in results:
        icon = "OK" if r.status == ProcessingStatus.SUCCESS else "FAIL"
        print(f"{icon:<8} {r.school_code:<8} {r.policy_name:<35} {r.duration_seconds:>5.2f}s")
        if r.error_message:
            print(f"         ERROR: {r.error_message}")
    print("=" * 70)

    success = sum(1 for r in results if r.status == ProcessingStatus.SUCCESS)
    failed = sum(1 for r in results if r.status == ProcessingStatus.ERROR)
    print(f"\nTotal: {len(results)} | Success: {success} | Failed: {failed}")


if __name__ == "__main__":
    main()
