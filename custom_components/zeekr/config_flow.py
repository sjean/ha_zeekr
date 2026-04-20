# custom_components/zeekr/config_flow.py
"""Config flow for Zeekr integration"""

import logging
import os
import sys
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_MOBILE,
    CONF_SMS_CODE,
    CONF_JWT_TOKEN,
    CONF_REMOTE_CONTROL_VEHICLES,
)

_LOGGER = logging.getLogger(__name__)


class ZeekrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Zeekr integration."""

    VERSION = 1

    def __init__(self):
        """Initialize."""
        self.mobile = None
        self.auth = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            mobile = user_input.get(CONF_MOBILE, "").strip()

            if not mobile:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({vol.Required(CONF_MOBILE): str}),
                    errors={"base": "invalid_phone"},
                )

            try:
                # Fixed: correct import
                from .auth import ZeekrAuth

                auth = ZeekrAuth()

                def request_sms():
                    success, msg = auth.request_sms_code(mobile)
                    return success, msg

                success, msg = await self.hass.async_add_executor_job(request_sms)

                if success:
                    self.mobile = mobile
                    self.auth = auth
                    return await self.async_step_sms_code()
                else:
                    _LOGGER.error(f"Failed to send SMS: {msg}")
                    return self.async_show_form(
                        step_id="user",
                        data_schema=vol.Schema({vol.Required(CONF_MOBILE): str}),
                        errors={"base": "cannot_send_sms"},
                    )
            except Exception as e:
                _LOGGER.error(f"Error: {e}", exc_info=True)
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({vol.Required(CONF_MOBILE): str}),
                    errors={"base": "cannot_connect"},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_MOBILE): str}),
        )

    async def async_step_sms_code(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle SMS code step."""
        if user_input is not None:
            sms_code = user_input.get(CONF_SMS_CODE, "").strip()

            if not sms_code:
                return self.async_show_form(
                    step_id="sms_code",
                    data_schema=vol.Schema({vol.Required(CONF_SMS_CODE): str}),
                    errors={"base": "invalid_code"},
                )

            try:
                auth = self.auth
                mobile = self.mobile

                # Step 1: SMS login
                def sms_login():
                    success, tokens = auth.login_with_sms(mobile, sms_code)
                    return success, tokens

                success, toc_tokens = await self.hass.async_add_executor_job(
                    sms_login
                )

                if not success:
                    _LOGGER.error("SMS login failed")
                    return self.async_show_form(
                        step_id="sms_code",
                        data_schema=vol.Schema({vol.Required(CONF_SMS_CODE): str}),
                        errors={"base": "invalid_auth"},
                    )

                jwt_token = toc_tokens.get("jwtToken")
                auth.mobile = mobile

                # Step 2: Get auth code
                def get_auth_code():
                    success, code = auth.get_auth_code(jwt_token)
                    return success, code

                success, auth_code = await self.hass.async_add_executor_job(
                    get_auth_code
                )

                if not success or not auth_code:
                    _LOGGER.error("Failed to get auth code")
                    return self.async_show_form(
                        step_id="sms_code",
                        data_schema=vol.Schema({vol.Required(CONF_SMS_CODE): str}),
                        errors={"base": "cannot_get_auth_code"},
                    )

                # Step 3: Login with auth code
                def auth_code_login():
                    success, tokens = auth.login_with_auth_code(auth_code)
                    return success, tokens

                success, secure_tokens = await self.hass.async_add_executor_job(
                    auth_code_login
                )

                if not success or not secure_tokens:
                    _LOGGER.error("Failed to get secure tokens")
                    return self.async_show_form(
                        step_id="sms_code",
                        data_schema=vol.Schema({vol.Required(CONF_SMS_CODE): str}),
                        errors={"base": "cannot_get_secure_tokens"},
                    )

                _LOGGER.info("✅ Authentication successful!")

                # Create the config entry with tokens
                await self.async_set_unique_id("zeekr_main")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Zeekr {mobile}",
                    data={
                        "mobile": mobile,
                        # Save tokens in the config entry
                        CONF_JWT_TOKEN: secure_tokens.get("jwtToken"),
                        "accessToken": secure_tokens.get("accessToken"),
                        "refreshToken": secure_tokens.get("refreshToken"),
                        "userId": secure_tokens.get("userId"),
                        "clientId": secure_tokens.get("clientId"),
                        "device_id": secure_tokens.get("device_id"),
                        CONF_REMOTE_CONTROL_VEHICLES: secure_tokens.get(
                            CONF_REMOTE_CONTROL_VEHICLES,
                            {},
                        ),
                    },
                )

            except Exception as e:
                _LOGGER.error(f"Error: {e}", exc_info=True)
                return self.async_show_form(
                    step_id="sms_code",
                    data_schema=vol.Schema({vol.Required(CONF_SMS_CODE): str}),
                    errors={"base": "cannot_connect"},
                )

        return self.async_show_form(
            step_id="sms_code",
            data_schema=vol.Schema({vol.Required(CONF_SMS_CODE): str}),
        )
