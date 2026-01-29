"""
Support for interface with a Sony MediaPlayer TV.

For more details about this platform, please refer to the documentation at
https://github.com/dilruacs/media_player.sony
"""
import logging
import asyncio
from homeassistant.components.media_player import MediaPlayerEntity, ENTITY_ID_FORMAT
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import SonyCoordinator
from .const import DOMAIN, SONY_COORDINATOR

_LOGGER = logging.getLogger(__name__)

SUPPORT_SONY = (
    MediaPlayerEntityFeature.PLAY |
    MediaPlayerEntityFeature.PAUSE |
    MediaPlayerEntityFeature.STOP |
    MediaPlayerEntityFeature.TURN_ON |
    MediaPlayerEntityFeature.TURN_OFF |
    MediaPlayerEntityFeature.PREVIOUS_TRACK |
    MediaPlayerEntityFeature.NEXT_TRACK
)

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Use to setup entity."""
    _LOGGER.debug("Sony async_add_entities media player")
    coordinator = hass.data[DOMAIN][config_entry.entry_id][SONY_COORDINATOR]
    async_add_entities(
        [SonyMediaPlayerEntity(coordinator)]
    )


class SonyMediaPlayerEntity(CoordinatorEntity[SonyCoordinator], MediaPlayerEntity):
    # pylint: disable=too-many-instance-attributes
    """Representation of a Sony mediaplayer."""

    def __init__(self, coordinator):
        """
        Initialize the Sony mediaplayer device.

        Mac address is optional but neccessary for wake on LAN
        """
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_state = MediaPlayerState.OFF
        self._attr_supported_features = SUPPORT_SONY
        self._unique_id = ENTITY_ID_FORMAT.format(
            f"{self.coordinator.api.host}_media_player")
        try:
            self.update()
        except Exception:  # pylint: disable=broad-except
            self._attr_state = MediaPlayerState.OFF

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
        return self._unique_id

    def update(self):
        """Update player info."""
        _LOGGER.debug("Sony media player update %s", self.coordinator.data)
        self._attr_state = self.coordinator.data.get("state")
        if (position_info := self.coordinator.data.get("position_info")) is not None:
            self._attr_media_duration = self._time_to_seconds(position_info["duration"])
            self._attr_media_position = self._time_to_seconds(position_info["position"])
            self._attr_media_position_updated_at = dt_util.utcnow()

    @property
    def name(self):
        """Return the name of the device."""
        return self.coordinator.api.nickname

    def _time_to_seconds(self, time_str):
        # API returns duration/position as "HH:MM:SS" string
        h, m, s = map(int, time_str.split(':'))
        return h * 3600 + m * 60 + s

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        await self.coordinator.device_data.async_check_device_status(
            MediaPlayerState.IDLE,
            self.coordinator.api.power, True
        )

    async def async_turn_off(self):
        """Turn off media player."""
        await self.coordinator.device_data.async_check_device_status(
            MediaPlayerState.OFF,
            self.coordinator.api.power, False
        )

    async def async_media_play_pause(self):
        """Simulate play pause media player."""
        if self._attr_state == MediaPlayerState.PLAYING:
            await self.async_media_pause()
        else:
            await self.async_media_play()

    async def async_media_play(self):
        """Send play command."""
        await self.coordinator.device_data.async_check_device_status(
            MediaPlayerState.PLAYING,
            self.coordinator.api.play
        )        

    async def async_media_pause(self):
        """Send media pause command to media player."""
        await self.coordinator.device_data.async_check_device_status(
            MediaPlayerState.PLAYING,
            self.coordinator.api.pause
        )          


    async def async_media_next_track(self):
        """Send next track command."""
        await self.coordinator.device_data.async_check_device_status(
            MediaPlayerState.PLAYING,
            self.coordinator.api.next
        ) 

    async def async_media_previous_track(self):
        """Send the previous track command."""
        await self.coordinator.device_data.async_check_device_status(
            MediaPlayerState.PLAYING,
            self.coordinator.api.prev
        ) 

    async def async_media_stop(self):
        """Send stop command."""
        await self.coordinator.device_data.async_check_device_status(
            MediaPlayerState.IDLE,
            self.coordinator.api.stop
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update only if activity changed
        self.update()
        return super()._handle_coordinator_update()