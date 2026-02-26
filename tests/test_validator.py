from pathlib import Path

from policy_localiser.engine.models import SchoolRecord
from policy_localiser.engine.validator import TemplateValidator


class TestTemplateValidator:
    def test_valid_inputs_no_errors(self, template_path, logos_dir, sample_schools):
        validator = TemplateValidator()
        errors = validator.validate([template_path], logos_dir, sample_schools)
        blocking = [e for e in errors if e.severity == "error"]
        assert blocking == []

    def test_missing_template_is_error(self, logos_dir, sample_schools):
        validator = TemplateValidator()
        errors = validator.validate(
            [Path("/nonexistent/template.docx")], logos_dir, sample_schools
        )
        blocking = [e for e in errors if e.severity == "error"]
        assert len(blocking) >= 1
        assert "not found" in blocking[0].message

    def test_missing_logo_is_error(self, template_path, tmp_path, sample_schools):
        # Use empty directory as logo_dir
        validator = TemplateValidator()
        errors = validator.validate([template_path], tmp_path, sample_schools)
        logo_errors = [e for e in errors if e.severity == "error" and "Logo" in e.message]
        assert len(logo_errors) == len(sample_schools)

    def test_empty_required_field_is_warning(self, template_path, logos_dir):
        school = SchoolRecord(
            Title="Test School",
            SchoolCode="TST",
            ShortName="",  # empty required field
            PrincipalName="",  # empty required field
            PrincipalTitle="Principal",
            SchoolAddress="123 Main St",
            Suburb="Testville",
            State="QLD",
            PostCode="4000",
            SchoolPhone="1234567890",
            SchoolEmail="test@test.edu.au",
            SchoolWebsite="www.test.edu.au",
            SchoolType="Primary",
            Parish="Test Parish",
            DiocesanRegion="Central",
            ABN="00 000 000 000",
            EstablishedYear="2000",
        )
        validator = TemplateValidator()
        # Need a logo for TST — won't exist, so filter to just warnings
        errors = validator.validate([template_path], logos_dir, [school])
        warnings = [e for e in errors if e.severity == "warning"]
        assert len(warnings) >= 2  # ShortName and PrincipalName

    def test_duplicate_school_code_is_error(self, template_path, logos_dir, sample_schools):
        # Duplicate the first school
        duped = sample_schools + [sample_schools[0]]
        validator = TemplateValidator()
        errors = validator.validate([template_path], logos_dir, duped)
        dup_errors = [e for e in errors if "Duplicate" in e.message]
        assert len(dup_errors) >= 1
