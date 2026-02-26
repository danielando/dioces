import logging
from typing import Dict, List

from ..engine.models import SchoolRecord
from ..graph.client import GraphClient
from ..graph.sharepoint_files import SharePointFiles

logger = logging.getLogger(__name__)


class FolderSharing:
    """Creates sharing links for school output folders."""

    def __init__(self, client: GraphClient):
        self._client = client

    def create_view_link(
        self,
        drive_id: str,
        folder_item_id: str,
        scope: str = "organization",
    ) -> str:
        """Create a view-only sharing link for a folder.

        scope options:
          - "organization": anyone in the tenant with the link can view
          - "anonymous": anyone with the link (use with caution)
        """
        resp = self._client.post(
            f"/drives/{drive_id}/items/{folder_item_id}/createLink",
            json={
                "type": "view",
                "scope": scope,
            },
        )
        web_url = resp.json().get("link", {}).get("webUrl", "")
        return web_url

    def share_with_email(
        self,
        drive_id: str,
        folder_item_id: str,
        email: str,
        role: str = "read",
        message: str = "",
    ) -> None:
        """Share a folder with a specific email address.

        role options: "read", "write"
        """
        self._client.post(
            f"/drives/{drive_id}/items/{folder_item_id}/invite",
            json={
                "requireSignIn": True,
                "sendInvitation": bool(message),
                "roles": [role],
                "recipients": [{"email": email}],
                "message": message,
            },
        )

    def share_all_school_folders(
        self,
        sp_files: SharePointFiles,
        output_drive_id: str,
        schools: List[SchoolRecord],
        scope: str = "organization",
    ) -> Dict[str, str]:
        """Create sharing links for all school folders. Returns {SchoolCode: URL}."""
        links = {}
        for school in schools:
            folder_name = school.folder_name
            try:
                folder_id = sp_files.ensure_folder(output_drive_id, folder_name)
                link = self.create_view_link(output_drive_id, folder_id, scope)
                links[school.SchoolCode] = link
                logger.info(f"{school.SchoolCode}: {link}")
            except Exception as e:
                logger.error(
                    f"Failed to share folder for {school.SchoolCode}: {e}"
                )
        return links
