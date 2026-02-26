import logging
import uuid
from pathlib import Path
from typing import List, Optional

from ..engine.models import ProcessingResult, ProcessingStatus, SchoolRecord
from ..engine.renderer import PolicyRenderer
from ..engine.validator import TemplateValidator

logger = logging.getLogger(__name__)


class LocalPipeline:
    """Layer 1 pipeline: processes documents using only local files.

    Use this for testing without any SharePoint dependency.
    """

    def __init__(self):
        self._renderer = PolicyRenderer()

    def process_all(
        self,
        template_dir: Path,
        logo_dir: Path,
        output_dir: Path,
        schools: List[SchoolRecord],
        template_filter: Optional[List[str]] = None,
        school_filter: Optional[List[str]] = None,
    ) -> List[ProcessingResult]:
        run_id = str(uuid.uuid4())[:8]
        results: List[ProcessingResult] = []

        templates = sorted(template_dir.glob("*.docx"))
        if template_filter:
            templates = [t for t in templates if t.stem in template_filter]

        if school_filter:
            schools = [s for s in schools if s.SchoolCode in school_filter]

        # Pre-flight validation
        validator = TemplateValidator()
        errors = validator.validate(templates, logo_dir, schools)
        blocking = [e for e in errors if e.severity == "error"]
        if blocking:
            for err in blocking:
                logger.error(str(err))
            raise RuntimeError(
                f"Validation failed with {len(blocking)} error(s). "
                "Fix them before proceeding."
            )
        for warn in [e for e in errors if e.severity == "warning"]:
            logger.warning(str(warn))

        total = len(schools) * len(templates)
        processed = 0

        logger.info(
            f"Starting run {run_id}: {len(schools)} school(s) x "
            f"{len(templates)} template(s) = {total} document(s)"
        )

        for school in schools:
            school_output_dir = output_dir / school.folder_name
            logo_path = logo_dir / f"{school.SchoolCode}.png"

            for template_path in templates:
                processed += 1
                output_file = school_output_dir / template_path.name
                logger.info(
                    f"[{processed}/{total}] {school.SchoolCode} / {template_path.stem}"
                )

                result = self._renderer.render(
                    template_path=template_path,
                    logo_path=logo_path,
                    school=school,
                    output_path=output_file,
                    run_id=run_id,
                )
                results.append(result)

                if result.status == ProcessingStatus.ERROR:
                    logger.error(f"  FAILED: {result.error_message}")

        # Summary
        success = sum(1 for r in results if r.status == ProcessingStatus.SUCCESS)
        failed = sum(1 for r in results if r.status == ProcessingStatus.ERROR)
        logger.info(f"Run {run_id} complete: {success} succeeded, {failed} failed out of {total}")

        return results
