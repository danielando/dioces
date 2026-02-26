import logging
from typing import List

from ..engine.models import ProcessingResult, SchoolRecord
from .client import GraphClient

logger = logging.getLogger(__name__)


class SharePointLists:
    """Read from School Directory list, write to Processing Log list."""

    def __init__(self, client: GraphClient, site_id: str):
        self._client = client
        self._site_id = site_id

    def _get_list_id(self, list_name: str) -> str:
        resp = self._client.get(
            f"/sites/{self._site_id}/lists",
            params={
                "$filter": f"displayName eq '{list_name}'",
                "$select": "id",
            },
        )
        lists = resp.json().get("value", [])
        if not lists:
            raise RuntimeError(f"List '{list_name}' not found in site")
        return lists[0]["id"]

    def get_schools(self) -> List[SchoolRecord]:
        """Read all items from the 'School Directory' list."""
        list_id = self._get_list_id("School Directory")
        items: list = []
        url = (
            f"/sites/{self._site_id}/lists/{list_id}/items"
            f"?$expand=fields&$top=100"
        )

        while url:
            resp = self._client.get(url)
            data = resp.json()
            items.extend(data.get("value", []))
            url = data.get("@odata.nextLink")

        schools = []
        for item in items:
            fields = item.get("fields", {})
            schools.append(
                SchoolRecord(
                    Title=fields.get("Title", ""),
                    SchoolCode=fields.get("SchoolCode", ""),
                    ShortName=fields.get("ShortName", ""),
                    PrincipalName=fields.get("PrincipalName", ""),
                    PrincipalTitle=fields.get("PrincipalTitle", ""),
                    SchoolAddress=fields.get("SchoolAddress", ""),
                    Suburb=fields.get("Suburb", ""),
                    State=fields.get("State", ""),
                    PostCode=fields.get("PostCode", ""),
                    SchoolPhone=fields.get("SchoolPhone", ""),
                    SchoolEmail=fields.get("SchoolEmail", ""),
                    SchoolWebsite=fields.get("SchoolWebsite", ""),
                    SchoolType=fields.get("SchoolType", ""),
                    Parish=fields.get("Parish", ""),
                    DiocesanRegion=fields.get("DiocesanRegion", ""),
                    ABN=fields.get("ABN", ""),
                    EstablishedYear=fields.get("EstablishedYear", ""),
                )
            )

        logger.info(f"Loaded {len(schools)} school(s) from School Directory")
        return schools

    def write_processing_log(self, results: List[ProcessingResult]) -> None:
        """Write processing results to the 'Processing Log' list."""
        list_id = self._get_list_id("Processing Log")
        for result in results:
            self._client.post(
                f"/sites/{self._site_id}/lists/{list_id}/items",
                json={
                    "fields": {
                        "Title": f"{result.school_code}-{result.policy_name}",
                        "RunId": result.run_id,
                        "RunDate": result.run_date.isoformat(),
                        "SchoolCode": result.school_code,
                        "PolicyName": result.policy_name,
                        "Status": result.status.value,
                        "ErrorMessage": result.error_message or "",
                        "Duration": result.duration_seconds,
                    }
                },
            )
        logger.info(f"Wrote {len(results)} entries to Processing Log")
