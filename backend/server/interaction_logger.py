import json
import logging
from typing import Any, Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)


class PocketBaseInteractionLogger:
    def __init__(
        self,
        pb_url: str,
        admin_email: str,
        admin_password: str,
        collection_name: str = "interaction_logs",
    ):
        self.pb_url = (pb_url or "").rstrip("/")
        self.admin_email = admin_email or ""
        self.admin_password = admin_password or ""
        self.collection_name = collection_name
        self._admin_token: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.pb_url and self.admin_email and self.admin_password)

    async def _authenticate(self) -> str:
        if self._admin_token:
            return self._admin_token

        if not self.is_configured():
            raise RuntimeError("PocketBase interaction logger is not configured.")

        auth_payload = {"identity": self.admin_email, "password": self.admin_password}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.pb_url}/api/collections/_superusers/auth-with-password",
                json=auth_payload,
            )
            if response.status_code == 404:
                response = await client.post(
                    f"{self.pb_url}/api/admins/auth-with-password",
                    json=auth_payload,
                )
            response.raise_for_status()
            token = response.json().get("token")
            if not token:
                raise RuntimeError("PocketBase auth response did not include a token.")
            self._admin_token = token
            return token

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        token = await self._authenticate()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = token

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.request(
                method,
                f"{self.pb_url}{path}",
                headers=headers,
                **kwargs,
            )

        if response.status_code == 401:
            self._admin_token = None
            token = await self._authenticate()
            headers["Authorization"] = token
            async with httpx.AsyncClient(timeout=15.0) as retry_client:
                response = await retry_client.request(
                    method,
                    f"{self.pb_url}{path}",
                    headers=headers,
                    **kwargs,
                )

        response.raise_for_status()
        return response

    async def log_interaction(
        self,
        participant_id: str,
        username: str,
        source_client_type: str,
        interaction_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("PocketBase is not configured. Set PB_URL, PB_ADMIN_EMAIL and PB_ADMIN_PASS.")

        cleaned_participant = (participant_id or "").strip()
        if not cleaned_participant:
            raise ValueError("participant_id is required for interaction logging.")

        payload = {
            "participant_id": cleaned_participant,
            "username": (username or "").strip() or "Gast",
            "source_client_type": (source_client_type or "").strip() or "unknown",
            "interaction_type": (interaction_type or "").strip(),
            "content": (content or "").strip(),
            "metadata_json": json.dumps(metadata or {}, ensure_ascii=True),
        }

        if not payload["interaction_type"]:
            raise ValueError("interaction_type is required.")

        response = await self._request(
            "POST",
            f"/api/collections/{self.collection_name}/records",
            json=payload,
        )
        return response.json()

    async def list_interactions(self, participant_id: str, per_page: int = 200) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("PocketBase is not configured. Set PB_URL, PB_ADMIN_EMAIL and PB_ADMIN_PASS.")

        cleaned_participant = (participant_id or "").strip()
        if not cleaned_participant:
            raise ValueError("participant_id is required.")

        escaped_participant = cleaned_participant.replace("'", "\\'")
        page = 1
        records: List[Dict[str, Any]] = []

        while True:
            response = await self._request(
                "GET",
                f"/api/collections/{self.collection_name}/records",
                params={
                    "filter": f"participant_id = '{escaped_participant}'",
                    "sort": "-created",
                    "perPage": per_page,
                    "page": page,
                },
            )
            payload = response.json()
            records.extend(payload.get("items", []))
            if page >= payload.get("totalPages", 1):
                break
            page += 1

        return records
