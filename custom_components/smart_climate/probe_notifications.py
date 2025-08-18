"""ProbeNotificationManager for Smart Climate Control.

Manages user notifications for probe scheduling events including pre-probe warnings,
completion notifications, learning milestones, and anomaly alerts.
"""

import logging
import time
from typing import Dict, List, Optional

from homeassistant.core import HomeAssistant
from .thermal_models import ProbeResult


_LOGGER = logging.getLogger(__name__)


class ProbeNotificationManager:
    """Manages user notifications for probe scheduling events."""

    def __init__(self, hass: HomeAssistant, entity_id: str):
        """Initialize the ProbeNotificationManager.
        
        Args:
            hass: Home Assistant instance
            entity_id: Entity ID for contextual notifications
        """
        self._hass = hass
        self._entity_id = entity_id
        self._logger = logging.getLogger(__name__)

    async def notify_pre_probe_warning(self, estimated_start_minutes: int) -> None:
        """Send pre-probe warning notification.
        
        Sent 15 minutes before probe starts to warn user of upcoming thermal calibration.
        Includes snooze option to delay probe by 24 hours.
        
        Args:
            estimated_start_minutes: Minutes until probe starts
        """
        title = "Smart Climate"
        message = f"Planning thermal calibration while away ({estimated_start_minutes} min)"
        
        actions = [{
            "action": "snooze_24h",
            "title": "Snooze 24h"
        }]
        
        await self._send_notification(
            title=title,
            message=message,
            persistent=True,
            actions=actions
        )

    async def notify_probe_completion(self, probe_result: ProbeResult) -> None:
        """Send probe completion notification.
        
        Notification varies based on probe outcome:
        - Success: "Successfully calibrated for [condition] conditions"
        - Partial: "Probe completed with partial data"
        - Aborted: "Probe cancelled - [reason]"
        
        Args:
            probe_result: ProbeResult containing probe outcome data
        """
        title = "Smart Climate"
        
        if probe_result.aborted:
            message = "Probe cancelled - user intervention detected"
        elif probe_result.confidence < 0.6:  # Low confidence indicates partial data
            message = "Probe completed with partial data"
        else:
            # Determine condition based on outdoor temperature
            condition = self._determine_weather_condition(probe_result.outdoor_temp)
            message = f"Successfully calibrated for {condition} conditions"
        
        await self._send_notification(
            title=title,
            message=message,
            persistent=False
        )

    async def notify_learning_milestone(self, confidence: float, milestone: str) -> None:
        """Send learning milestone notification.
        
        Notification varies based on milestone type:
        - initial: "Initial learning complete (X% confidence)"
        - optimized: "System fully optimized (X% confidence)"
        - full_diversity: "All climate conditions learned"
        
        Args:
            confidence: Current system confidence level (0.0-1.0)
            milestone: Milestone type identifier
        """
        title = "Smart Climate"
        confidence_pct = int(confidence * 100)
        
        if milestone == "initial":
            message = f"Initial learning complete ({confidence_pct}% confidence)"
        elif milestone == "optimized":
            message = f"System fully optimized ({confidence_pct}% confidence)"
        elif milestone == "full_diversity":
            message = "All climate conditions learned"
        else:
            message = f"Learning milestone reached ({confidence_pct}% confidence)"
        
        await self._send_notification(
            title=title,
            message=message,
            persistent=False
        )

    async def notify_probe_anomaly(self, anomaly_reason: str) -> None:
        """Send anomaly detection notification.
        
        Notification varies based on anomaly type:
        - unusual_readings: "Unusual reading detected - check if HVAC serviced"
        - sensor_anomaly: "Temperature sensor anomaly - check sensor placement"
        - system_error: "Probe scheduling error - check configuration"
        
        Args:
            anomaly_reason: Type of anomaly detected
        """
        title = "Smart Climate"
        
        if anomaly_reason == "unusual_readings":
            message = "Unusual reading detected - check if HVAC serviced"
        elif anomaly_reason == "sensor_anomaly":
            message = "Temperature sensor anomaly - check sensor placement"
        elif anomaly_reason == "system_error":
            message = "Probe scheduling error - check configuration"
        else:
            message = f"Anomaly detected: {anomaly_reason}"
        
        await self._send_notification(
            title=title,
            message=message,
            persistent=True
        )

    async def _send_notification(
        self, 
        title: str, 
        message: str, 
        persistent: bool = False,
        actions: Optional[List[Dict]] = None
    ) -> None:
        """Send notification via Home Assistant notification service.
        
        Args:
            title: Notification title
            message: Notification message
            persistent: Whether notification should be persistent
            actions: Optional list of notification actions
        """
        try:
            # Create unique notification ID
            notification_id = f"smart_climate_{self._entity_id}_{int(time.time())}"
            
            data = {
                "title": title,
                "message": message,
                "notification_id": notification_id
            }
            
            if persistent:
                data["persistent"] = True
                
            if actions:
                data["actions"] = actions
            
            await self._hass.services.async_call(
                "notify", "persistent_notification", data
            )
            
            self._logger.debug(
                "Sent notification: %s - %s (persistent=%s)", 
                title, message, persistent
            )
            
        except Exception as e:
            self._logger.error(
                "Failed to send notification: %s - %s. Error: %s",
                title, message, str(e)
            )

    def _determine_weather_condition(self, outdoor_temp: Optional[float]) -> str:
        """Determine weather condition description based on outdoor temperature.
        
        Args:
            outdoor_temp: Outdoor temperature in Celsius
            
        Returns:
            Weather condition description string
        """
        if outdoor_temp is None:
            return "current weather"
        
        if outdoor_temp >= 30.0:
            return "hot weather"
        elif outdoor_temp >= 20.0:
            return "warm weather"
        elif outdoor_temp >= 10.0:
            return "mild weather"
        elif outdoor_temp >= 0.0:
            return "cool weather"
        else:
            return "cold weather"