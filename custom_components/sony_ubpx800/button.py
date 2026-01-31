"""
Support for interface with a Sony Remote.

For more details about this platform, please refer to the documentation at
https://github.com/dilruacs/media_player.sony
"""
from __future__ import annotations

import logging
import asyncio
from typing import Any

from homeassistant.components.button import (
    ButtonEntity,
    ENTITY_ID_FORMAT
)
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

ICON_MAP = {
    "Num0": "mdi:numeric-0",
    "Num1": "mdi:numeric-1",
    "Num2": "mdi:numeric-2",
    "Num3": "mdi:numeric-3",
    "Num4": "mdi:numeric-4",
    "Num5": "mdi:numeric-5",
    "Num6": "mdi:numeric-6",
    "Num7": "mdi:numeric-7",
    "Num8": "mdi:numeric-8",
    "Num9": "mdi:numeric-9",    
    "Power": "mdi:power",
    "Eject": "mdi:eject",
    "Stop": "mdi:stop",
    "Pause": "mdi:pause",
    "Rewind": "mdi:rewind",
    "Forward": "mdi:fast-forward",
    "PopUpMenu": "mdi:dots-horizontal",
    "TopMenu": "mdi:menu",
    "Up": "mdi:menu-up",
    "Down": "mdi:menu-down",
    "Left": "mdi:menu-left",
    "Right": "mdi:menu-right",
    "Confirm": "mdi:check-circle",
    "Options": "mdi:dots-vertical",
    "Display": "mdi:information-outline",
    "Home": "mdi:home-outline",
    "Return": "mdi:undo",
    "Karaoke": "mdi:microphone",
    "Netflix": "mdi:netflix",
    "Mode3d": "mdi:3d",
    "Next": "mdi:skip-forward",
    "Prev": "mdi:skip-backward",
    "Favorites": "mdi:star",
    "SubTitle": "mdi:subtitles",
    "Audio": "mdi:surround-sound",
    "Angle": "mdi:camera-switch",
    "Blue": "mdi:alpha-b-circle-outline",
    "Red": "mdi:alpha-r-circle-outline",
    "Green": "mdi:alpha-g-circle-outline",
    "Yellow": "mdi:alpha-y-circle-outline",
    "Replay": "mdi:replay",
    "Advance": "mdi:fast-forward-10",
    "Play": "mdi:play"
}

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Use to setup entity."""
    _LOGGER.debug("Sony async_add_entities button")
    coordinator = hass.data[DOMAIN][config_entry.entry_id][SONY_COORDINATOR]
    # For each command generate a button
    commands = coordinator.api.commands
    entities = [SonyButtonEntity(coordinator, command) for command in commands]
    async_add_entities(entities)

class SonyButtonEntity(CoordinatorEntity[SonyCoordinator], ButtonEntity):
    # pylint: disable=too-many-instance-attributes
    """Representation of a Sony Remote Button."""

    def __init__(self, coordinator, command):
        """Initialize the Sony remote button."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._command = command
        self._attr_name = command
        self._attr_icon = ICON_MAP.get(command, "mdi:gesture-tap-button")
        self._attr_unique_id = ENTITY_ID_FORMAT.format(
            f"{self.coordinator.api.host}_{command}")
        self._state_map = {
            "Stop": STATE_IDLE,
            "Play": STATE_PLAYING,
            "Pause": STATE_PLAYING,
            "Next": STATE_PLAYING,
            "Prev": STATE_PLAYING,
            "Advance": STATE_PLAYING,
            "Replay": STATE_PLAYING,
            "Home": STATE_IDLE      
        }

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
            model=self.coordinator.api.client_id
        )

    @property
    def unique_id(self) -> str | None:
        return self._attr_unique_id
    
    def _toggle_power_state(self):
        return STATE_IDLE if self.coordinator.device_data.state == STATE_OFF else STATE_OFF

    @property
    def name(self):
        """Return the name of the device."""
        return self._attr_name

    async def async_press(self) -> None:
        """Send command to device."""
        if self._command == "Power":
            # If device is powered off and this button is a power button, use the Power(power_on)
            # function father than send_command. Power(True) sends a Wake-On-Lan magic packet.
            power_on = True if self.coordinator.device_data.state == STATE_OFF else False
            await self.coordinator.device_data.async_check_device_status(
                self._toggle_power_state(),  
                self.coordinator.api.power, power_on
            )
        elif (state := self._state_map.get(self._command)) is not None:
            await self.coordinator.device_data.async_check_device_status(
                state,
                self.coordinator.api.send_command, self._command
            ) 
        else:
            await self.coordinator.hass.async_add_executor_job(
                self.coordinator.api.send_command, self._command
            )
