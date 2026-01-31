"""The IntelliFire integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.error import HTTPError

import requests
from homeassistant.const import STATE_OFF, STATE_ON, STATE_PLAYING, STATE_PAUSED, STATE_IDLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store
from .device import SonyDevice, HttpMethod
from .sony_config import SonyConfigData

from .const import DEVICE_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

class SonyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Data update coordinator for an Sony device."""
    # List of events to subscribe to the websocket
    subscribe_events: dict[str, bool]

    def __init__(self, hass: HomeAssistant, sony_device) -> None:
        """Initialize the Coordinator."""
        super().__init__(
            hass,
            name=DOMAIN,
            logger=_LOGGER,
            update_interval=DEVICE_SCAN_INTERVAL,
        )
        self.hass = hass
        self.api: SonyDevice = sony_device
        self.device_data = SonyDeviceData(self)
        self.data = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Get the latest data from the Sony device."""
        _LOGGER.debug("Sony device coordinator update")
        try:
            await self.device_data.update_state()
            self.data = {
                "state": self.device_data.state,
                "position_info": self.device_data.position_info
            }
            return self.data
        except Exception as ex:
            _LOGGER.error("Sony device coordinator error during update", ex)
            raise UpdateFailed(
                f"Error communicating with Sony device API {ex}"
            ) from ex


class SonyDeviceData:
    def __init__(self, coordinator: SonyCoordinator):
        self.coordinator = coordinator
        self.store = Store[SonyConfigData](self.coordinator.hass, 1, "bluray.json")
        self.state = STATE_OFF
        self.position_info: dict | None = None
        self._task_running = False
        self._lock = asyncio.Lock()
        self._init = False
        
    async def save_device(self):
        """Save the device to disk."""
        sony_device = self.coordinator.api
        data = await self.coordinator.hass.async_add_executor_job(sony_device.save_to_json)
        await self.store.async_save(data)
          
    async def retrieve_device(self):
        data = await self.store.async_load()
        if data is not None:
            return await self.coordinator.hass.async_add_executor_job(SonyDevice.load_from_json, data)
        return data
    
    async def async_check_device_status(self, state, func, *args):
        async with self._lock:
            if self._task_running:
                return
            else:
                self._task_running = True
        await self.coordinator.hass.async_add_executor_job(func, *args)
        for _  in range(10):
            await self.coordinator.async_request_refresh()
            if self.state == state:
                async with self._lock:
                    self._task_running = False
                return
            await asyncio.sleep(3)
        async with self._lock:
            self._task_running = False

    async def init_device(self):
        """If not previously registered, initialize the device by reading necessary resources."""
        if (sony_device := await self.retrieve_device()) is not None:
            self.coordinator.api = sony_device
            self._init = True
            return
        sony_device = self.coordinator.api
        
        try:
            response = await self.coordinator.hass.async_add_executor_job(sony_device._send_http,sony_device.dmr_url, HttpMethod.GET)
        except requests.exceptions.ConnectionError:
            _LOGGER.debug("Sony device connection error, waiting next call")
            response = None
        except requests.exceptions.RequestException as exc:
            _LOGGER.error("Failed to get DMR: %s: %s", type(exc), exc)
            return

        try:
            if response:
                _LOGGER.debug("Sony device connection ready, proceed to init device")
                await self.coordinator.hass.async_add_executor_job(sony_device.init_device)
                await self.save_device()
                self._init = True
            else:
                _LOGGER.debug("Sony device connection not ready, wait next call")
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.error("Failed to get device information: %s, wait next call", str(ex))

    async def update_state(self) -> None:
        """Update device info."""
        if not self._init:
            await self.init_device()
            if not self._init:
                return

        # Retrieve the latest data.
        try:
            playback_info = await self.coordinator.hass.async_add_executor_job(
                self.coordinator.api.get_playing_status
            )
            match playback_info:
                case "PLAYING":
                    self.state = STATE_PLAYING
                case "PAUSED_PLAYBACK":
                    self.state = STATE_PAUSED
                case "OFF":
                    self.state = STATE_OFF
                case "IDLE":
                    self.state = STATE_IDLE
                case _:
                    self.state = STATE_ON
            
            if self.state == STATE_OFF:
                return
            
            position_info = await self.coordinator.hass.async_add_executor_job(
                self.coordinator.api.get_position_info
            )
            if position_info is not None:
                self.position_info = position_info

                    
        except Exception as exception_instance:  # pylint: disable=broad-except
            _LOGGER.error("Sony device error", exception_instance)
            self.state = STATE_OFF
