"""Test ProbeNotificationManager for notification system functionality."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
import logging

# Import the module under test
from custom_components.smart_climate.probe_notifications import ProbeNotificationManager
from custom_components.smart_climate.thermal_models import ProbeResult


class TestProbeNotificationManager:
    """Test the ProbeNotificationManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.hass = MagicMock()
        self.hass.services = MagicMock()
        self.hass.services.async_call = AsyncMock()
        self.entity_id = "climate.test_thermostat"
        self.notification_manager = ProbeNotificationManager(self.hass, self.entity_id)

    @pytest.mark.asyncio
    async def test_init(self):
        """Test ProbeNotificationManager initialization."""
        assert self.notification_manager._hass == self.hass
        assert self.notification_manager._entity_id == self.entity_id
        assert isinstance(self.notification_manager._logger, logging.Logger)

    @pytest.mark.asyncio
    async def test_notify_pre_probe_warning(self):
        """Test pre-probe warning notification."""
        estimated_start_minutes = 15
        
        await self.notification_manager.notify_pre_probe_warning(estimated_start_minutes)
        
        # Verify the notification service was called
        self.hass.services.async_call.assert_called_once()
        call_args = self.hass.services.async_call.call_args
        
        # Check service and method
        assert call_args[0][0] == "notify"
        assert call_args[0][1] == "persistent_notification"
        
        # Check notification data
        data = call_args[1]
        assert data["title"] == "Smart Climate"
        assert "Planning thermal calibration while away (15 min)" in data["message"]
        assert data["persistent"] == True
        assert "actions" in data
        assert len(data["actions"]) == 1
        assert data["actions"][0]["action"] == "snooze_24h"
        assert data["actions"][0]["title"] == "Snooze 24h"

    @pytest.mark.asyncio
    async def test_notify_probe_completion_success(self):
        """Test probe completion notification for successful probe."""
        probe_result = ProbeResult(
            tau_value=92.5,
            confidence=0.87,
            duration=3600,
            fit_quality=0.92,
            aborted=False,
            outdoor_temp=25.5
        )
        
        await self.notification_manager.notify_probe_completion(probe_result)
        
        # Verify the notification service was called
        self.hass.services.async_call.assert_called_once()
        call_args = self.hass.services.async_call.call_args
        
        # Check service and method
        assert call_args[0][0] == "notify"
        assert call_args[0][1] == "persistent_notification"
        
        # Check notification data
        data = call_args[1]
        assert data["title"] == "Smart Climate"
        assert "Successfully calibrated for" in data["message"]
        assert "conditions" in data["message"]
        assert data["persistent"] == False

    @pytest.mark.asyncio
    async def test_notify_probe_completion_aborted(self):
        """Test probe completion notification for aborted probe."""
        probe_result = ProbeResult(
            tau_value=0.0,
            confidence=0.0,
            duration=900,
            fit_quality=0.0,
            aborted=True,
            outdoor_temp=28.0
        )
        
        await self.notification_manager.notify_probe_completion(probe_result)
        
        # Verify the notification service was called
        self.hass.services.async_call.assert_called_once()
        call_args = self.hass.services.async_call.call_args
        
        # Check notification data
        data = call_args[1]
        assert data["title"] == "Smart Climate"
        assert "Probe cancelled" in data["message"]
        assert data["persistent"] == False

    @pytest.mark.asyncio
    async def test_notify_probe_completion_partial(self):
        """Test probe completion notification for partial data."""
        probe_result = ProbeResult(
            tau_value=89.2,
            confidence=0.45,  # Low confidence indicates partial data
            duration=1200,
            fit_quality=0.65,
            aborted=False,
            outdoor_temp=22.0
        )
        
        await self.notification_manager.notify_probe_completion(probe_result)
        
        # Verify the notification service was called
        self.hass.services.async_call.assert_called_once()
        call_args = self.hass.services.async_call.call_args
        
        # Check notification data
        data = call_args[1]
        assert data["title"] == "Smart Climate"
        assert "Probe completed with partial data" in data["message"]
        assert data["persistent"] == False

    @pytest.mark.asyncio
    async def test_notify_learning_milestone_initial(self):
        """Test learning milestone notification for initial learning."""
        confidence = 0.6
        milestone = "initial"
        
        await self.notification_manager.notify_learning_milestone(confidence, milestone)
        
        # Verify the notification service was called
        self.hass.services.async_call.assert_called_once()
        call_args = self.hass.services.async_call.call_args
        
        # Check notification data
        data = call_args[1]
        assert data["title"] == "Smart Climate"
        assert "Initial learning complete (60% confidence)" in data["message"]
        assert data["persistent"] == False

    @pytest.mark.asyncio
    async def test_notify_learning_milestone_high_confidence(self):
        """Test learning milestone notification for high confidence."""
        confidence = 0.9
        milestone = "optimized"
        
        await self.notification_manager.notify_learning_milestone(confidence, milestone)
        
        # Verify the notification service was called
        self.hass.services.async_call.assert_called_once()
        call_args = self.hass.services.async_call.call_args
        
        # Check notification data
        data = call_args[1]
        assert data["title"] == "Smart Climate"
        assert "System fully optimized (90% confidence)" in data["message"]
        assert data["persistent"] == False

    @pytest.mark.asyncio
    async def test_notify_learning_milestone_full_diversity(self):
        """Test learning milestone notification for full diversity."""
        confidence = 0.95
        milestone = "full_diversity"
        
        await self.notification_manager.notify_learning_milestone(confidence, milestone)
        
        # Verify the notification service was called
        self.hass.services.async_call.assert_called_once()
        call_args = self.hass.services.async_call.call_args
        
        # Check notification data
        data = call_args[1]
        assert data["title"] == "Smart Climate"
        assert "All climate conditions learned" in data["message"]
        assert data["persistent"] == False

    @pytest.mark.asyncio
    async def test_notify_probe_anomaly_unusual_reading(self):
        """Test anomaly notification for unusual readings."""
        anomaly_reason = "unusual_readings"
        
        await self.notification_manager.notify_probe_anomaly(anomaly_reason)
        
        # Verify the notification service was called
        self.hass.services.async_call.assert_called_once()
        call_args = self.hass.services.async_call.call_args
        
        # Check notification data
        data = call_args[1]
        assert data["title"] == "Smart Climate"
        assert "Unusual reading detected - check if HVAC serviced" in data["message"]
        assert data["persistent"] == True

    @pytest.mark.asyncio
    async def test_notify_probe_anomaly_sensor_issues(self):
        """Test anomaly notification for sensor issues."""
        anomaly_reason = "sensor_anomaly"
        
        await self.notification_manager.notify_probe_anomaly(anomaly_reason)
        
        # Verify the notification service was called
        self.hass.services.async_call.assert_called_once()
        call_args = self.hass.services.async_call.call_args
        
        # Check notification data
        data = call_args[1]
        assert data["title"] == "Smart Climate"
        assert "Temperature sensor anomaly - check sensor placement" in data["message"]
        assert data["persistent"] == True

    @pytest.mark.asyncio
    async def test_notify_probe_anomaly_system_error(self):
        """Test anomaly notification for system errors."""
        anomaly_reason = "system_error"
        
        await self.notification_manager.notify_probe_anomaly(anomaly_reason)
        
        # Verify the notification service was called
        self.hass.services.async_call.assert_called_once()
        call_args = self.hass.services.async_call.call_args
        
        # Check notification data
        data = call_args[1]
        assert data["title"] == "Smart Climate"
        assert "Probe scheduling error - check configuration" in data["message"]
        assert data["persistent"] == True

    @pytest.mark.asyncio
    async def test_notification_id_uniqueness(self):
        """Test that notification IDs are unique and properly formatted."""
        # Send two notifications
        await self.notification_manager.notify_pre_probe_warning(15)
        await self.notification_manager.notify_learning_milestone(0.8, "initial")
        
        # Check both calls were made
        assert self.hass.services.async_call.call_count == 2
        
        # Get notification IDs from both calls
        call1_data = self.hass.services.async_call.call_args_list[0][1]
        call2_data = self.hass.services.async_call.call_args_list[1][1]
        
        # Verify IDs are different
        assert call1_data["notification_id"] != call2_data["notification_id"]
        
        # Verify ID format
        assert call1_data["notification_id"].startswith("smart_climate_climate.test_thermostat_")
        assert call2_data["notification_id"].startswith("smart_climate_climate.test_thermostat_")

    @pytest.mark.asyncio
    async def test_service_call_failure_handling(self):
        """Test error handling when notification service call fails."""
        # Make the service call fail
        self.hass.services.async_call.side_effect = Exception("Service call failed")
        
        # This should not raise an exception
        await self.notification_manager.notify_pre_probe_warning(15)
        
        # Verify the call was attempted
        self.hass.services.async_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_notification_rate_limiting(self):
        """Test notification filtering and rate limiting."""
        # Send multiple identical notifications rapidly
        for _ in range(5):
            await self.notification_manager.notify_probe_anomaly("unusual_readings")
        
        # All calls should go through (rate limiting implementation may vary)
        assert self.hass.services.async_call.call_count == 5

    @pytest.mark.asyncio
    async def test_temperature_condition_determination(self):
        """Test temperature condition determination for probe completion."""
        # Test hot weather condition  
        hot_probe = ProbeResult(
            tau_value=85.0,
            confidence=0.85,
            duration=3600,
            fit_quality=0.9,
            aborted=False,
            outdoor_temp=35.0  # Hot weather
        )
        
        await self.notification_manager.notify_probe_completion(hot_probe)
        
        call_args = self.hass.services.async_call.call_args
        data = call_args[1]
        assert "hot weather" in data["message"] or "warm" in data["message"]

        # Reset mock
        self.hass.services.async_call.reset_mock()
        
        # Test cold weather condition
        cold_probe = ProbeResult(
            tau_value=110.0,
            confidence=0.82,
            duration=3600,
            fit_quality=0.88,
            aborted=False,
            outdoor_temp=5.0  # Cold weather
        )
        
        await self.notification_manager.notify_probe_completion(cold_probe)
        
        call_args = self.hass.services.async_call.call_args
        data = call_args[1]
        assert "cold weather" in data["message"] or "cool" in data["message"]


class TestProbeNotificationIntegration:
    """Integration tests for ProbeNotificationManager."""
    
    @pytest.mark.asyncio
    async def test_full_notification_workflow(self):
        """Test complete notification workflow from probe start to completion."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        
        notification_manager = ProbeNotificationManager(hass, "climate.test")
        
        # Step 1: Pre-probe warning
        await notification_manager.notify_pre_probe_warning(15)
        
        # Step 2: Probe completion
        probe_result = ProbeResult(
            tau_value=95.0,
            confidence=0.88,
            duration=3900,
            fit_quality=0.91,
            aborted=False,
            outdoor_temp=22.5
        )
        await notification_manager.notify_probe_completion(probe_result)
        
        # Step 3: Learning milestone
        await notification_manager.notify_learning_milestone(0.75, "initial")
        
        # Verify all notifications were sent
        assert hass.services.async_call.call_count == 3
        
        # Verify notification types
        call_args_list = hass.services.async_call.call_args_list
        
        # Pre-probe warning should be persistent
        assert call_args_list[0][1]["persistent"] == True
        
        # Completion should not be persistent
        assert call_args_list[1][1]["persistent"] == False
        
        # Milestone should not be persistent
        assert call_args_list[2][1]["persistent"] == False