"""
Report generation modules.
"""

from .trackman_report import generate_trackman_report
from .single_outing_643 import generate_single_outing_643
from .outing_one_pager import generate_outing_one_pager

__all__ = ['generate_trackman_report', 'generate_single_outing_643', 'generate_outing_one_pager']

