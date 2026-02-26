import json
from pathlib import Path

import pytest

from policy_localiser.engine.models import ProcessingStatus, SchoolRecord
from policy_localiser.orchestrator.pipeline import LocalPipeline


class TestLocalPipeline:
    def test_processes_all_combinations(
        self, fixtures_dir, logos_dir, sample_schools, tmp_path
    ):
        pipeline = LocalPipeline()
        results = pipeline.process_all(
            template_dir=fixtures_dir / "templates",
            logo_dir=logos_dir,
            output_dir=tmp_path,
            schools=sample_schools,
        )

        # 3 schools x 1 template = 3 results
        assert len(results) == 3
        assert all(r.status == ProcessingStatus.SUCCESS for r in results)

        # Check output folders exist
        for school in sample_schools:
            folder = tmp_path / school.folder_name
            assert folder.exists()
            assert (folder / "Sample_Policy.docx").exists()

    def test_school_filter(self, fixtures_dir, logos_dir, sample_schools, tmp_path):
        pipeline = LocalPipeline()
        results = pipeline.process_all(
            template_dir=fixtures_dir / "templates",
            logo_dir=logos_dir,
            output_dir=tmp_path,
            schools=sample_schools,
            school_filter=["STM"],
        )

        assert len(results) == 1
        assert results[0].school_code == "STM"

    def test_overwrites_on_rerun(self, fixtures_dir, logos_dir, sample_schools, tmp_path):
        pipeline = LocalPipeline()

        # First run
        results1 = pipeline.process_all(
            template_dir=fixtures_dir / "templates",
            logo_dir=logos_dir,
            output_dir=tmp_path,
            schools=sample_schools[:1],
        )
        assert len(results1) == 1

        # Second run (same output dir)
        results2 = pipeline.process_all(
            template_dir=fixtures_dir / "templates",
            logo_dir=logos_dir,
            output_dir=tmp_path,
            schools=sample_schools[:1],
        )
        assert len(results2) == 1
        assert results2[0].status == ProcessingStatus.SUCCESS

    def test_validation_failure_raises(self, fixtures_dir, sample_schools, tmp_path):
        pipeline = LocalPipeline()

        with pytest.raises(RuntimeError, match="Validation failed"):
            pipeline.process_all(
                template_dir=fixtures_dir / "templates",
                logo_dir=tmp_path,  # Empty dir = no logos
                output_dir=tmp_path / "out",
                schools=sample_schools,
            )
