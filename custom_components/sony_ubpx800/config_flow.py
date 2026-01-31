"""Config flow for Sony UBP-X800 integration."""

from __future__ import annotations
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .device import SonyDevice, AuthenticationResult
from .const import (
    DOMAIN, 
    CONF_APP_PORT, 
    DEFAULT_APP_PORT, 
    CONF_DMR_PORT, 
    DEFAULT_DMR_PORT, 
    CONF_IRCC_PORT, 
    DEFAULT_IRCC_PORT, 
    CONF_PIN, 
    DEFAULT_DEVICE_NAME
)

_LOGGER = logging.getLogger(__name__)

# Initial setup schema
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Optional(CONF_PIN, default="0000"): str,
    vol.Optional(CONF_APP_PORT, default=DEFAULT_APP_PORT): int,
    vol.Optional(CONF_DMR_PORT, default=DEFAULT_DMR_PORT): int,
    vol.Optional(CONF_IRCC_PORT, default=DEFAULT_IRCC_PORT): int
})

# Schema for the PIN entry step
STEP_PIN_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_PIN, default="0000"): str
})

def validate_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    pin = user_input.get(CONF_PIN)
    _LOGGER.debug("Sony device user input %s", user_input)
    
    sony_device = SonyDevice(
        user_input[CONF_HOST], 
        DEFAULT_DEVICE_NAME,
        psk=None, 
        app_port=user_input[CONF_APP_PORT],
        dmr_port=user_input[CONF_DMR_PORT], 
        ircc_port=user_input[CONF_IRCC_PORT]
    )
    
    authenticated = False
    if pin == '0000' or pin is None or pin == '':
        register_result = sony_device.register()
        if register_result == AuthenticationResult.SUCCESS:
            authenticated = True
        elif register_result == AuthenticationResult.PIN_NEEDED:
            config = {"error": AuthenticationResult.PIN_NEEDED}
            config.update(user_input)
            return config
        else:
            _LOGGER.error("An unknown error occurred during registration")

    if not authenticated:
        authenticated = sony_device.send_authentication(pin)

    config = {
        "authenticated": authenticated,
        "mac_address": sony_device.mac
    }
    config.update(user_input)
    return config


class SonyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sony device."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Sony Config Flow."""
        self.user_input: dict[str, Any] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SonyDeviceOptionsFlowHandler:
        """This enables the 'Configure' button (gear icon) on the integration card."""
        return SonyDeviceOptionsFlowHandler()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is None or user_input == {}:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )

        if self.user_input is None:
            self.user_input = user_input
        else:
            self.user_input.update(user_input)

        try:
            info = await self.hass.async_add_executor_job(validate_input, self.user_input)
            if info.get("error") == AuthenticationResult.PIN_NEEDED:
                errors["base"] = "invalid_auth"
                return self.async_show_form(
                    step_id="user", data_schema=STEP_PIN_DATA_SCHEMA, errors=errors,
                )
        except Exception:
            _LOGGER.exception("Unexpected exception during validation")
            errors["base"] = "unknown"
        else:
            if not errors:
                await self.async_set_unique_id(self.user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=DEFAULT_DEVICE_NAME, data=info)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class SonyDeviceOptionsFlowHandler(OptionsFlow):
    """Handle options flow for the Sony device."""

    def __init__(self) -> None:
        """Initialize options flow."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options settings."""
        if user_input is not None:
            # This creates an entry in entry.options
            return self.async_create_entry(title="", data=user_input)

        # Pre-populate the form with current settings
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_HOST, 
                    default=self.config_entry.options.get(CONF_HOST, self.config_entry.data.get(CONF_HOST))
                ): str,
                vol.Optional(
                    CONF_APP_PORT, 
                    default=self.config_entry.options.get(CONF_APP_PORT, self.config_entry.data.get(CONF_APP_PORT))
                ): int,
                vol.Optional(
                    CONF_DMR_PORT, 
                    default=self.config_entry.options.get(CONF_DMR_PORT, self.config_entry.data.get(CONF_DMR_PORT))
                ): int,
                vol.Optional(
                    CONF_IRCC_PORT, 
                    default=self.config_entry.options.get(CONF_IRCC_PORT, self.config_entry.data.get(CONF_IRCC_PORT))
                ): int,
            }),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""