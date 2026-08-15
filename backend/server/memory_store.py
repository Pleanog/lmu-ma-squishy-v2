import logging
from typing import Any, Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)


class PocketBaseMemoryStore:
    def __init__(
        self,
        pb_url: str,
        admin_email: str,
        admin_password: str,
        collection_name: str = "saved_memories",
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
            raise RuntimeError("PocketBase memory store is not configured.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            auth_payload = {"identity": self.admin_email, "password": self.admin_password}

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

    async def save_memory(
        self,
        participant_id: str,
        username: str,
        content: str,
        source: str,
        trigger_event: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("PocketBase is not configured. Set PB_URL, PB_ADMIN_EMAIL and PB_ADMIN_PASS.")

        participant = (participant_id or "").strip()
        if not participant:
            raise ValueError("participant_id is required to save memory.")

        payload = {
            "participant_id": participant,
            "username": (username or "").strip() or "Gast",
            "content": (content or "").strip(),
            "source": source,
            "trigger_event": trigger_event or "",
        }

        if not payload["content"]:
            raise ValueError("content is required to save memory.")

        response = await self._request(
            "POST",
            f"/api/collections/{self.collection_name}/records",
            json=payload,
        )
        return response.json()

    async def list_memories(self, participant_id: str, per_page: int = 200) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("PocketBase is not configured. Set PB_URL, PB_ADMIN_EMAIL and PB_ADMIN_PASS.")

        participant = (participant_id or "").strip()
        if not participant:
            raise ValueError("participant_id is required to list memories.")

        escaped_participant = participant.replace("'", "\\'")
        records: List[Dict[str, Any]] = []
        page = 1

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
            items = payload.get("items", [])
            records.extend(items)
            if page >= payload.get("totalPages", 1):
                break
            page += 1

        return records
