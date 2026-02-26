import logging
from pathlib import Path
from typing import List

from .client import GraphClient

logger = logging.getLogger(__name__)


class SharePointFiles:
    """Download files from and upload files to SharePoint document libraries."""

    def __init__(self, client: GraphClient, site_id: str):
        self._client = client
        self._site_id = site_id

    def get_drive_id(self, library_name: str) -> str:
        """Look up the drive ID for a named document library."""
        resp = self._client.get(f"/sites/{self._site_id}/drives")
        drives = resp.json().get("value", [])
        for drive in drives:
            if drive.get("name") == library_name:
                return drive["id"]
        raise RuntimeError(f"Document library '{library_name}' not found")

    def list_files(self, drive_id: str) -> List[dict]:
        """List files in the root of a drive. Returns list of {name, id, ...}."""
        resp = self._client.get(f"/drives/{drive_id}/root/children")
        return resp.json().get("value", [])

    def download_file(self, drive_id: str, item_id: str, local_path: Path) -> None:
        """Download a file by item ID to local disk."""
        data = self._client.get_binary(
            f"/drives/{drive_id}/items/{item_id}/content"
        )
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)

    def download_file_by_name(
        self, drive_id: str, file_name: str, local_path: Path
    ) -> None:
        """Download a file by its name from the root of a drive."""
        data = self._client.get_binary(
            f"/drives/{drive_id}/root:/{file_name}:/content"
        )
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)

    def ensure_folder(self, drive_id: str, folder_name: str) -> str:
        """Create a folder if it doesn't exist. Returns the folder's item ID."""
        try:
            resp = self._client.get(f"/drives/{drive_id}/root:/{folder_name}")
            folder_id = resp.json()["id"]
            logger.debug(f"Folder '{folder_name}' already exists")
            return folder_id
        except Exception:
            resp = self._client.post(
                f"/drives/{drive_id}/root/children",
                json={
                    "name": folder_name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "fail",
                },
            )
            folder_id = resp.json()["id"]
            logger.info(f"Created folder '{folder_name}'")
            return folder_id

    def upload_file(
        self,
        drive_id: str,
        folder_name: str,
        file_name: str,
        file_bytes: bytes,
    ) -> dict:
        """Upload a file to a folder, overwriting if it exists.

        Uses the simple upload API (PUT to path). Supports files up to 250 MB.
        """
        resp = self._client.put_binary(
            f"/drives/{drive_id}/root:/{folder_name}/{file_name}:/content",
            data=file_bytes,
            content_type=(
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
        )
        return resp.json()
