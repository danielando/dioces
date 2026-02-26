import msal


class GraphAuth:
    """Acquires access tokens using MSAL client credentials flow.

    The app registration in Entra ID needs:
      - Sites.ReadWrite.All (application permission) + admin consent
    """

    SCOPES = ["https://graph.microsoft.com/.default"]

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self._app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )

    def get_token(self) -> str:
        """Acquire token for Microsoft Graph. Uses MSAL's built-in caching."""
        result = self._app.acquire_token_for_client(scopes=self.SCOPES)
        if "access_token" in result:
            return result["access_token"]
        raise RuntimeError(
            f"Failed to acquire token: "
            f"{result.get('error_description', result.get('error'))}"
        )
