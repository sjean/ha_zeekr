# custom_components/zeekr/__init__.py
"""Zeekr integration for Home Assistant"""

import logging
import os
import json
from typing import Final
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .zeekr_api import ZeekrAPI
from .coordinator import ZeekrDataCoordinator
from .zeekr_storage import token_storage

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zeekr integration"""

    _LOGGER.info(f"🔧 Setting up Zeekr integration for entry {entry.entry_id}")

    try:
        # Загружаем токены из entry
        tokens = dict(entry.data)

        # Резервно проверяем файл (для старых установок)
        if not tokens or not tokens.get('accessToken'):
            _LOGGER.warning("⚠️ No tokens in entry.data, trying file storage...")
            tokens = token_storage.load_tokens()

            if tokens:
                hass.config_entries.async_update_entry(entry, data=tokens)
                _LOGGER.info("✅ Tokens migrated from file to entry")

        if not tokens or not tokens.get('accessToken'):
            _LOGGER.error("❌ No tokens found")
            return False

        # Проверяем необходимые поля
        required_fields = ['accessToken', 'userId', 'clientId', 'device_id']
        missing_fields = [f for f in required_fields if f not in tokens or not tokens[f]]

        if missing_fields:
            _LOGGER.error(f"❌ Missing required token fields: {missing_fields}")
            return False

        # Создаем папку для ответов
        try:
            responses_dir = os.path.join(hass.config.path('www'), 'zeekr_responses')
            os.makedirs(responses_dir, exist_ok=True)
            _LOGGER.info(f"📁 Responses directory: {responses_dir}")
        except Exception as e:
            _LOGGER.error(f"❌ Failed to create responses directory: {e}")
            responses_dir = None

        # Создаем API клиент
        api_client = ZeekrAPI(
            access_token=tokens.get('accessToken'),
            user_id=tokens.get('userId'),
            client_id=tokens.get('clientId'),
            device_id=tokens.get('device_id')
        )

        # Создаем coordinator
        coordinator = ZeekrDataCoordinator(hass, api_client, responses_dir)

        # Получаем первые данные
        try:
            await coordinator.async_config_entry_first_refresh()
            _LOGGER.info("✅ First data refresh successful")
        except Exception as e:
            _LOGGER.warning(f"⚠️ First refresh failed: {e}")

        # Сохраняем coordinator
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

        # Устанавливаем platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.info(f"✅ Platforms configured: {PLATFORMS}")

        # Регистрируем services
        _register_services(hass, responses_dir)

        _LOGGER.info("🎉 Zeekr integration setup COMPLETE!")
        return True

    except Exception as err:
        _LOGGER.error(f"❌ Error setting up Zeekr: {err}", exc_info=True)
        return False


def _register_services(hass: HomeAssistant, responses_dir: str) -> None:
    """Регистрирует сервисы интеграции"""

    async def handle_save_response(call: ServiceCall) -> None:
        """Сохраняет ответ сервера"""
        _LOGGER.info("📥 Manual save response called")

        try:
            if not responses_dir:
                _LOGGER.error("❌ Responses directory not configured")
                return

            filename = call.data.get(
                'filename',
                f'response_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )

            for entry_id, coord in hass.data.get(DOMAIN, {}).items():
                if isinstance(coord, ZeekrDataCoordinator) and coord.last_response:
                    filepath = os.path.join(responses_dir, filename)

                    data = {
                        "_metadata": {
                            "saved_at": datetime.now().isoformat(),
                            "description": call.data.get('description', 'Manual save'),
                        },
                        "data": coord.last_response
                    }

                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    _LOGGER.info(f"✅ Response saved to {filepath}")
                    return

            _LOGGER.warning("⚠️ No vehicle data available")

        except Exception as e:
            _LOGGER.error(f"❌ Error saving response: {e}", exc_info=True)

    async def handle_refresh_and_save(call: ServiceCall) -> None:
        """Обновляет данные и сохраняет ответ"""
        _LOGGER.info("🔄 Refresh and save called")

        try:
            if not responses_dir:
                _LOGGER.error("❌ Responses directory not configured")
                return

            for entry_id, coord in hass.data.get(DOMAIN, {}).items():
                if isinstance(coord, ZeekrDataCoordinator):
                    await coord.async_refresh()

                    if coord.last_response:
                        filename = f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        filepath = os.path.join(responses_dir, filename)

                        data = {
                            "_metadata": {
                                "saved_at": datetime.now().isoformat(),
                                "description": call.data.get('description', 'Auto refresh'),
                            },
                            "data": coord.last_response
                        }

                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)

                        _LOGGER.info(f"✅ Response auto-saved")

        except Exception as e:
            _LOGGER.error(f"❌ Error: {e}", exc_info=True)

    # Регистрируем сервисы
    hass.services.async_register(DOMAIN, 'save_response', handle_save_response)
    hass.services.async_register(DOMAIN, 'refresh_and_save', handle_refresh_and_save)

    _LOGGER.info("✅ Services registered: save_response, refresh_and_save")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Zeekr integration"""

    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id)
            _LOGGER.info("✅ Zeekr integration unloaded")

        hass.services.async_remove(DOMAIN, 'save_response')
        hass.services.async_remove(DOMAIN, 'refresh_and_save')

        return unload_ok

    except Exception as err:
        _LOGGER.error(f"❌ Error unloading Zeekr: {err}")
        return False