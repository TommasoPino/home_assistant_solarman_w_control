
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
from homeassistant.components.select import SelectEntity
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
    hass_selects = []
    for select in inverter.get_selects():
        try:
            hass_selects.append(SolarmanSelect(inverter_name, inverter, select, inverter_sn))

        except BaseException as ex:
            _LOGGER.error(f'Config error {ex} {select}')
            raise

    _LOGGER.debug(f'select.py:_do_setup_platform: async_add_entities')
    _LOGGER.debug(hass_selects)

    async_add_entities(hass_selects)

# Set-up from configuration.yaml
async def async_setup_platform(hass: HomeAssistant, config, async_add_entities : AddEntitiesCallback, discovery_info=None):
    _LOGGER.debug(f'select.py:async_setup_platform: {config}') 
    _do_setup_platform(hass, config, async_add_entities)
       
# Set-up from the entries in config-flow
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    _LOGGER.debug(f'select.py:async_setup_entry: {entry.options}') 
    _do_setup_platform(hass, entry.options, async_add_entities)
    
   

#############################################################################################################
# This is the entity seen by Home Assistant.
#  It derives from the Entity class in HA and is suited for status values.
#############################################################################################################

class SolarmanSelect(SelectEntity):
    def __init__(self, inverter_name, inverter, select, sn):
        self._inverter_name = inverter_name
        self.inverter = inverter
        self._field_name = select['name']
        self.p_state = None
        self.registers = select['registers']
        if 'icon' in select:
            self.p_icon = select['icon']
        else:
            self.p_icon = 'mdi:magnify'
        self._sn = sn
        self._options = {}
        for option in select['lookup']:
            self._options[option['key']]=option['value']
        return

    def _select_option(self,option:str):
        for key,value in self._options.items():
            if value == option:
                newvalue = key
                break
        self.inverter.write_multiple_values(self.registers[0],[newvalue])

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        self._select_option(option)


    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self._select_option(option)

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

    @property
    def current_option(self):
        #  Return the select current state.
        return self.p_state

    @property
    def options(self):
        #  Return the select options.
        return list(self._options.values())

    def update(self):
    #  Update this sensor using the data.
    #  Get the latest data and use it to update our sensor state.
    #  Retrieve the sensor data from actual interface
        # self.p_state = getattr(self.inverter, self._field_name)
        # self.inverter.update()

        val = self.inverter.get_current_val()
        if val is not None:
            if self._field_name in val:
                self.p_state = val[self._field_name]
            else:
                _LOGGER.debug(f'No value recorded for {self._field_name}')

