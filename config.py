"""
Configuration module for TikTok Shop AI Sync bot.
Handles environment variables, API client initialization, and logging setup.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
try:
    import shopify
except ImportError:
    # Fallback if shopify-python-api is not installed
    shopify = None

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for managing API keys and settings."""
    
    # Shopify Configuration
    SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
    SHOPIFY_API_SECRET = os.getenv('SHOPIFY_API_SECRET')
    SHOPIFY_STORE = os.getenv('SHOPIFY_STORE')  # e.g., 'your-store.myshopify.com'
    SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
    
    # TikTok Shop Configuration
    TIKTOK_APP_KEY = os.getenv('TIKTOK_APP_KEY')
    TIKTOK_SECRET = os.getenv('TIKTOK_SECRET')
    TIKTOK_ACCESS_TOKEN = os.getenv('TIKTOK_ACCESS_TOKEN', '')
    TIKTOK_API_BASE = os.getenv('TIKTOK_API_BASE', 'https://partner.tiktokshop.com/api')
    
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
            ('SHOPIFY_API_KEY', cls.SHOPIFY_API_KEY),
            ('SHOPIFY_STORE', cls.SHOPIFY_STORE),
            ('SHOPIFY_ACCESS_TOKEN', cls.SHOPIFY_ACCESS_TOKEN),
            ('TIKTOK_APP_KEY', cls.TIKTOK_APP_KEY),
            ('TIKTOK_SECRET', cls.TIKTOK_SECRET),
            ('OPENAI_API_KEY', cls.OPENAI_API_KEY),
        ]
        
        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
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
    Initialize Shopify API client.
    
    Returns:
        Configured Shopify session
    """
    if shopify is None:
        raise ImportError("shopify-python-api library is not installed. Install it with: pip install shopify-python-api")
    
    if not Config.SHOPIFY_STORE or not Config.SHOPIFY_ACCESS_TOKEN:
        raise ValueError("Shopify store and access token required")
    
    try:
        shopify.ShopifyResource.set_site(
            f"https://{Config.SHOPIFY_STORE}/admin/api/2024-01"
        )
        shopify.Session.setup(
            api_key=Config.SHOPIFY_API_KEY,
            secret=Config.SHOPIFY_API_SECRET
        )
        
        session = shopify.Session(
            Config.SHOPIFY_STORE,
            '2024-01',
            Config.SHOPIFY_ACCESS_TOKEN
        )
        shopify.ShopifyResource.activate_session(session)
        
        return session
    except Exception as e:
        raise ValueError(f"Failed to initialize Shopify client: {e}")


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

