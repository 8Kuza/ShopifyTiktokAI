"""
Configuration module for TikTok Shop AI Sync bot.
Handles environment variables, API client initialization, and logging setup.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for managing API keys and settings."""
    
    # Shopify Configuration
    _shopify_store_raw = os.getenv('SHOPIFY_STORE', '')
    # Normalize store URL: remove https://, http://, and trailing slashes
    if _shopify_store_raw:
        _shopify_store_raw = _shopify_store_raw.strip()
        # Remove protocol if present
        if _shopify_store_raw.startswith('https://'):
            _shopify_store_raw = _shopify_store_raw[8:]
        elif _shopify_store_raw.startswith('http://'):
            _shopify_store_raw = _shopify_store_raw[7:]
        # Remove trailing slash
        _shopify_store_raw = _shopify_store_raw.rstrip('/')
    SHOPIFY_STORE = _shopify_store_raw  # e.g., 'your-store.myshopify.com'
    # Accept both SHOPIFY_TOKEN and SHOPIFY_ACCESS_TOKEN for flexibility
    SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN') or os.getenv('SHOPIFY_ACCESS_TOKEN')  # Access token for Shopify API
    SHOPIFY_API_VERSION = os.getenv('SHOPIFY_API_VERSION', '2025-10')
    
    # TikTok Shop Configuration (optional - will mock if not provided)
    TIKTOK_APP_KEY = os.getenv('TIKTOK_APP_KEY', '')
    TIKTOK_SECRET = os.getenv('TIKTOK_SECRET', '')
    TIKTOK_API_BASE = os.getenv('TIKTOK_API_BASE', 'https://partner.tiktokshop.com/api')
    
    # Mock Mode Detection
    MOCK_MODE = True if not TIKTOK_APP_KEY or not TIKTOK_APP_KEY.startswith('app_') else False
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    # Sync Settings
    SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', '300'))  # Default 5 minutes
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))  # Products per batch
    
    # Retry Settings
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_BACKOFF = float(os.getenv('RETRY_BACKOFF', '2.0'))
    
    # Notification Settings (optional)
    EMAIL_NOTIFICATIONS = os.getenv('EMAIL_NOTIFICATIONS', 'false').lower() == 'true'
    SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK', '')
    
    @classmethod
    def validate(cls, strict: bool = True):
        """
        Validate that all required configuration is present.
        
        Args:
            strict: If True, raise ValueError on missing vars. If False, log warning.
            
        Returns:
            True if validation passes
            
        Raises:
            ValueError: If required variables are missing and strict=True
        """
        required = [
            ('SHOPIFY_STORE', cls.SHOPIFY_STORE),
            ('SHOPIFY_TOKEN', cls.SHOPIFY_TOKEN),
            ('OPENAI_API_KEY', cls.OPENAI_API_KEY),
        ]
        
        missing = [name for name, value in required if not value]
        if missing:
            error_msg = f"Missing required environment variables: {', '.join(missing)}"
            if strict:
                raise ValueError(error_msg)
            else:
                logger.warning(error_msg)
                return False
        
        if cls.MOCK_MODE:
            logger.info("TikTok API keys not provided - running in MOCK MODE")
        
        logger.info("Configuration validation passed")
        return True


def setup_logging(log_level=logging.INFO, log_file='sync_bot.log'):
    """
    Setup logging configuration for console and file output.
    
    Args:
        log_level: Logging level (default: INFO)
        log_file: Path to log file (default: sync_bot.log)
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Setup handlers
    handlers = [
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


def init_shopify_client():
    """
    Initialize Shopify API client (using direct HTTP requests).
    Validation only - actual requests are made in shopify_handler.
    
    Returns:
        True if configuration is valid
    """
    if not Config.SHOPIFY_STORE or not Config.SHOPIFY_TOKEN:
        raise ValueError("Shopify store and token required")
    
    # Validate store format
    store = Config.SHOPIFY_STORE.strip()
    if not store:
        raise ValueError("SHOPIFY_STORE cannot be empty")
    if store.startswith('http://') or store.startswith('https://'):
        logger.warning(f"SHOPIFY_STORE should not include protocol. Normalized: {store} -> {store.split('://', 1)[1]}")
    if '.' not in store:
        raise ValueError(f"Invalid SHOPIFY_STORE format: '{store}'. Expected: 'your-store.myshopify.com'")
    
    logger.info(f"Shopify client configuration validated for {Config.SHOPIFY_STORE}")
    return True


def init_openai_client(max_retries: int = 3):
    """
    Initialize OpenAI API client with retry logic.
    Compatible with OpenAI library 1.51.0.
    Uses custom HTTP client to explicitly disable proxies.
    
    Args:
        max_retries: Maximum number of initialization attempts
        
    Returns:
        OpenAI client instance
        
    Raises:
        ValueError: If initialization fails after all retries
    """
    if not Config.OPENAI_API_KEY:
        raise ValueError("OpenAI API key required")
    
    import os
    import requests
    
    # Save proxy environment variables
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
                 'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy']
    saved_env = {}
    for var in proxy_vars:
        if var in os.environ:
            saved_env[var] = os.environ[var]
            # Temporarily remove to prevent OpenAI from using them
            del os.environ[var]
    
    try:
        # Create a custom HTTP client with explicit proxy settings disabled
        # This ensures no proxy is used even if environment variables are detected
        from openai import OpenAI
        
        for attempt in range(max_retries):
            try:
                # Method 1: Try with explicit http_client that has proxies disabled
                try:
                    import httpx
                    # Create httpx client with no proxies
                    http_client = httpx.Client(
                        proxies=None,  # Explicitly disable proxies
                        timeout=60.0
                    )
                    client = OpenAI(
                        api_key=Config.OPENAI_API_KEY,
                        http_client=http_client
                    )
                except (ImportError, TypeError, ValueError):
                    # Fallback: Try direct initialization without http_client
                    # If httpx is not available or http_client parameter doesn't work
                    client = OpenAI(api_key=Config.OPENAI_API_KEY)
                
                # Test the client works by checking it has the expected attribute
                if hasattr(client, 'chat'):
                    logger.info("OpenAI client initialized successfully")
                    # Restore environment variables
                    for var, value in saved_env.items():
                        os.environ[var] = value
                    return client
                else:
                    raise ValueError("OpenAI client missing expected 'chat' attribute")
            except TypeError as e:
                error_msg = str(e).lower()
                if 'proxies' in error_msg or 'unexpected keyword' in error_msg:
                    if attempt < max_retries - 1:
                        logger.warning(f"OpenAI init attempt {attempt + 1}/{max_retries} failed, retrying...")
                        # Try importing OpenAI fresh to avoid any cached state
                        import importlib
                        import sys
                        if 'openai' in sys.modules:
                            importlib.reload(sys.modules['openai'])
                        continue
                    else:
                        logger.error("OpenAI client initialization failed after all retries")
                        logger.warning("OpenAI will use fallback mock responses. Bot will continue to function.")
                        # Raise ValueError but make it clear this is expected and handled
                        error_msg = f"OpenAI client initialization failed: {e}. Bot will use mock AI responses."
                        raise ValueError(error_msg) from e
                else:
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"OpenAI init attempt {attempt + 1}/{max_retries} failed: {e}, retrying...")
                    continue
                else:
                    raise ValueError(f"OpenAI client initialization failed: {e}") from e
    finally:
        # Always restore environment variables
        for var, value in saved_env.items():
            os.environ[var] = value


# Initialize logger
logger = setup_logging()

