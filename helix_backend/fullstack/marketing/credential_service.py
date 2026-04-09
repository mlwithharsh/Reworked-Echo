from __future__ import annotations

import base64
import hashlib
import json

from cryptography.fernet import Fernet

from ..config import Settings
from .repository import LocalMarketingRepository
from .schemas import ChannelCredentialResponse, UpsertChannelCredentialRequest


class MarketingCredentialService:
    """Encrypts and retrieves local channel credentials for platform adapters."""

    def __init__(self, repository: LocalMarketingRepository, settings: Settings):
        self.repository = repository
        self.settings = settings
        self._fernet = Fernet(self._build_key())

    def list_credentials(self) -> list[ChannelCredentialResponse]:
        items = self.repository.list_channel_credentials()
        return [self._with_configured_fields(item) for item in items]

    def save(self, payload: UpsertChannelCredentialRequest) -> ChannelCredentialResponse:
        secrets = {key: value for key, value in payload.secrets.items() if value}
        encrypted_blob = self._encrypt(
            {
                "configured_fields": sorted(secrets.keys()),
                "secrets": secrets,
            }
        )
        saved = self.repository.upsert_channel_credential(
            platform=payload.platform.lower(),
            account_label=payload.account_label,
            encrypted_secret_blob=encrypted_blob,
        )
        return saved.model_copy(update={"configured_fields": sorted(secrets.keys())})

    def resolve_platform_settings(self, platform: str, account_label: str = "default") -> Settings:
        blob = self.repository.get_channel_credential_blob(platform=platform.lower(), account_label=account_label)
        if not blob:
            return self.settings
        payload = self._decrypt(blob)
        secrets = payload.get("secrets", {}) if isinstance(payload, dict) else {}
        if not isinstance(secrets, dict):
            return self.settings
        return self.settings.model_copy(update=secrets)

    def _build_key(self) -> bytes:
        seed = self.settings.credential_secret or f"{self.settings.api_token}:{self.settings.root_dir}:helix-credentials"
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def _encrypt(self, payload: dict[str, object]) -> str:
        return self._fernet.encrypt(json.dumps(payload).encode("utf-8")).decode("utf-8")

    def _decrypt(self, encrypted_blob: str) -> dict[str, object]:
        try:
            from cryptography.fernet import InvalidToken
            decrypted = self._fernet.decrypt(encrypted_blob.encode("utf-8"))
            return json.loads(decrypted.decode("utf-8"))
        except (InvalidToken, Exception) as e:
            # If decryption fails, the key might have changed or data is corrupted
            # We return an empty payload to avoid crashing the entire service
            return {"error": "Decryption failed", "details": str(e)}

    def _with_configured_fields(self, item: ChannelCredentialResponse) -> ChannelCredentialResponse:
        blob = self.repository.get_channel_credential_blob(platform=item.platform, account_label=item.account_label)
        if not blob:
            return item
        payload = self._decrypt(blob)
        configured_fields = payload.get("configured_fields", []) if isinstance(payload, dict) else []
        return item.model_copy(update={"configured_fields": configured_fields})
