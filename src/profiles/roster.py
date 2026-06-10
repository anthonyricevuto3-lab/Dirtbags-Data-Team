"""
Static roster mapping loaded from team config (config/team.local.yaml or team.example.yaml).
"""

from .team_config import get_roster_entry

__all__ = ["get_roster_entry"]
