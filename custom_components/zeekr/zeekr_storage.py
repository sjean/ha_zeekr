# custom_components/zeekr/zeekr_storage.py
"""
Manage token persistence and loading.

PRIMARY STORAGE: entry.data in Home Assistant
BACKUP STORAGE: tokens.json file
"""
import json
import os
from typing import Optional, Dict

_LOGGER = None


def set_logger(logger):
    """Set the logger."""
    global _LOGGER
    _LOGGER = logger


class TokenStorage:
    """Helper for working with token storage."""

    def __init__(self):
        """Initialize storage."""
        # Resolve the directory where this file lives
        self.storage_dir = os.path.dirname(os.path.abspath(__file__))
        self.filename = os.path.join(self.storage_dir, 'tokens.json')

    def save_tokens(self, tokens: Dict[str, str]) -> None:
        """
        Save tokens to the JSON backup file.

        Primary storage: entry.data in Home Assistant
        This is a backup copy for migrating older installations

        Args:
            tokens: Dictionary with keys:
                   - accessToken: Access token for the SECURE API
                   - refreshToken: Refresh token
                   - jwtToken: JWT token used by the remote-control gateway
                   - userId: User ID
                   - clientId: Client ID
                   - device_id: Device ID
                   - remote_control_vehicles: VIN -> remote-control metadata map
        """
        try:
            if _LOGGER:
                _LOGGER.debug(f"[TokenStorage] Saving tokens (backup) to {self.filename}")

            with open(self.filename, 'w') as f:
                json.dump(tokens, f, indent=4)

            if _LOGGER:
                _LOGGER.info(f"✅ [TokenStorage] Tokens saved (backup)")
        except Exception as e:
            if _LOGGER:
                _LOGGER.error(f"❌ [TokenStorage] Failed to save tokens: {e}")

    def load_tokens(self) -> Optional[Dict[str, str]]:
        """
        Load tokens from the JSON backup file.

        Used to migrate older versions

        Returns:
            Token dictionary or None if the file does not exist
        """
        if not os.path.exists(self.filename):
            if _LOGGER:
                _LOGGER.debug(f"[TokenStorage] File {self.filename} not found")
            return None

        try:
            with open(self.filename, 'r') as f:
                tokens = json.load(f)

            if _LOGGER:
                _LOGGER.info(f"✅ [TokenStorage] Tokens loaded from file (backup)")

            return tokens
        except Exception as e:
            if _LOGGER:
                _LOGGER.error(f"❌ [TokenStorage] Failed to load tokens: {e}")
            return None

    def clear_tokens(self) -> None:
        """Delete the token file."""
        if os.path.exists(self.filename):
            os.remove(self.filename)
            if _LOGGER:
                _LOGGER.info(f"✅ [TokenStorage] Tokens file deleted")


# Create the global instance
token_storage = TokenStorage()
