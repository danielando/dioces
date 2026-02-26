import time
from datetime import datetime, timezone
from pathlib import Path

from docxtpl import DocxTemplate

from .models import ProcessingResult, ProcessingStatus, SchoolRecord

LOGO_PLACEHOLDER_NAME = "logo_placeholder.png"


class PolicyRenderer:
    """Renders a single policy template for a single school.

    Stateless per call — a new DocxTemplate is created each time to
    avoid cross-contamination between schools.
    """

    def render(
        self,
        template_path: Path,
        logo_path: Path,
        school: SchoolRecord,
        output_path: Path,
        run_id: str,
    ) -> ProcessingResult:
        start = time.monotonic()
        policy_name = template_path.stem
        try:
            doc = DocxTemplate(str(template_path))

            # Replace placeholder image with school logo.
            # replace_pic matches on the *basename* of the image inside the docx.
            # Must happen BEFORE render() which processes the XML via Jinja2.
            doc.replace_pic(LOGO_PLACEHOLDER_NAME, str(logo_path))

            # Render text placeholders
            context = school.to_context()
            doc.render(context)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path))

            elapsed = time.monotonic() - start
            return ProcessingResult(
                run_id=run_id,
                run_date=datetime.now(timezone.utc),
                school_code=school.SchoolCode,
                policy_name=policy_name,
                status=ProcessingStatus.SUCCESS,
                duration_seconds=round(elapsed, 2),
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            return ProcessingResult(
                run_id=run_id,
                run_date=datetime.now(timezone.utc),
                school_code=school.SchoolCode,
                policy_name=policy_name,
                status=ProcessingStatus.ERROR,
                error_message=str(e),
                duration_seconds=round(elapsed, 2),
            )
