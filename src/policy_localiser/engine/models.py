from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ProcessingStatus(Enum):
    SUCCESS = "Success"
    ERROR = "Error"
    SKIPPED = "Skipped"


@dataclass
class SchoolRecord:
    """Maps 1:1 to the 'School Directory' Microsoft List columns."""

    Title: str
    SchoolCode: str
    ShortName: str
    PrincipalName: str
    PrincipalTitle: str
    SchoolAddress: str
    Suburb: str
    State: str
    PostCode: str
    SchoolPhone: str
    SchoolEmail: str
    SchoolWebsite: str
    SchoolType: str
    Parish: str
    DiocesanRegion: str
    ABN: str
    EstablishedYear: str

    @property
    def folder_name(self) -> str:
        return f"{self.SchoolCode} - {self.Title}"

    def to_context(self) -> dict:
        """Convert to a flat dict for docxtpl rendering.
        Keys match the {{PlaceholderName}} tags in templates exactly."""
        return {
            "Title": self.Title,
            "SchoolCode": self.SchoolCode,
            "ShortName": self.ShortName,
            "PrincipalName": self.PrincipalName,
            "PrincipalTitle": self.PrincipalTitle,
            "SchoolAddress": self.SchoolAddress,
            "Suburb": self.Suburb,
            "State": self.State,
            "PostCode": self.PostCode,
            "SchoolPhone": self.SchoolPhone,
            "SchoolEmail": self.SchoolEmail,
            "SchoolWebsite": self.SchoolWebsite,
            "SchoolType": self.SchoolType,
            "Parish": self.Parish,
            "DiocesanRegion": self.DiocesanRegion,
            "ABN": self.ABN,
            "EstablishedYear": self.EstablishedYear,
        }


@dataclass
class ProcessingResult:
    """Result of processing a single (school, policy) combination."""

    run_id: str
    run_date: datetime
    school_code: str
    policy_name: str
    status: ProcessingStatus
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
