"""
ABOUTME: Dashboard module for Smart Climate Control Advanced Analytics
ABOUTME: Provides dashboard generation, tab builders, constants, and templates
"""

from .base import TabBuilder
from .constants import (
    DashboardColors,
    SENSOR_MAPPINGS,
    REFRESH_INTERVALS,
    CARD_TYPES
)
from .templates import GraphTemplates

__all__ = [
    "TabBuilder",
    "DashboardColors",
    "SENSOR_MAPPINGS", 
    "REFRESH_INTERVALS",
    "CARD_TYPES",
    "GraphTemplates"
]