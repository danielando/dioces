from dataclasses import dataclass
from pathlib import Path
from typing import List

from .models import SchoolRecord


@dataclass
class ValidationError:
    severity: str  # "error" or "warning"
    message: str

    def __repr__(self) -> str:
        return f"[{self.severity.upper()}] {self.message}"


class TemplateValidator:
    """Validates that templates, logos, and school data are consistent."""

    REQUIRED_FIELDS = ["Title", "SchoolCode", "ShortName", "PrincipalName"]

    def validate(
        self,
        template_paths: List[Path],
        logo_dir: Path,
        schools: List[SchoolRecord],
    ) -> List[ValidationError]:
        errors: List[ValidationError] = []

        # Check templates exist and are .docx
        for tp in template_paths:
            if not tp.exists():
                errors.append(ValidationError("error", f"Template not found: {tp}"))
            elif tp.suffix.lower() != ".docx":
                errors.append(ValidationError("error", f"Template is not .docx: {tp}"))

        # Check each school has a logo
        for school in schools:
            logo_path = logo_dir / f"{school.SchoolCode}.png"
            if not logo_path.exists():
                errors.append(
                    ValidationError(
                        "error",
                        f"Logo not found for {school.SchoolCode}: {logo_path}",
                    )
                )

        # Check for empty required fields
        for school in schools:
            ctx = school.to_context()
            for field_name in self.REQUIRED_FIELDS:
                if not ctx.get(field_name):
                    errors.append(
                        ValidationError(
                            "warning",
                            f"School {school.SchoolCode} has empty {field_name}",
                        )
                    )

        # Check for duplicate school codes
        codes = [s.SchoolCode for s in schools]
        seen = set()
        for code in codes:
            if code in seen:
                errors.append(
                    ValidationError("error", f"Duplicate SchoolCode: {code}")
                )
            seen.add(code)

        return errors
