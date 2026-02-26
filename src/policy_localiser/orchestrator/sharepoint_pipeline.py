import logging
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional

from ..engine.models import ProcessingResult, ProcessingStatus, SchoolRecord
from ..engine.renderer import PolicyRenderer
from ..engine.validator import TemplateValidator
from ..graph.sharepoint_files import SharePointFiles
from ..graph.sharepoint_lists import SharePointLists

logger = logging.getLogger(__name__)


class SharePointPipeline:
    """Full pipeline: downloads from SharePoint, processes, uploads back."""

    TEMPLATES_LIBRARY = "Policy Templates"
    LOGOS_LIBRARY = "School Logos"
    OUTPUT_LIBRARY = "Localised Policies"

    def __init__(self, sp_lists: SharePointLists, sp_files: SharePointFiles):
        self._sp_lists = sp_lists
        self._sp_files = sp_files
        self._renderer = PolicyRenderer()

    def run(
        self,
        school_filter: Optional[List[str]] = None,
        template_filter: Optional[List[str]] = None,
    ) -> List[ProcessingResult]:
        run_id = str(uuid.uuid4())[:8]
        results: List[ProcessingResult] = []

        # Step 1: Get school data
        logger.info("Fetching school directory from SharePoint...")
        schools = self._sp_lists.get_schools()
        if school_filter:
            schools = [s for s in schools if s.SchoolCode in school_filter]
        logger.info(f"Processing {len(schools)} school(s)")

        # Step 2: Resolve drive IDs
        templates_drive = self._sp_files.get_drive_id(self.TEMPLATES_LIBRARY)
        logos_drive = self._sp_files.get_drive_id(self.LOGOS_LIBRARY)
        output_drive = self._sp_files.get_drive_id(self.OUTPUT_LIBRARY)

        with tempfile.TemporaryDirectory(prefix="policy_loc_") as tmp:
            tmp_path = Path(tmp)
            tmpl_dir = tmp_path / "templates"
            logo_dir = tmp_path / "logos"
            out_dir = tmp_path / "output"
            tmpl_dir.mkdir()
            logo_dir.mkdir()
            out_dir.mkdir()

            # Step 3: Download templates
            logger.info("Downloading policy templates...")
            template_items = self._sp_files.list_files(templates_drive)
            for item in template_items:
                if item["name"].endswith(".docx"):
                    self._sp_files.download_file(
                        templates_drive, item["id"], tmpl_dir / item["name"]
                    )
            logger.info(f"Downloaded {len(list(tmpl_dir.glob('*.docx')))} template(s)")

            # Step 4: Download logos
            logger.info("Downloading school logos...")
            for school in schools:
                logo_name = f"{school.SchoolCode}.png"
                try:
                    self._sp_files.download_file_by_name(
                        logos_drive, logo_name, logo_dir / logo_name
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to download logo for {school.SchoolCode}: {e}"
                    )

            # Step 5: Validate
            templates = sorted(tmpl_dir.glob("*.docx"))
            if template_filter:
                templates = [t for t in templates if t.stem in template_filter]

            validator = TemplateValidator()
            errors = validator.validate(templates, logo_dir, schools)
            blocking = [e for e in errors if e.severity == "error"]
            if blocking:
                for err in blocking:
                    logger.error(str(err))
                raise RuntimeError(
                    f"Validation failed with {len(blocking)} error(s)"
                )

            # Step 6: Process and upload
            total = len(schools) * len(templates)
            processed = 0
            logger.info(
                f"Starting run {run_id}: {len(schools)} school(s) x "
                f"{len(templates)} template(s) = {total} document(s)"
            )

            for school in schools:
                folder_name = school.folder_name
                self._sp_files.ensure_folder(output_drive, folder_name)

                school_out = out_dir / folder_name
                logo_path = logo_dir / f"{school.SchoolCode}.png"

                for template_path in templates:
                    processed += 1
                    output_file = school_out / template_path.name
                    logger.info(
                        f"[{processed}/{total}] "
                        f"{school.SchoolCode} / {template_path.stem}"
                    )

                    result = self._renderer.render(
                        template_path=template_path,
                        logo_path=logo_path,
                        school=school,
                        output_path=output_file,
                        run_id=run_id,
                    )
                    results.append(result)

                    if result.status == ProcessingStatus.SUCCESS:
                        file_bytes = output_file.read_bytes()
                        self._sp_files.upload_file(
                            output_drive,
                            folder_name,
                            template_path.name,
                            file_bytes,
                        )
                    else:
                        logger.error(f"  FAILED: {result.error_message}")

            # Step 7: Write processing log
            logger.info("Writing processing log to SharePoint...")
            self._sp_lists.write_processing_log(results)

        success = sum(1 for r in results if r.status == ProcessingStatus.SUCCESS)
        failed = sum(1 for r in results if r.status == ProcessingStatus.ERROR)
        logger.info(
            f"Run {run_id} complete: {success} succeeded, "
            f"{failed} failed out of {total}"
        )

        return results
