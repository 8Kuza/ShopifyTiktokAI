"""
Main orchestration module for Shopify-Only AI Sync Bot with Mock TikTok.
Handles CLI, scheduling, Flask health endpoint, and coordination of sync operations.
"""

import argparse
import logging
import time
import sys
import traceback
from typing import Optional

# Setup basic logging first before any other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from flask import Flask
    
    from config import Config, setup_logging
    from shopify_handler import ShopifyHandler
    from tiktok_handler import TikTokHandler
    from ai_mapper import AIMapper
    
    # Re-initialize logging with proper setup after config is loaded
    setup_logging()
except Exception as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

# Initialize Flask app for health endpoint (Render deployment)
app = Flask(__name__)


class SyncBot:
    """Main sync bot orchestrator."""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize sync bot.
        
        Args:
            dry_run: If True, simulate operations without making API calls
        """
        self.dry_run = dry_run
        self.shopify = ShopifyHandler(dry_run=dry_run)
        self.tiktok = TikTokHandler(dry_run=dry_run)
        self.ai_mapper = AIMapper(dry_run=dry_run)
        self.scheduler = None
        
        logger.info(f"Sync bot initialized (dry_run={dry_run})")
    
    def sync_inventory(self) -> dict:
        """
        Sync inventory from Shopify to TikTok Shop.
        
        Returns:
            Dictionary with sync results
        """
        logger.info("Starting inventory sync...")
        results = {
            'success': 0,
            'failed': 0,
            'total': 0
        }
        
        try:
            # Fetch inventory levels from Shopify
            inventory_levels = self.shopify.get_inventory_levels()
            results['total'] = len(inventory_levels)
            
            if not inventory_levels:
                logger.warning("No inventory levels found")
                return results
            
            # Prepare inventory updates for TikTok
            inventory_updates = []
            for level in inventory_levels:
                sku = level.get('sku')
                if not sku:
                    continue
                
                inventory_updates.append({
                    'sku': sku,
                    'quantity': level.get('available', 0),
                })
            
            if not inventory_updates:
                logger.warning("No valid inventory updates to sync")
                return results
            
            # Bulk update TikTok inventory
            if self.tiktok.bulk_update_inventory(inventory_updates):
                results['success'] = len(inventory_updates)
                logger.info(f"Inventory sync completed: {results['success']} items updated")
            else:
                results['failed'] = len(inventory_updates)
                logger.error("Inventory sync failed")
            
        except Exception as e:
            logger.error(f"Error during inventory sync: {e}")
            results['failed'] = results.get('total', 0)
        
        return results
    
    def sync_products(self, limit: Optional[int] = None) -> dict:
        """
        Sync products from Shopify with AI optimization (mock TikTok until approval).
        
        Args:
            limit: Optional limit on number of products to sync
            
        Returns:
            Dictionary with sync results
        """
        logger.info("Starting product sync with AI optimization...")
        results = {
            'success': 0,
            'failed': 0,
            'total': 0,
            'product_ids': []
        }
        
        try:
            # Fetch products from Shopify
            products = self.shopify.get_all_products(limit=limit or 250)
            if limit:
                products = products[:limit]
            
            results['total'] = len(products)
            
            if not products:
                logger.warning("No products found")
                return results
            
            logger.info(f"Found {len(products)} products to sync")
            
            # Map products using AI for TikTok optimization
            logger.info("Optimizing products with AI (OpenAI gpt-4o-mini)...")
            tiktok_products = self.ai_mapper.batch_map_products(products)
            
            # Push to TikTok (will mock if keys not provided)
            logger.info("Pushing optimized products to TikTok Shop...")
            create_results = self.tiktok.bulk_create_products(tiktok_products)
            
            results['success'] = create_results.get('success', 0)
            results['failed'] = create_results.get('failed', 0)
            results['product_ids'] = create_results.get('product_ids', [])
            
            logger.info(f"Product sync completed: {results['success']} success, {results['failed']} failed")
            
        except Exception as e:
            logger.error(f"Error during product sync: {e}")
            results['failed'] = results.get('total', 0)
        
        return results
    
    def sync_orders(self) -> dict:
        """
        Sync orders from TikTok Shop to Shopify for fulfillment.
        
        Returns:
            Dictionary with sync results
        """
        logger.info("Starting order sync...")
        results = {
            'success': 0,
            'failed': 0,
            'total': 0
        }
        
        try:
            # Fetch recent orders from TikTok
            tiktok_orders = self.tiktok.get_orders(limit=50)
            results['total'] = len(tiktok_orders)
            
            if not tiktok_orders:
                logger.info("No new orders found")
                return results
            
            logger.info(f"Found {len(tiktok_orders)} orders to process")
            
            # Process each order
            for order in tiktok_orders:
                try:
                    order_id = order.get('order_id')
                    line_items = order.get('line_items', [])
                    
                    # Create order in Shopify (or match existing)
                    # This would typically involve creating a draft order or matching by SKU
                    logger.info(f"Processing order {order_id} with {len(line_items)} items")
                    
                    # For now, just log the order
                    # In production, implement order creation/matching logic
                    results['success'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing order {order.get('order_id')}: {e}")
                    results['failed'] += 1
            
            logger.info(f"Order sync completed: {results['success']} success, {results['failed']} failed")
            
        except Exception as e:
            logger.error(f"Error during order sync: {e}")
            results['failed'] = results.get('total', 0)
        
        return results
    
    def update_order_tracking(self, order_id: str, tracking_number: str,
                             tracking_url: Optional[str] = None,
                             carrier: Optional[str] = None) -> bool:
        """
        Update tracking information for a TikTok order.
        
        Args:
            order_id: TikTok order ID
            tracking_number: Tracking number
            tracking_url: Optional tracking URL
            carrier: Optional carrier name
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Updating tracking for order {order_id}")
        return self.tiktok.update_order_tracking(order_id, tracking_number, tracking_url, carrier)
    
    def run_full_sync(self):
        """Run full sync (inventory + products)."""
        logger.info("=" * 60)
        logger.info("Starting FULL SYNC (Shopify → AI Optimization → Mock TikTok)")
        logger.info("=" * 60)
        
        # Sync inventory
        inv_results = self.sync_inventory()
        logger.info(f"Inventory sync: {inv_results}")
        
        # Sync products with AI optimization
        prod_results = self.sync_products()
        logger.info(f"Product sync: {prod_results}")
        
        logger.info("=" * 60)
        logger.info("FULL SYNC COMPLETED")
        logger.info("=" * 60)
    
    def start_scheduler(self, interval: int = 300):
        """
        Start scheduled sync operations.
        
        Args:
            interval: Sync interval in seconds (default: 300 = 5 minutes)
        """
        logger.info(f"Starting scheduler with {interval}s interval")
        
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self.run_full_sync,
            trigger=IntervalTrigger(seconds=interval),
            id='full_sync',
            name='Full Sync Job',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def stop_scheduler(self):
        """Stop the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")


@app.route('/health')
def health():
    """Health check endpoint for Render deployment."""
    return "AI Sync Bot Running", 200


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Shopify-Only AI Sync Bot - Sync inventory and products from Shopify with AI optimization (Mock TikTok until approval)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['full', 'inventory', 'products'],
        default='full',
        help='Sync mode: full (all), inventory, or products (default: full)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=None,
        help='Sync interval in seconds (for continuous mode). If not set, runs once.'
    )
    
    parser.add_argument(
        '--dry-run',
        '--dry',
        action='store_true',
        dest='dry_run',
        help='Dry run mode (simulate without API calls)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of products to sync (for testing)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    try:
        args = parse_args()
        
        # Setup logging
        log_level = getattr(logging, args.log_level.upper())
        setup_logging(log_level=log_level)
        
        logger.info("=" * 60)
        logger.info("Starting Shopify-Only AI Sync Bot")
        logger.info("=" * 60)
        
        # Validate configuration
        try:
            Config.validate(strict=True)
            logger.info("Configuration validated successfully")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            logger.error("Please check your .env file and ensure all required variables are set:")
            logger.error("  - SHOPIFY_STORE (e.g., your-store.myshopify.com)")
            logger.error("  - SHOPIFY_TOKEN (Shopify Admin API access token)")
            logger.error("  - OPENAI_API_KEY (OpenAI API key)")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Failed during startup: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    # Initialize bot with error handling
    try:
        bot = SyncBot(dry_run=args.dry_run)
        logger.info("Sync bot initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize sync bot: {e}")
        logger.error("This may be due to:")
        logger.error("  1. Missing or invalid API keys")
        logger.error("  2. Network connectivity issues")
        logger.error("  3. API service unavailability")
        logger.error("Try running with --dry-run to test configuration")
        sys.exit(1)
    
    # Run sync based on mode
    try:
        if args.interval:
            # Continuous mode with scheduler and Flask
            bot.start_scheduler(interval=args.interval)
            logger.info(f"Bot running in continuous mode (interval: {args.interval}s). Flask health endpoint available at /health")
            logger.info("Press Ctrl+C to stop.")
            
            # Run Flask in a separate thread for health endpoint
            import threading
            flask_thread = threading.Thread(
                target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False),
                daemon=True
            )
            flask_thread.start()
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Stopping bot...")
                bot.stop_scheduler()
        else:
            # Single run mode
            if args.mode == 'full':
                bot.run_full_sync()
            elif args.mode == 'inventory':
                results = bot.sync_inventory()
                logger.info(f"Inventory sync results: {results}")
            elif args.mode == 'products':
                results = bot.sync_products(limit=args.limit)
                logger.info(f"Product sync results: {results}")
    
    except Exception as e:
        logger.error(f"Error during sync: {e}")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

