"""
Player profile management system.

Accumulates stats across multiple Trackman CSV files per player.
"""

from .player_profile import PlayerProfile, load_player_profile, save_player_profile
from .profile_manager import ProfileManager

__all__ = ['PlayerProfile', 'load_player_profile', 'save_player_profile', 'ProfileManager']

