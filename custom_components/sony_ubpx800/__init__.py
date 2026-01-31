"""The sony component."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.helpers.storage import Store
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from .device import SonyDevice, AuthenticationResult
from .sony_config import SonyConfigData

from .const import DOMAIN, CONF_HOST, CONF_APP_PORT, CONF_IRCC_PORT, CONF_DMR_PORT, SONY_COORDINATOR, \
    SONY_API, DEFAULT_DEVICE_NAME
from .coordinator import SonyCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.REMOTE,
    Platform.BUTTON
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sony UBP-X800 from a config entry."""

    # Use .get() to check options first, falling back to entry.data 
    # This ensures the 'Configure' wheel changes actually take effect.
    host = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST))
    app_port = entry.options.get(CONF_APP_PORT, entry.data.get(CONF_APP_PORT))
    dmr_port = entry.options.get(CONF_DMR_PORT, entry.data.get(CONF_DMR_PORT))
    ircc_port = entry.options.get(CONF_IRCC_PORT, entry.data.get(CONF_IRCC_PORT))

    try:
        sony_device = SonyDevice(
            host, 
            DEFAULT_DEVICE_NAME,
            psk=None, 
            app_port=app_port,
            dmr_port=dmr_port, 
            ircc_port=ircc_port
        )
        
        # PIN and MAC are usually static once paired
        pin = entry.data.get('pin', None)
        sony_device.pin = pin
        sony_device.mac = entry.data.get('mac_address', None)

        if pin is None or pin == '0000' or pin == '':
            register_result = await hass.async_add_executor_job(sony_device.register)
            if register_result == AuthenticationResult.PIN_NEEDED:
                raise ConfigEntryAuthFailed("PIN Required for Sony Device")
    except Exception as ex:
        _LOGGER.error("Failed to connect to Sony device at %s: %s", host, ex)
        raise ConfigEntryNotReady(ex) from ex

    coordinator = SonyCoordinator(hass, sony_device)
    
    # Store both the coordinator and the API for easy access
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        SONY_COORDINATOR: coordinator,
        SONY_API: sony_device,
    }

    # Silence the noisy library logging
    logging.getLogger("sonyapilib").setLevel(logging.CRITICAL)

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # This line ensures that when you click 'Save' in the configuration,
    # the 'update_listener' below is called to reload the integration.
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # 1. Unload platforms (media_player, remote, etc.)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # 2. Clean up the data stored in hass.data
    if unload_ok:
        if entry.entry_id in hass.data[DOMAIN]:
            # We remove the entry. The Python garbage collector will 
            # take care of the coordinator and device objects.
            hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    store = Store[SonyConfigData](hass, 1, "bluray.json")
    # Use the built-in async_remove method to delete the file from .storage
    try:
        await store.async_remove()
    except Exception as err:
        # Log error if deletion fails (e.g., file already gone)
        hass.components.persistent_notification.create(
            f"Error removing storage: {err}", title="Cleanup Error"
        )

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Update Listener."""
    await hass.config_entries.async_reload(entry.entry_id)
