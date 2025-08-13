"""ABOUTME: Core humidity sensor entities providing indoor, outdoor, and differential humidity measurements.
Implements the first 3 humidity sensors as specified in the humidity monitoring architecture."""

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from typing import Optional
from .humidity_monitor import HumidityMonitor


class HumiditySensorEntity(SensorEntity):
    """Base class for humidity monitoring sensors."""
    
    def __init__(self, monitor: HumidityMonitor, sensor_type: str):
        """Initialize base humidity sensor.
        
        Args:
            monitor: HumidityMonitor instance for data access
            sensor_type: Unique sensor type identifier (e.g., "indoor_humidity")
        """
        super().__init__()
        self._monitor = monitor
        self._sensor_type = sensor_type
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = self._get_device_class()
        self._attr_native_unit_of_measurement = self._get_unit()
        self._attr_available = True
    
    @property
    def name(self) -> str:
        """Return human-readable sensor name."""
        return f"Smart Climate {self._sensor_type.replace('_', ' ').title()}"
    
    @property
    def unique_id(self) -> str:
        """Return unique sensor identifier."""
        return f"smart_climate_{self._sensor_type}"
    
    def _get_device_class(self) -> Optional[SensorDeviceClass]:
        """Return device class for sensor type. Override in subclasses."""
        return None
    
    def _get_unit(self) -> str:
        """Return unit of measurement. Override in subclasses if needed."""
        return PERCENTAGE
    
    async def async_update(self) -> None:
        """Update sensor state from HumidityMonitor. Override in subclasses."""
        data = await self._monitor.async_get_sensor_data()
        value = data.get(self._sensor_type)
        
        self._attr_native_value = value
        self._attr_available = value is not None


class IndoorHumiditySensor(HumiditySensorEntity):
    """Sensor for indoor humidity percentage."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize indoor humidity sensor."""
        super().__init__(monitor, "indoor_humidity")
    
    def _get_device_class(self) -> SensorDeviceClass:
        """Return humidity device class."""
        return SensorDeviceClass.HUMIDITY


class OutdoorHumiditySensor(HumiditySensorEntity):
    """Sensor for outdoor humidity percentage."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize outdoor humidity sensor."""
        super().__init__(monitor, "outdoor_humidity")
    
    def _get_device_class(self) -> SensorDeviceClass:
        """Return humidity device class."""
        return SensorDeviceClass.HUMIDITY


class HumidityDifferentialSensor(HumiditySensorEntity):
    """Sensor for humidity differential (indoor - outdoor)."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize humidity differential sensor."""
        super().__init__(monitor, "humidity_differential")
    
    def _get_device_class(self) -> Optional[SensorDeviceClass]:
        """Return None - differential doesn't use humidity device class."""
        return None


class HeatIndexSensor(HumiditySensorEntity):
    """Sensor for heat index (feels-like temperature) in degrees Celsius."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize heat index sensor."""
        super().__init__(monitor, "heat_index")
    
    def _get_device_class(self) -> SensorDeviceClass:
        """Return temperature device class for heat index."""
        return SensorDeviceClass.TEMPERATURE
    
    def _get_unit(self) -> str:
        """Return Celsius unit for temperature measurement."""
        return UnitOfTemperature.CELSIUS


class IndoorDewPointSensor(HumiditySensorEntity):
    """Sensor for indoor dew point temperature in degrees Celsius."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize indoor dew point sensor."""
        super().__init__(monitor, "dew_point_indoor")
    
    def _get_device_class(self) -> SensorDeviceClass:
        """Return temperature device class for dew point."""
        return SensorDeviceClass.TEMPERATURE
    
    def _get_unit(self) -> str:
        """Return Celsius unit for temperature measurement."""
        return UnitOfTemperature.CELSIUS


class OutdoorDewPointSensor(HumiditySensorEntity):
    """Sensor for outdoor dew point temperature in degrees Celsius."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize outdoor dew point sensor."""
        super().__init__(monitor, "dew_point_outdoor")
    
    def _get_device_class(self) -> SensorDeviceClass:
        """Return temperature device class for dew point."""
        return SensorDeviceClass.TEMPERATURE
    
    def _get_unit(self) -> str:
        """Return Celsius unit for temperature measurement."""
        return UnitOfTemperature.CELSIUS


class AbsoluteHumiditySensor(HumiditySensorEntity):
    """Sensor for absolute humidity in grams per cubic meter."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize absolute humidity sensor."""
        super().__init__(monitor, "absolute_humidity")
    
    def _get_device_class(self) -> Optional[SensorDeviceClass]:
        """Return None - no device class for g/m³ unit."""
        return None
    
    def _get_unit(self) -> str:
        """Return g/m³ unit for absolute humidity measurement."""
        return "g/m³"


class MLHumidityOffsetSensor(HumiditySensorEntity):
    """Sensor for humidity's contribution to ML offset prediction in degrees Celsius."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize ML humidity offset sensor."""
        super().__init__(monitor, "ml_humidity_offset")
    
    def _get_device_class(self) -> Optional[SensorDeviceClass]:
        """Return None - no device class for offset contribution."""
        return None
    
    def _get_unit(self) -> str:
        """Return Celsius unit for offset contribution."""
        return UnitOfTemperature.CELSIUS


class MLHumidityConfidenceSensor(HumiditySensorEntity):
    """Sensor for humidity's impact on ML prediction confidence as percentage change."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize ML humidity confidence sensor."""
        super().__init__(monitor, "ml_humidity_confidence")
    
    def _get_device_class(self) -> Optional[SensorDeviceClass]:
        """Return None - no device class for confidence impact."""
        return None
    
    def _get_unit(self) -> str:
        """Return percentage unit for confidence impact."""
        return PERCENTAGE


class MLHumidityWeightSensor(HumiditySensorEntity):
    """Sensor for humidity's relative importance in ML model as percentage weight."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize ML humidity weight sensor."""
        super().__init__(monitor, "ml_humidity_weight")
    
    def _get_device_class(self) -> Optional[SensorDeviceClass]:
        """Return None - no device class for feature importance."""
        return None
    
    def _get_unit(self) -> str:
        """Return percentage unit for feature weight."""
        return PERCENTAGE


class HumiditySensorStatusSensor(HumiditySensorEntity):
    """Sensor for humidity sensor availability and reliability status."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize humidity sensor status sensor."""
        super().__init__(monitor, "humidity_sensor_status")
    
    def _get_device_class(self) -> Optional[SensorDeviceClass]:
        """Return None - no device class for status strings."""
        return None
    
    def _get_unit(self) -> str:
        """Return empty string - status is a text value."""
        return ""
    
    async def async_update(self) -> None:
        """Update sensor state from HumidityMonitor."""
        data = await self._monitor.async_get_sensor_data()
        value = data.get(self._sensor_type)
        
        # For text sensors, always mark as available if we have a value
        self._attr_native_value = value if value is not None else "Unknown"
        self._attr_available = True


class HumidityComfortLevelSensor(HumiditySensorEntity):
    """Sensor for humidity comfort level assessment."""
    
    def __init__(self, monitor: HumidityMonitor):
        """Initialize humidity comfort level sensor."""
        super().__init__(monitor, "humidity_comfort_level")
    
    def _get_device_class(self) -> Optional[SensorDeviceClass]:
        """Return None - no device class for comfort level strings."""
        return None
    
    def _get_unit(self) -> str:
        """Return empty string - comfort level is a text value."""
        return ""
    
    async def async_update(self) -> None:
        """Update sensor state from HumidityMonitor."""
        data = await self._monitor.async_get_sensor_data()
        value = data.get(self._sensor_type)
        
        # For text sensors, always mark as available if we have a value
        self._attr_native_value = value if value is not None else "Unknown"
        self._attr_available = True