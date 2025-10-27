"""
Configuration Loader Module

Loads and validates configuration from YAML files and environment variables.
Provides a centralized configuration object for the entire application.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class ConfigLoader:
    """Loads and manages application configuration."""
    
    def __init__(self, config_dir: str = "config", env_file: Optional[str] = None):
        """
        Initialize the configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
            env_file: Path to .env file (optional, defaults to .env in project root)
        """
        self.config_dir = Path(config_dir)
        
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()  # Load from .env in current directory
        
        self.config: Dict[str, Any] = {}
        self._load_all_configs()
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        Load a YAML configuration file.
        
        Args:
            filename: Name of the YAML file to load
            
        Returns:
            Dictionary containing the configuration
        """
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            return yaml.safe_load(f) or {}
    
    def _load_all_configs(self):
        """Load all configuration files."""
        self.config['main'] = self._load_yaml('config.yaml')
        
        self.config['strategies'] = self._load_yaml('strategies.yaml')
        
        self.config['risk'] = self._load_yaml('risk_params.yaml')
        
        self._apply_env_overrides()
        
        self._validate_config()
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        if os.getenv('TRADING_MODE'):
            self.config['main']['trading_mode'] = os.getenv('TRADING_MODE')
        
        if 'exchange' not in self.config['main']:
            self.config['main']['exchange'] = {}
        
        if 'demo_api' not in self.config['main']['exchange']:
            self.config['main']['exchange']['demo_api'] = {}
        
        if 'live_api' not in self.config['main']['exchange']:
            self.config['main']['exchange']['live_api'] = {}
        
        self.config['main']['exchange']['demo_api']['api_key'] = os.getenv('BINANCE_TESTNET_API_KEY', '')
        self.config['main']['exchange']['demo_api']['api_secret'] = os.getenv('BINANCE_TESTNET_API_SECRET', '')
        
        self.config['main']['exchange']['live_api']['api_key'] = os.getenv('BINANCE_LIVE_API_KEY', '')
        self.config['main']['exchange']['live_api']['api_secret'] = os.getenv('BINANCE_LIVE_API_SECRET', '')
        
        if os.getenv('DATABASE_URL'):
            if 'database' not in self.config['main']:
                self.config['main']['database'] = {}
            if 'sqlite' not in self.config['main']['database']:
                self.config['main']['database']['sqlite'] = {}
            self.config['main']['database']['sqlite']['url'] = os.getenv('DATABASE_URL')
        
        if os.getenv('REDIS_URL'):
            if 'database' not in self.config['main']:
                self.config['main']['database'] = {}
            if 'redis' not in self.config['main']['database']:
                self.config['main']['database']['redis'] = {}
            self.config['main']['database']['redis']['url'] = os.getenv('REDIS_URL')
        
        if os.getenv('LOG_LEVEL'):
            if 'logging' not in self.config['main']:
                self.config['main']['logging'] = {}
            self.config['main']['logging']['level'] = os.getenv('LOG_LEVEL')
        
        if os.getenv('LOG_DIR'):
            if 'logging' not in self.config['main']:
                self.config['main']['logging'] = {}
            self.config['main']['logging']['dir'] = os.getenv('LOG_DIR')
    
    def _validate_config(self):
        """Validate the loaded configuration."""
        trading_mode = self.config['main'].get('trading_mode', 'demo')
        if trading_mode not in ['demo', 'live']:
            raise ValueError(f"Invalid trading_mode: {trading_mode}. Must be 'demo' or 'live'")
        
        if 'exchange' not in self.config['main']:
            raise ValueError("Exchange configuration is missing")
        
        if 'symbols' not in self.config['main']['exchange'] or not self.config['main']['exchange']['symbols']:
            raise ValueError("No trading symbols configured")
        
        if 'timeframes' not in self.config['main']['exchange'] or not self.config['main']['exchange']['timeframes']:
            raise ValueError("No timeframes configured")
        
        if trading_mode == 'demo':
            api_config = self.config['main']['exchange'].get('demo_api', {})
        else:
            api_config = self.config['main']['exchange'].get('live_api', {})
        
        if not api_config.get('api_key') or not api_config.get('api_secret'):
            print(f"WARNING: API keys not configured for {trading_mode} mode")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the configuration value (e.g., 'main.exchange.name')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_trading_mode(self) -> str:
        """Get the current trading mode."""
        return self.config['main'].get('trading_mode', 'demo')
    
    def get_exchange_config(self) -> Dict[str, Any]:
        """Get exchange configuration for the current trading mode."""
        trading_mode = self.get_trading_mode()
        exchange_config = self.config['main']['exchange'].copy()
        
        if trading_mode == 'demo':
            exchange_config['api'] = exchange_config.get('demo_api', {})
        else:
            exchange_config['api'] = exchange_config.get('live_api', {})
        
        return exchange_config
    
    def get_symbols(self) -> list:
        """Get the list of trading symbols."""
        return self.config['main']['exchange'].get('symbols', [])
    
    def get_timeframes(self) -> list:
        """Get the list of timeframes."""
        return self.config['main']['exchange'].get('timeframes', [])
    
    def get_indicator_config(self, indicator_name: str) -> Dict[str, Any]:
        """Get configuration for a specific technical indicator."""
        return self.config['main'].get('indicators', {}).get(indicator_name, {})
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self.config['main'].get('database', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.config['main'].get('logging', {})
    
    def reload(self):
        """Reload all configuration files."""
        self.config = {}
        self._load_all_configs()


_config_instance: Optional[ConfigLoader] = None


def get_config(config_dir: str = "config", env_file: Optional[str] = None) -> ConfigLoader:
    """
    Get the global configuration instance.
    
    Args:
        config_dir: Directory containing configuration files
        env_file: Path to .env file
        
    Returns:
        ConfigLoader instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigLoader(config_dir, env_file)
    
    return _config_instance
