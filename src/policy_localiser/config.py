import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Entra ID App Registration
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""

    # SharePoint site
    sharepoint_site_id: str = ""

    # Local paths for Layer 1 testing
    local_template_dir: Path = field(default_factory=lambda: Path("./data/templates"))
    local_logo_dir: Path = field(default_factory=lambda: Path("./data/logos"))
    local_output_dir: Path = field(default_factory=lambda: Path("./data/output"))

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            tenant_id=os.environ.get("AZURE_TENANT_ID", ""),
            client_id=os.environ.get("AZURE_CLIENT_ID", ""),
            client_secret=os.environ.get("AZURE_CLIENT_SECRET", ""),
            sharepoint_site_id=os.environ.get("SHAREPOINT_SITE_ID", ""),
            local_template_dir=Path(os.environ.get("LOCAL_TEMPLATE_DIR", "./data/templates")),
            local_logo_dir=Path(os.environ.get("LOCAL_LOGO_DIR", "./data/logos")),
            local_output_dir=Path(os.environ.get("LOCAL_OUTPUT_DIR", "./data/output")),
        )
