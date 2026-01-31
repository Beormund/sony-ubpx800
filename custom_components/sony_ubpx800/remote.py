"""
Support for interface with a Sony Remote.

For more details about this platform, please refer to the documentation at
https://github.com/dilruacs/media_player.sony
"""
from __future__ import annotations

import logging
import asyncio
from typing import Iterable, Any

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_HOLD_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    DEFAULT_HOLD_SECS,
    DEFAULT_NUM_REPEATS,
    RemoteEntity,
    RemoteEntityFeature, ENTITY_ID_FORMAT)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_IDLE,
    STATE_PLAYING
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SonyCoordinator
from .const import DOMAIN, SONY_COORDINATOR, DEFAULT_DEVICE_NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Use to setup entity."""
    _LOGGER.debug("Sony async_add_entities remote")
    coordinator = hass.data[DOMAIN][config_entry.entry_id][SONY_COORDINATOR]
    async_add_entities(
        [SonyRemoteEntity(coordinator)]
    )

class SonyRemoteEntity(CoordinatorEntity[SonyCoordinator], RemoteEntity):
    """Representation of a Sony mediaplayer."""
    _attr_has_entity_name = True
    _attr_name = "Remote"
    _attr_icon = "mdi:remote-tv"
    _attr_supported_features = RemoteEntityFeature.ACTIVITY

    def __init__(self, coordinator):
        """
        Initialize the Sony remote device.

        Mac address is optional but neccessary for wake on LAN
        """
        super().__init__(coordinator)
        self.coordinator = coordinator

        # Clean the MAC address (remove dashes/colons) and use it as the unique ID
        clean_mac = coordinator.api.mac.replace("-", "").replace(":", "")
        self._attr_unique_id = f"{clean_mac}_remote"


        self._state_map = {
            "Power": lambda: self.toggled_state(),
            "Stop": STATE_IDLE,
            "Play": STATE_PLAYING,
            "Pause": STATE_PLAYING,
            "Next": STATE_PLAYING,
            "Prev": STATE_PLAYING,
            "Advance": STATE_PLAYING,
            "Replay": STATE_PLAYING,
            "Home": STATE_IDLE      
        }
        self._attr_state = STATE_OFF
        self.update()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Mac address is unique identifiers within a specific domain
                (DOMAIN, self.coordinator.api.mac)
            },
            name=self.coordinator.api.nickname,
            manufacturer="Sony",
            model="UBP-X800"
        )

    def toggled_state(self):
        return STATE_ON if self._attr_state == STATE_OFF else STATE_IDLE

    def update(self):
        """Update TV info."""
        _LOGGER.debug("Sony remote control update %s", self.coordinator.data)
        self._attr_state = self.coordinator.data.get("state", STATE_OFF)

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        await self.coordinator.device_data.async_check_device_status(
            STATE_IDLE,
            self.coordinator.api.power, True
        )

    async def async_turn_off(self):
        """Turn off media player."""
        await self.coordinator.device_data.async_check_device_status(
            STATE_OFF,
            self.coordinator.api.power, False
        )

    async def async_toggle(self, activity: str = None, **kwargs):
        """Toggle a device."""
        if self._attr_state == STATE_OFF:
            await self.async_turn_on()
        else:
            await self.async_turn_off()

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send commands to one device."""
        num_repeats = kwargs.get(ATTR_NUM_REPEATS, DEFAULT_NUM_REPEATS)
        delay_secs = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)
        # hold_secs = kwargs.get(ATTR_HOLD_SECS, DEFAULT_HOLD_SECS)
        _LOGGER.debug("async_send_command %s %d repeats %d delay", ''.join(list(command)), num_repeats, delay_secs)

        for _ in range(num_repeats):
            for single_command in command:
                if single_command not in self.coordinator.api.commands:
                    continue
                if (state := self._state_map.get(single_command)) is not None:
                    await self.coordinator.device_data.async_check_device_status(
                        state() if callable(state) else state,
                        self.coordinator.api.send_command, single_command
                    ) 
                else:
                    await self.coordinator.hass.async_add_executor_job(
                        self.coordinator.api.send_command, single_command
                    )
                await asyncio.sleep(delay_secs)                

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update()
        self.async_write_ha_state()
