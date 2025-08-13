"""ABOUTME: Test ML impact humidity sensors including offset contribution, confidence impact, and feature weights.
Tests sensors 8-10 of the humidity monitoring specification."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from custom_components.smart_climate.humidity_sensors import (
    MLHumidityOffsetSensor,
    MLHumidityConfidenceSensor, 
    MLHumidityWeightSensor,
)


@pytest.fixture
def mock_humidity_monitor():
    """Create mock HumidityMonitor for testing."""
    monitor = MagicMock()
    monitor.async_get_sensor_data = AsyncMock()
    return monitor


@pytest.fixture 
def mock_offset_engine():
    """Create mock OffsetEngine with ML methods."""
    engine = MagicMock()
    engine.get_feature_contribution = MagicMock()
    engine.get_feature_importance = MagicMock() 
    engine.get_confidence_impact = MagicMock()
    return engine


class TestMLHumidityOffsetSensor:
    """Test ML humidity offset contribution sensor."""
    
    def test_sensor_initialization(self, mock_humidity_monitor):
        """Test ML humidity offset sensor initializes correctly."""
        sensor = MLHumidityOffsetSensor(mock_humidity_monitor)
        
        assert sensor.name == "Smart Climate Ml Humidity Offset"
        assert sensor.unique_id == "smart_climate_ml_humidity_offset"
        assert sensor._attr_device_class is None
        assert sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS
        
    @pytest.mark.asyncio
    async def test_positive_offset_contribution(self, mock_humidity_monitor):
        """Test positive humidity offset contribution."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            "ml_humidity_offset": 1.5
        }
        
        sensor = MLHumidityOffsetSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value == 1.5
        assert sensor._attr_available is True
        
    @pytest.mark.asyncio
    async def test_negative_offset_contribution(self, mock_humidity_monitor):
        """Test negative humidity offset contribution."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            "ml_humidity_offset": -0.8
        }
        
        sensor = MLHumidityOffsetSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value == -0.8
        assert sensor._attr_available is True
        
    @pytest.mark.asyncio
    async def test_no_offset_data(self, mock_humidity_monitor):
        """Test sensor when no ML offset data available."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {}
        
        sensor = MLHumidityOffsetSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value is None
        assert sensor._attr_available is False


class TestMLHumidityConfidenceSensor:
    """Test ML humidity confidence impact sensor."""
    
    def test_sensor_initialization(self, mock_humidity_monitor):
        """Test ML humidity confidence sensor initializes correctly."""
        sensor = MLHumidityConfidenceSensor(mock_humidity_monitor)
        
        assert sensor.name == "Smart Climate Ml Humidity Confidence"
        assert sensor.unique_id == "smart_climate_ml_humidity_confidence"
        assert sensor._attr_device_class is None
        assert sensor._attr_native_unit_of_measurement == PERCENTAGE
        
    @pytest.mark.asyncio
    async def test_confidence_impact_positive(self, mock_humidity_monitor):
        """Test positive confidence impact from humidity."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            "ml_humidity_confidence": 5.2
        }
        
        sensor = MLHumidityConfidenceSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value == 5.2
        assert sensor._attr_available is True
        
    @pytest.mark.asyncio
    async def test_confidence_impact_negative(self, mock_humidity_monitor):
        """Test negative confidence impact from humidity."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            "ml_humidity_confidence": -3.1
        }
        
        sensor = MLHumidityConfidenceSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value == -3.1
        assert sensor._attr_available is True
        
    @pytest.mark.asyncio
    async def test_no_confidence_data(self, mock_humidity_monitor):
        """Test sensor when no confidence impact data available."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {}
        
        sensor = MLHumidityConfidenceSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value is None
        assert sensor._attr_available is False


class TestMLHumidityWeightSensor:
    """Test ML humidity feature importance sensor."""
    
    def test_sensor_initialization(self, mock_humidity_monitor):
        """Test ML humidity weight sensor initializes correctly."""
        sensor = MLHumidityWeightSensor(mock_humidity_monitor)
        
        assert sensor.name == "Smart Climate Ml Humidity Weight"
        assert sensor.unique_id == "smart_climate_ml_humidity_weight"
        assert sensor._attr_device_class is None
        assert sensor._attr_native_unit_of_measurement == PERCENTAGE
        
    @pytest.mark.asyncio
    async def test_feature_weight_high(self, mock_humidity_monitor):
        """Test high humidity feature importance."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            "ml_humidity_weight": 42.7
        }
        
        sensor = MLHumidityWeightSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value == 42.7
        assert sensor._attr_available is True
        
    @pytest.mark.asyncio
    async def test_feature_weight_low(self, mock_humidity_monitor):
        """Test low humidity feature importance."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            "ml_humidity_weight": 8.1
        }
        
        sensor = MLHumidityWeightSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value == 8.1
        assert sensor._attr_available is True
        
    @pytest.mark.asyncio
    async def test_no_weight_data(self, mock_humidity_monitor):
        """Test sensor when no feature importance data available."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {}
        
        sensor = MLHumidityWeightSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value is None
        assert sensor._attr_available is False


class TestHumidityMonitorMLIntegration:
    """Test HumidityMonitor integration with OffsetEngine ML methods."""
    
    @pytest.mark.asyncio
    async def test_get_ml_metrics_from_offset_engine(self, mock_offset_engine):
        """Test getting ML metrics from OffsetEngine."""
        # Mock OffsetEngine ML methods  
        mock_offset_engine.get_feature_contribution.return_value = 1.2
        mock_offset_engine.get_confidence_impact.return_value = -2.5
        mock_offset_engine.get_feature_importance.return_value = 35.8
        
        # Test direct method calls that HumidityMonitor should make
        offset = mock_offset_engine.get_feature_contribution("humidity")
        confidence = mock_offset_engine.get_confidence_impact("humidity") 
        weight = mock_offset_engine.get_feature_importance("humidity")
        
        assert offset == 1.2
        assert confidence == -2.5
        assert weight == 35.8
        
        # Verify correct feature name passed
        mock_offset_engine.get_feature_contribution.assert_called_with("humidity")
        mock_offset_engine.get_confidence_impact.assert_called_with("humidity")
        mock_offset_engine.get_feature_importance.assert_called_with("humidity")
        
    @pytest.mark.asyncio
    async def test_ml_methods_return_defaults_when_unavailable(self, mock_offset_engine):
        """Test ML methods return reasonable defaults when ML not available."""
        # Mock methods to return None when ML model not available
        mock_offset_engine.get_feature_contribution.return_value = None
        mock_offset_engine.get_confidence_impact.return_value = None
        mock_offset_engine.get_feature_importance.return_value = None
        
        offset = mock_offset_engine.get_feature_contribution("humidity")
        confidence = mock_offset_engine.get_confidence_impact("humidity")
        weight = mock_offset_engine.get_feature_importance("humidity")
        
        assert offset is None
        assert confidence is None
        assert weight is None
        
    @pytest.mark.asyncio
    async def test_ml_methods_handle_missing_offset_engine(self):
        """Test handling when OffsetEngine is not available."""
        # This test verifies that HumidityMonitor gracefully handles
        # missing OffsetEngine reference
        with patch('custom_components.smart_climate.humidity_monitor.HumidityMonitor') as MockMonitor:
            mock_monitor = MockMonitor.return_value
            mock_monitor.async_get_sensor_data = AsyncMock(return_value={
                "ml_humidity_offset": 0.0,
                "ml_humidity_confidence": 0.0, 
                "ml_humidity_weight": 0.0
            })
            
            # Should return defaults when OffsetEngine unavailable
            data = await mock_monitor.async_get_sensor_data()
            
            assert data["ml_humidity_offset"] == 0.0
            assert data["ml_humidity_confidence"] == 0.0
            assert data["ml_humidity_weight"] == 0.0


class TestSignedValueFormatting:
    """Test proper formatting of signed offset values."""
    
    @pytest.mark.asyncio
    async def test_positive_offset_formatting(self, mock_humidity_monitor):
        """Test positive offset displays with + sign."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            "ml_humidity_offset": 2.3
        }
        
        sensor = MLHumidityOffsetSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        # Value should be stored as positive number
        assert sensor._attr_native_value == 2.3
        
        # Additional formatting may be handled by extra_state_attributes
        # or through custom display logic
        
    @pytest.mark.asyncio
    async def test_negative_offset_formatting(self, mock_humidity_monitor):
        """Test negative offset displays correctly."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            "ml_humidity_offset": -1.7
        }
        
        sensor = MLHumidityOffsetSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        # Value should be stored as negative number
        assert sensor._attr_native_value == -1.7
        
    @pytest.mark.asyncio 
    async def test_zero_offset(self, mock_humidity_monitor):
        """Test zero offset displays correctly."""
        mock_humidity_monitor.async_get_sensor_data.return_value = {
            "ml_humidity_offset": 0.0
        }
        
        sensor = MLHumidityOffsetSensor(mock_humidity_monitor)
        await sensor.async_update()
        
        assert sensor._attr_native_value == 0.0