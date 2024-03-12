
################################################################################
#   Solarman local interface.
#
#   This component can retrieve data from the solarman dongle using version 5
#   of the protocol.
#
###############################################################################

import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import *
from .solarman import Inverter, inverters
from .scanner import InverterScanner

_LOGGER = logging.getLogger(__name__)
_inverter_scanner = InverterScanner()

def _do_setup_platform(hass: HomeAssistant, config, async_add_entities : AddEntitiesCallback):
    _LOGGER.debug(f'selectpy:async_setup_platform: {config}') 
   
    inverter_name = config.get(CONF_NAME)
    inverter_host = config.get(CONF_INVERTER_HOST)
    if inverter_host == "0.0.0.0":
        inverter_host = _inverter_scanner.get_ipaddress()
        
   
    inverter_port = config.get(CONF_INVERTER_PORT)
    inverter_sn = config.get(CONF_INVERTER_SERIAL)
    if inverter_sn == 0:
        inverter_sn = _inverter_scanner.get_serialno()
    
    inverter_mb_slaveid = config.get(CONF_INVERTER_MB_SLAVEID)
    if not inverter_mb_slaveid:
        inverter_mb_slaveid = DEFAULT_INVERTER_MB_SLAVEID
    lookup_file = config.get(CONF_LOOKUP_FILE)
    path = hass.config.path(PATH_INVERTER_DEF)

    # Check input configuration.
    if inverter_host is None:
        raise vol.Invalid('configuration parameter [inverter_host] does not have a value')
    if inverter_sn is None:
        raise vol.Invalid('configuration parameter [inverter_serial] does not have a value')

    # in order to avoid several initialization of the same inverter a singleton is used
    if inverter_sn not in inverters.keys():
        inverters[inverter_sn] = Inverter(path, inverter_sn, inverter_host, inverter_port, inverter_mb_slaveid, lookup_file)
    inverter = inverters[inverter_sn]

    #  Prepare the sensor entities.
    hass_buttons = []
    for button in inverter.get_buttons():
        try:
            hass_buttons.append(SolarmanButton(inverter_name, inverter, button, inverter_sn))

        except BaseException as ex:
            _LOGGER.error(f'Config error {ex} {button}')
            raise

    _LOGGER.debug(f'button.py:_do_setup_platform: async_add_entities')
    _LOGGER.debug(hass_buttons)

    async_add_entities(hass_buttons)

# Set-up from configuration.yaml
async def async_setup_platform(hass: HomeAssistant, config, async_add_entities : AddEntitiesCallback, discovery_info=None):
    _LOGGER.debug(f'button.py:async_setup_platform: {config}') 
    _do_setup_platform(hass, config, async_add_entities)
       
# Set-up from the entries in config-flow
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    _LOGGER.debug(f'button.py:async_setup_entry: {entry.options}') 
    _do_setup_platform(hass, entry.options, async_add_entities)
    
   

#############################################################################################################
# This is the entity seen by Home Assistant.
#  It derives from the Entity class in HA and is suited for status values.
#############################################################################################################

class SolarmanButton(ButtonEntity):
    def __init__(self, inverter_name, inverter, button, sn):
        self._inverter_name = inverter_name
        self.inverter = inverter
        self._field_name = button['name']
        self.p_state = None
        self.registers = button['registers']
        if 'icon' in button:
            self.p_icon = button['icon']
        else:
            self.p_icon = 'mdi:magnify'
        self._sn = sn

    def _press_button(self):
        self.inverter.write_multiple_values(self.registers[0],[1])

    def press(self) -> None:
        """Handle the button press."""
        self._press_button()

    async def async_press(self) -> None:
        """Handle the button press."""
        self._press_button()

    @property
    def icon(self):
        #  Return the icon of the sensor. """
        return self.p_icon

    @property
    def name(self):
        #  Return the name of the sensor.
        return "{} {}".format(self._inverter_name, self._field_name)

    @property
    def unique_id(self):
        # Return a unique_id based on the serial number
        return "{}_{}_{}".format(self._inverter_name, self._sn, self._field_name)


    def update(self):
    #  Update this sensor using the data.
    #  Get the latest data and use it to update our sensor state.
    #  Retrieve the sensor data from actual interface
        self.p_state = getattr(self.inverter, self._field_name)
        # self.inverter.update()

        # val = self.inverter.get_current_val()
        # if val is not None:
        #     if self._field_name in val:
        #         self.p_state = val[self._field_name]
        #     else:
        #         _LOGGER.debug(f'No value recorded for {self._field_name}')

