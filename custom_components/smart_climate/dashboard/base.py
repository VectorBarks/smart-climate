"""Base classes for Smart Climate Advanced Analytics Dashboard.

This module provides the abstract base classes and interfaces for building
dashboard tabs in the Advanced Analytics Dashboard system.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class TabBuilder(ABC):
    """Abstract base class for building dashboard tabs.
    
    Each tab builder is responsible for generating the cards and configuration
    for a specific tab in the Advanced Analytics Dashboard. This ensures
    consistent interface and structure across all tab implementations.
    
    The TabBuilder uses a template-based approach where concrete implementations
    define the specific cards and metadata for their respective tabs.
    """
    
    @abstractmethod
    def build_cards(self, entity_id: str) -> List[Dict[str, Any]]:
        """Build all cards for this tab.
        
        This method generates the complete list of Home Assistant dashboard cards
        for the tab. Each card is a dictionary containing the card configuration
        that will be used in the YAML dashboard template.
        
        Args:
            entity_id: The base entity ID for the climate component (e.g., 'living_room')
                      Used to construct sensor entity names like 'sensor.{entity_id}_offset'
        
        Returns:
            List of card dictionaries, each containing Home Assistant card configuration.
            Example:
                [
                    {'type': 'gauge', 'entity': 'sensor.living_room_offset'},
                    {'type': 'history-graph', 'entities': ['sensor.living_room_temp']}
                ]
        
        Raises:
            NotImplementedError: If not implemented by concrete subclass.
        """
        pass
    
    @abstractmethod
    def get_tab_config(self) -> Dict[str, str]:
        """Get tab metadata configuration.
        
        This method returns the metadata needed to configure the tab in the 
        Home Assistant dashboard, including display name, icon, and URL path.
        
        Returns:
            Dictionary containing tab metadata with required keys:
            - 'title': Display name of the tab
            - 'icon': Material Design Icon name (e.g., 'mdi:view-dashboard')
            - 'path': URL path for the tab (e.g., 'overview')
            
            Example:
                {
                    'title': 'Overview',
                    'icon': 'mdi:view-dashboard', 
                    'path': 'overview'
                }
        
        Raises:
            NotImplementedError: If not implemented by concrete subclass.
        """
        pass