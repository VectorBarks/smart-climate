"""Data Transfer Objects for Smart Climate dashboard data."""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional
from datetime import datetime

API_VERSION = "1.3.0"


@dataclass
class SeasonalData:
    """Seasonal learning information."""
    enabled: bool = False
    contribution: float = 0.0  # Percentage (0-100)
    pattern_count: int = 0
    outdoor_temp_bucket: Optional[str] = None  # e.g., "20-25°C"
    accuracy: float = 0.0  # Percentage (0-100)


@dataclass
class DelayData:
    """Delay learning information."""
    adaptive_delay: float = 0.0  # seconds
    temperature_stability_detected: bool = False
    learned_delay_seconds: float = 0.0  # seconds


@dataclass
class ACBehaviorData:
    """AC behavior learning metrics."""
    temperature_window: Optional[str] = None  # e.g., "±0.5°C"
    power_correlation_accuracy: float = 0.0  # Percentage (0-100)
    hysteresis_cycle_count: int = 0


@dataclass
class PerformanceData:
    """Performance metrics."""
    ema_coefficient: float = 0.0  # 0.0 to 1.0
    prediction_latency_ms: float = 0.0
    energy_efficiency_score: int = 0  # 0-100
    sensor_availability_score: float = 0.0  # Percentage (0-100)


@dataclass
class SystemHealthData:
    """System health metrics."""
    memory_usage_kb: float = 0.0
    persistence_latency_ms: float = 0.0
    outlier_detection_active: bool = False
    samples_per_day: float = 0.0
    accuracy_improvement_rate: float = 0.0  # Percentage per day
    convergence_trend: Optional[str] = None  # "improving", "stable", "unstable"
    # Outlier detection specific fields (Section 9.6 of c_architecture.md)
    outliers_detected_today: int = 0
    outlier_detection_threshold: float = 2.5
    last_outlier_detection_time: Optional[datetime] = None


@dataclass
class DiagnosticsData:
    """Internal performance metrics for debugging."""
    last_update_duration_ms: float = 0.0
    cache_hit_rate: float = 0.0  # 0.0 to 1.0
    cached_keys: int = 0


@dataclass
class AlgorithmMetrics:
    """Algorithm performance metrics."""
    correlation_coefficient: float = 0.0  # -1.0 to 1.0
    prediction_variance: float = 0.0
    model_entropy: float = 0.0
    learning_rate: float = 0.0  # 0.0 to 1.0
    momentum_factor: float = 0.0  # 0.0 to 1.0
    regularization_strength: float = 0.0  # 0.0 to 1.0
    mean_squared_error: float = 0.0  # MSE
    mean_absolute_error: float = 0.0  # MAE
    r_squared: float = 0.0  # 0.0 to 1.0


@dataclass
class DashboardData:
    """Main DTO for all dashboard data."""
    # --- Backward Compatibility Fields (REQUIRED) ---
    calculated_offset: float
    learning_info: Dict[str, Any]
    save_diagnostics: Dict[str, Any]
    calibration_info: Dict[str, Any]
    
    # --- Metadata ---
    api_version: str = API_VERSION
    
    # --- New Structured Fields (v1.3.0+) ---
    seasonal_data: SeasonalData = field(default_factory=SeasonalData)
    delay_data: DelayData = field(default_factory=DelayData)
    ac_behavior: ACBehaviorData = field(default_factory=ACBehaviorData)
    performance: PerformanceData = field(default_factory=PerformanceData)
    system_health: SystemHealthData = field(default_factory=SystemHealthData)
    diagnostics: DiagnosticsData = field(default_factory=DiagnosticsData)
    algorithm_metrics: AlgorithmMetrics = field(default_factory=AlgorithmMetrics)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converts the dataclass to a dictionary for JSON serialization."""
        return asdict(self)