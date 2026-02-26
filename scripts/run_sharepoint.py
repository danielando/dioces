"""CLI entry point for SharePoint mode (Layer 2+).

Requires .env file with Azure/SharePoint credentials.
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

from policy_localiser.config import Config
from policy_localiser.engine.models import ProcessingStatus
from policy_localiser.graph.auth import GraphAuth
from policy_localiser.graph.client import GraphClient
from policy_localiser.graph.sharepoint_files import SharePointFiles
from policy_localiser.graph.sharepoint_lists import SharePointLists
from policy_localiser.orchestrator.sharepoint_pipeline import SharePointPipeline
from policy_localiser.sharing.folder_sharing import FolderSharing


def main():
    parser = argparse.ArgumentParser(
        description="Policy Localisation Engine — SharePoint Runner"
    )
    parser.add_argument(
        "--school", nargs="*",
        help="Filter to specific school codes (e.g. --school STM HFC)",
    )
    parser.add_argument(
        "--policy", nargs="*",
        help="Filter to specific policy names (e.g. --policy 'Enrolment Policy')",
    )
    parser.add_argument(
        "--share", action="store_true",
        help="Create sharing links for output folders after processing",
    )
    parser.add_argument(
        "--env-file", type=Path, default=Path(".env"),
        help="Path to .env file (default: .env)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    load_dotenv(args.env_file)
    config = Config.from_env()

    if not config.tenant_id or not config.client_id or not config.client_secret:
        print("ERROR: Missing Azure credentials. Check your .env file.")
        sys.exit(1)
    if not config.sharepoint_site_id:
        print("ERROR: Missing SHAREPOINT_SITE_ID. Check your .env file.")
        sys.exit(1)

    auth = GraphAuth(config.tenant_id, config.client_id, config.client_secret)
    client = GraphClient(auth)
    sp_lists = SharePointLists(client, config.sharepoint_site_id)
    sp_files = SharePointFiles(client, config.sharepoint_site_id)

    # Run the pipeline
    pipeline = SharePointPipeline(sp_lists, sp_files)
    results = pipeline.run(
        school_filter=args.school,
        template_filter=args.policy,
    )

    # Print results table
    print("\n" + "=" * 70)
    print(f"{'Status':<8} {'School':<8} {'Policy':<35} {'Time':>6}")
    print("-" * 70)
    for r in results:
        icon = "OK" if r.status == ProcessingStatus.SUCCESS else "FAIL"
        print(
            f"{icon:<8} {r.school_code:<8} {r.policy_name:<35} "
            f"{r.duration_seconds:>5.2f}s"
        )
        if r.error_message:
            print(f"         ERROR: {r.error_message}")
    print("=" * 70)

    success = sum(1 for r in results if r.status == ProcessingStatus.SUCCESS)
    failed = sum(1 for r in results if r.status == ProcessingStatus.ERROR)
    print(f"\nTotal: {len(results)} | Success: {success} | Failed: {failed}")

    # Share folders if requested
    if args.share:
        print("\nCreating sharing links...")
        sharing = FolderSharing(client)
        output_drive = sp_files.get_drive_id(SharePointPipeline.OUTPUT_LIBRARY)
        schools = sp_lists.get_schools()
        if args.school:
            schools = [s for s in schools if s.SchoolCode in args.school]
        links = sharing.share_all_school_folders(sp_files, output_drive, schools)
        print("\nSharing links:")
        for code, url in links.items():
            print(f"  {code}: {url}")


if __name__ == "__main__":
    main()
