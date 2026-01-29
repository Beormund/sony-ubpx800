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

from .const import DOMAIN, CONF_NAME, CONF_HOST, CONF_APP_PORT, CONF_IRCC_PORT, CONF_DMR_PORT, SONY_COORDINATOR, \
    SONY_API, DEFAULT_DEVICE_NAME
from .coordinator import SonyCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.REMOTE,
    Platform.BUTTON
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Unfolded Circle Remote from a config entry."""

    try:
        sony_device = SonyDevice(entry.data[CONF_HOST], DEFAULT_DEVICE_NAME,
                             psk=None, app_port=entry.data[CONF_APP_PORT],
                             dmr_port=entry.data[CONF_DMR_PORT], ircc_port=entry.data[CONF_IRCC_PORT])
        pin = entry.data.get('pin', None)
        sony_device.pin = pin
        sony_device.mac = entry.data.get('mac_address', None)

        if pin is None or pin == '0000' or pin == '':
            register_result = await hass.async_add_executor_job(sony_device.register)
            if register_result == AuthenticationResult.PIN_NEEDED:
                raise ConfigEntryAuthFailed(Exception("Authentication error"))
        else:
            pass
    except Exception as ex:
        raise ConfigEntryNotReady(ex) from ex

    _LOGGER.debug("Sony device initialization %s", vars(sony_device))
    coordinator = SonyCoordinator(hass, sony_device)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        SONY_COORDINATOR: coordinator,
        SONY_API: sony_device,
    }

    logging.getLogger("sonyapilib").setLevel(logging.CRITICAL)

    # Retrieve info from Remote
    # Get Basic Device Information
    await coordinator.async_config_entry_first_refresh()

    # Extract activities and activity groups
    # await coordinator.api.update()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Disconnect from device
    if entry.entry_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][entry.entry_id][SONY_COORDINATOR]
        await coordinator.async_disconnect()
        del hass.data[DOMAIN][entry.entry_id]

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
