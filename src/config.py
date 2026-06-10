"""
Configuration management for Dirtbags Data Team.
"""

import yaml
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    'data_root': 'BaseballData',
    'reports_output': 'BaseballData/{year}/{opponent}/Series_{date}/Game_{game}/Pitching/Reports',
    'trackman': {
        'auto_generate_reports': True,
        'watch_directory': 'BaseballData/{year}/{opponent}/Series_{date}/Game_{game}/Pitching/Trackman',
        'output_directory': 'BaseballData/{year}/{opponent}/Series_{date}/Game_{game}/Pitching/Reports',
    },
    'scouting': {
        'output_directory': 'BaseballData/{year}/{opponent}/Series_{date}/Scouting',
    },
    'dashboard': {
        'port': 8501,
        'host': 'localhost',
        'internal_only': True,
    },
    'logging': {
        'level': 'INFO',
        'file': 'logs/dirtbags_data_team.log',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    },
    'validation': {
        'strict_mode': False,
        'check_file_naming': True,
        'check_folder_structure': True,
    },
}


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file (default: config/config.yaml)
        
    Returns:
        Configuration dictionary
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    else:
        config_path = Path(config_path)
    
    config = DEFAULT_CONFIG.copy()
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    config.update(user_config)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}. Using defaults.")
    else:
        logger.info(f"Config file not found at {config_path}. Using defaults.")
    
    return config


def setup_logging(config: Dict[str, Any] = None):
    """
    Setup logging based on configuration.
    
    Args:
        config: Configuration dictionary (loads from file if None)
    """
    if config is None:
        config = load_config()
    
    log_config = config.get('logging', {})
    level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('file', 'logs/dirtbags_data_team.log')
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create logs directory
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )

