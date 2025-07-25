"""Algorithm metrics sensors for Smart Climate integration."""

import logging
from typing import Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .entity import SmartClimateSensorEntity

_LOGGER = logging.getLogger(__name__)


class SmartClimateDashboardSensor(SmartClimateSensorEntity):
    """Base class for Smart Climate dashboard sensors."""
    pass


class CorrelationCoefficientSensor(SmartClimateDashboardSensor):
    """Sensor for correlation coefficient metric."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize correlation coefficient sensor."""
        super().__init__(coordinator, base_entity_id, "correlation_coefficient", config_entry)
        self._attr_name = "Correlation Coefficient"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 3
        self._attr_icon = "mdi:chart-scatter-plot"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the correlation coefficient value."""
        if not self.coordinator.data:
            return None
        
        try:
            algorithm_metrics = self.coordinator.data.get("algorithm_metrics", {})
            value = algorithm_metrics.get("correlation_coefficient")
            if value is not None:
                return round(float(value), 3)
            return None
        except (AttributeError, TypeError, ValueError):
            return None


class PredictionVarianceSensor(SmartClimateDashboardSensor):
    """Sensor for prediction variance metric."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize prediction variance sensor."""
        super().__init__(coordinator, base_entity_id, "prediction_variance", config_entry)
        self._attr_name = "Prediction Variance"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 3
        self._attr_icon = "mdi:sigma"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the prediction variance value."""
        if not self.coordinator.data:
            return None
        
        try:
            algorithm_metrics = self.coordinator.data.get("algorithm_metrics", {})
            value = algorithm_metrics.get("prediction_variance")
            if value is not None:
                return round(float(value), 3)
            return None
        except (AttributeError, TypeError, ValueError):
            return None


class ModelEntropySensor(SmartClimateDashboardSensor):
    """Sensor for model entropy metric."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize model entropy sensor."""
        super().__init__(coordinator, base_entity_id, "model_entropy", config_entry)
        self._attr_name = "Model Entropy"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 3
        self._attr_icon = "mdi:chart-histogram"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the model entropy value."""
        if not self.coordinator.data:
            return None
        
        try:
            algorithm_metrics = self.coordinator.data.get("algorithm_metrics", {})
            value = algorithm_metrics.get("model_entropy")
            if value is not None:
                return round(float(value), 3)
            return None
        except (AttributeError, TypeError, ValueError):
            return None


class LearningRateSensor(SmartClimateDashboardSensor):
    """Sensor for learning rate metric."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize learning rate sensor."""
        super().__init__(coordinator, base_entity_id, "learning_rate", config_entry)
        self._attr_name = "Learning Rate"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 3
        self._attr_icon = "mdi:speedometer"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the learning rate value."""
        if not self.coordinator.data:
            return None
        
        try:
            algorithm_metrics = self.coordinator.data.get("algorithm_metrics", {})
            value = algorithm_metrics.get("learning_rate")
            if value is not None:
                return round(float(value), 3)
            return None
        except (AttributeError, TypeError, ValueError):
            return None


class MomentumFactorSensor(SmartClimateDashboardSensor):
    """Sensor for momentum factor metric."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize momentum factor sensor."""
        super().__init__(coordinator, base_entity_id, "momentum_factor", config_entry)
        self._attr_name = "Momentum Factor"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 3
        self._attr_icon = "mdi:motion"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the momentum factor value."""
        if not self.coordinator.data:
            return None
        
        try:
            algorithm_metrics = self.coordinator.data.get("algorithm_metrics", {})
            value = algorithm_metrics.get("momentum_factor")
            if value is not None:
                return round(float(value), 3)
            return None
        except (AttributeError, TypeError, ValueError):
            return None


class RegularizationStrengthSensor(SmartClimateDashboardSensor):
    """Sensor for regularization strength metric."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize regularization strength sensor."""
        super().__init__(coordinator, base_entity_id, "regularization_strength", config_entry)
        self._attr_name = "Regularization Strength"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 3
        self._attr_icon = "mdi:tune-vertical"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the regularization strength value."""
        if not self.coordinator.data:
            return None
        
        try:
            algorithm_metrics = self.coordinator.data.get("algorithm_metrics", {})
            value = algorithm_metrics.get("regularization_strength")
            if value is not None:
                return round(float(value), 3)
            return None
        except (AttributeError, TypeError, ValueError):
            return None


class MeanSquaredErrorSensor(SmartClimateDashboardSensor):
    """Sensor for mean squared error (MSE) metric."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize mean squared error sensor."""
        super().__init__(coordinator, base_entity_id, "mean_squared_error", config_entry)
        self._attr_name = "Mean Squared Error"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 3
        self._attr_icon = "mdi:chart-line-variant"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the mean squared error value."""
        if not self.coordinator.data:
            return None
        
        try:
            algorithm_metrics = self.coordinator.data.get("algorithm_metrics", {})
            value = algorithm_metrics.get("mean_squared_error")
            if value is not None:
                return round(float(value), 3)
            return None
        except (AttributeError, TypeError, ValueError):
            return None


class MeanAbsoluteErrorSensor(SmartClimateDashboardSensor):
    """Sensor for mean absolute error (MAE) metric."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize mean absolute error sensor."""
        super().__init__(coordinator, base_entity_id, "mean_absolute_error", config_entry)
        self._attr_name = "Mean Absolute Error"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 3
        self._attr_icon = "mdi:chart-line"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the mean absolute error value."""
        if not self.coordinator.data:
            return None
        
        try:
            algorithm_metrics = self.coordinator.data.get("algorithm_metrics", {})
            value = algorithm_metrics.get("mean_absolute_error")
            if value is not None:
                return round(float(value), 3)
            return None
        except (AttributeError, TypeError, ValueError):
            return None


class RSquaredSensor(SmartClimateDashboardSensor):
    """Sensor for R-squared (coefficient of determination) metric."""
    
    def __init__(
        self,
        coordinator,
        base_entity_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize R-squared sensor."""
        super().__init__(coordinator, base_entity_id, "r_squared", config_entry)
        self._attr_name = "R-Squared"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 3
        self._attr_icon = "mdi:chart-box"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
    
    @property
    def native_value(self) -> Optional[float]:
        """Return the R-squared value."""
        if not self.coordinator.data:
            return None
        
        try:
            algorithm_metrics = self.coordinator.data.get("algorithm_metrics", {})
            value = algorithm_metrics.get("r_squared")
            if value is not None:
                return round(float(value), 3)
            return None
        except (AttributeError, TypeError, ValueError):
            return None


# Export all sensor classes
__all__ = [
    "CorrelationCoefficientSensor",
    "PredictionVarianceSensor",
    "ModelEntropySensor",
    "LearningRateSensor",
    "MomentumFactorSensor",
    "RegularizationStrengthSensor",
    "MeanSquaredErrorSensor",
    "MeanAbsoluteErrorSensor",
    "RSquaredSensor",
]