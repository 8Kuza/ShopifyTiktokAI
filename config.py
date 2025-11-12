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
    SHOPIFY_STORE = os.getenv('SHOPIFY_STORE')  # e.g., 'your-store.myshopify.com'
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
    def validate(cls):
        """Validate that all required configuration is present."""
        required = [
            ('SHOPIFY_STORE', cls.SHOPIFY_STORE),
            ('SHOPIFY_TOKEN', cls.SHOPIFY_TOKEN),
            ('OPENAI_API_KEY', cls.OPENAI_API_KEY),
        ]
        
        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        if cls.MOCK_MODE:
            logger.info("TikTok API keys not provided - running in MOCK MODE")
        
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
    
    logger.info(f"Shopify client configuration validated for {Config.SHOPIFY_STORE}")
    return True


def init_openai_client():
    """
    Initialize OpenAI API client.
    
    Returns:
        OpenAI client instance
    """
    if not Config.OPENAI_API_KEY:
        raise ValueError("OpenAI API key required")
    
    return OpenAI(api_key=Config.OPENAI_API_KEY)


# Initialize logger
logger = setup_logging()

