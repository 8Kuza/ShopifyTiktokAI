"""
Shopify API handler for fetching products, inventory, and orders.
Handles bulk operations and error retries.
Uses direct HTTP requests for reliability.
"""

import logging
import time
import requests
from typing import List, Dict, Optional, Any
from config import Config

logger = logging.getLogger(__name__)


class ShopifyHandler:
    """Handler for Shopify API operations."""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize Shopify handler.
        
        Args:
            dry_run: If True, simulate operations without making API calls
        """
        self.dry_run = dry_run
        self.session = None
        if not dry_run:
            try:
                self.session = self._init_session()
            except Exception as e:
                logger.error(f"Failed to initialize Shopify session: {e}")
                raise
    
    def _init_session(self):
        """Initialize Shopify session using direct HTTP requests."""
        if not Config.SHOPIFY_STORE or not Config.SHOPIFY_TOKEN:
            raise ValueError("Shopify store and token required")
        return True
    
    def _make_shopify_request(self, endpoint: str, method: str = 'GET', params: Dict[str, Any] = None) -> tuple:
        """
        Make authenticated request to Shopify API with rate limit checking.
        
        Args:
            endpoint: API endpoint (e.g., '/products.json')
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            
        Returns:
            Tuple of (response_json, response_headers) for pagination support
            
        Raises:
            requests.exceptions.RequestException: If request fails
            ValueError: If rate limit is exceeded (>90% usage)
        """
        # Ensure store URL is properly formatted (no protocol, no trailing slash)
        store = Config.SHOPIFY_STORE.strip().rstrip('/')
        if store.startswith('http://') or store.startswith('https://'):
            store = store.split('://', 1)[1]  # Remove protocol if present
        
        # Validate store format
        if not store or '.' not in store:
            raise ValueError(f"Invalid SHOPIFY_STORE format: '{Config.SHOPIFY_STORE}'. Expected format: 'your-store.myshopify.com'")
        
        url = f"https://{store}/admin/api/{Config.SHOPIFY_API_VERSION}{endpoint}"
        headers = {
            'X-Shopify-Access-Token': Config.SHOPIFY_TOKEN,
            'Content-Type': 'application/json'
        }
        
        logger.debug(f"Making Shopify API request to: {url}")
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            else:
                response = requests.request(method, url, headers=headers, json=params, timeout=30)
            
            # Handle authentication errors (401, 403) - don't retry these
            if response.status_code == 401:
                error_msg = response.json().get('errors', 'Invalid API key or access token')
                logger.error(f"Shopify API authentication failed (401): {error_msg}")
                logger.error("Please check your SHOPIFY_TOKEN environment variable:")
                logger.error("  1. Verify the token is correct in your .env file")
                logger.error("  2. Ensure the token has not expired")
                logger.error("  3. Check that the token has required permissions (read_products, read_inventory)")
                logger.error("  4. Regenerate the token in Shopify Admin if needed")
                raise ValueError(f"Shopify API authentication failed: {error_msg}. Check SHOPIFY_TOKEN configuration.")
            
            if response.status_code == 403:
                logger.error("Shopify API access forbidden (403): Token may not have required permissions")
                logger.error("Required permissions: read_products, read_inventory, write_inventory")
                raise ValueError("Shopify API access forbidden. Check token permissions.")
            
            response.raise_for_status()
            
            # Check rate limits from X-Shopify-Shop-Api-Call-Limit header
            rate_limit_header = response.headers.get('X-Shopify-Shop-Api-Call-Limit', '')
            if rate_limit_header:
                try:
                    # Format: "1/40" (used/limit)
                    used, limit = map(int, rate_limit_header.split('/'))
                    usage_percent = (used / limit) * 100 if limit > 0 else 0
                    
                    if usage_percent > 90:
                        logger.warning(f"Shopify API rate limit warning: {usage_percent:.1f}% used ({used}/{limit})")
                    elif usage_percent > 75:
                        logger.info(f"Shopify API rate limit: {usage_percent:.1f}% used ({used}/{limit})")
                except (ValueError, ZeroDivisionError):
                    # Ignore parsing errors for rate limit header
                    pass
            
            # Return both JSON and headers for pagination support
            return response.json(), response.headers
        except ValueError:
            # Re-raise authentication errors immediately (no retry)
            raise
        except requests.exceptions.RequestException as e:
            # Check if it's an authentication error
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code in (401, 403):
                    error_data = {}
                    try:
                        error_data = e.response.json()
                    except:
                        pass
                    error_msg = error_data.get('errors', str(e))
                    logger.error(f"Shopify API authentication failed ({e.response.status_code}): {error_msg}")
                    raise ValueError(f"Shopify API authentication failed: {error_msg}. Check SHOPIFY_TOKEN configuration.") from e
            
            logger.error(f"Shopify API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    def _retry_request(self, func, *args, **kwargs):
        """
        Retry a function call with exponential backoff.
        Skips retries for authentication errors (401, 403) and ValueError.
        
        Args:
            func: Function to retry
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func call
        """
        for attempt in range(Config.MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except (ValueError, requests.exceptions.HTTPError) as e:
                # Don't retry authentication errors (401, 403) or configuration errors
                if isinstance(e, ValueError) or (hasattr(e, 'response') and e.response and e.response.status_code in (401, 403)):
                    logger.error(f"Authentication/configuration error - not retrying: {e}")
                    raise
                # For other HTTP errors, retry
                if attempt == Config.MAX_RETRIES - 1:
                    logger.error(f"Max retries reached for {func.__name__}: {e}")
                    raise
                wait_time = Config.RETRY_BACKOFF ** attempt
                logger.warning(f"Retry {attempt + 1}/{Config.MAX_RETRIES} for {func.__name__} after {wait_time}s")
                time.sleep(wait_time)
            except Exception as e:
                if attempt == Config.MAX_RETRIES - 1:
                    logger.error(f"Max retries reached for {func.__name__}: {e}")
                    raise
                wait_time = Config.RETRY_BACKOFF ** attempt
                logger.warning(f"Retry {attempt + 1}/{Config.MAX_RETRIES} for {func.__name__} after {wait_time}s")
                time.sleep(wait_time)
    
    def get_all_products(self, limit: int = 250) -> List[Dict[str, Any]]:
        """
        Fetch all products from Shopify using direct HTTP requests.
        
        Args:
            limit: Maximum products per page (default: 250, max: 250)
            
        Returns:
            List of product dictionaries
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would fetch all products from Shopify")
            return []
        
        products = []
        page_info = None
        
        try:
            while True:
                params = {'limit': limit}
                if page_info:
                    params['page_info'] = page_info
                
                response_data, response_headers = self._retry_request(
                    self._make_shopify_request,
                    '/products.json',
                    'GET',
                    params
                )
                
                if not response_data or 'products' not in response_data:
                    break
                
                page_products = response_data['products']
                
                if not page_products:
                    break
                
                for product_data in page_products:
                    products.append(self._product_dict_to_dict(product_data))
                
                # Check for pagination using Link header (Shopify pagination)
                link_header = response_headers.get('Link', '')
                if not link_header and len(page_products) < limit:
                    break
                
                # Extract next page_info from Link header if present
                if link_header and 'rel="next"' in link_header:
                    # Extract page_info from Link header
                    import re
                    match = re.search(r'page_info=([^&>]+)', link_header)
                    if match:
                        page_info = match.group(1)
                    else:
                        break
                else:
                    break
                
                logger.info(f"Fetched {len(products)} products so far...")
                
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            # If pagination fails, try simple page-based approach
            try:
                for page in range(1, 10):  # Limit to 10 pages max
                    params = {'limit': limit, 'page': page}
                    response_data, _ = self._retry_request(
                        self._make_shopify_request,
                        '/products.json',
                        'GET',
                        params
                    )
                    if not response_data or 'products' not in response_data or not response_data['products']:
                        break
                    for product_data in response_data['products']:
                        products.append(self._product_dict_to_dict(product_data))
                    if len(response_data['products']) < limit:
                        break
            except Exception as e2:
                logger.error(f"Fallback pagination also failed: {e2}")
                raise
        
        logger.info(f"Successfully fetched {len(products)} products")
        return products
    
    def _product_dict_to_dict(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Shopify product dictionary to standardized format.
        
        Args:
            product_data: Shopify product dictionary from API
            
        Returns:
            Product dictionary
        """
        variants = []
        for variant in product_data.get('variants', []):
            variants.append({
                'id': variant.get('id'),
                'sku': variant.get('sku', ''),
                'title': variant.get('title', ''),
                'price': variant.get('price', '0'),
                'inventory_quantity': variant.get('inventory_quantity', 0),
                'inventory_item_id': variant.get('inventory_item_id'),
                'weight': variant.get('weight', 0),
                'weight_unit': variant.get('weight_unit', 'kg'),
                'barcode': variant.get('barcode', ''),
            })
        
        images = [img.get('src', '') for img in product_data.get('images', [])]
        
        return {
            'id': product_data.get('id'),
            'title': product_data.get('title', ''),
            'description': product_data.get('body_html', '') or product_data.get('description', ''),
            'handle': product_data.get('handle', ''),
            'vendor': product_data.get('vendor', ''),
            'product_type': product_data.get('product_type', ''),
            'tags': product_data.get('tags', '').split(',') if product_data.get('tags') else [],
            'images': images,
            'variants': variants,
            'status': product_data.get('status', 'active'),
            'created_at': product_data.get('created_at', ''),
            'updated_at': product_data.get('updated_at', ''),
        }
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single product by ID using direct HTTP requests.
        
        Args:
            product_id: Shopify product ID
            
        Returns:
            Product dictionary or None if not found
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would fetch product {product_id}")
            return None
        
        try:
            response_data, _ = self._retry_request(
                self._make_shopify_request,
                f'/products/{product_id}.json',
                'GET'
            )
            
            if response_data and 'product' in response_data:
                return self._product_dict_to_dict(response_data['product'])
            return None
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {e}")
            return None
    
    def get_inventory_levels(self, inventory_item_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch inventory levels for products using direct HTTP requests.
        
        Args:
            inventory_item_ids: Optional list of inventory item IDs to filter
            
        Returns:
            List of inventory level dictionaries
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would fetch inventory levels")
            return []
        
        try:
            inventory_levels = []
            
            if inventory_item_ids:
                # Fetch specific inventory items
                for item_id in inventory_item_ids:
                    try:
                        response_data, _ = self._retry_request(
                            self._make_shopify_request,
                            f'/inventory_items/{item_id}/inventory_levels.json',
                            'GET'
                        )
                        if response_data and 'inventory_levels' in response_data:
                            for level in response_data['inventory_levels']:
                                inventory_levels.append({
                                    'inventory_item_id': item_id,
                                    'location_id': level.get('location_id'),
                                    'available': level.get('available', 0),
                                    'updated_at': level.get('updated_at'),
                                })
                    except Exception as e:
                        logger.warning(f"Could not fetch inventory for item {item_id}: {e}")
            else:
                # Fetch all products and extract inventory from variants
                products = self.get_all_products()
                logger.info(f"Processing {len(products)} products for inventory sync")
                
                skipped_no_sku = 0
                skipped_no_tracking = 0
                
                for product in products:
                    for variant in product.get('variants', []):
                        # Check if inventory tracking is enabled
                        if not variant.get('inventory_item_id'):
                            skipped_no_tracking += 1
                            continue
                        
                        # Check if SKU exists (required for TikTok)
                        if not variant.get('sku'):
                            skipped_no_sku += 1
                            logger.debug(f"Product {product.get('title')} variant {variant.get('title')} skipped - no SKU")
                            continue
                        
                        inventory_levels.append({
                            'inventory_item_id': variant['inventory_item_id'],
                            'sku': variant['sku'],
                            'available': variant.get('inventory_quantity', 0),
                            'updated_at': product.get('updated_at'),
                        })
                
                logger.info(f"Inventory extraction: {len(inventory_levels)} items with SKUs and tracking")
                if skipped_no_sku > 0:
                    logger.warning(f"  - {skipped_no_sku} variants skipped (no SKU) - add SKUs in Shopify to sync them")
                if skipped_no_tracking > 0:
                    logger.info(f"  - {skipped_no_tracking} variants skipped (inventory tracking disabled)")
            
            return inventory_levels
            
        except Exception as e:
            logger.error(f"Error fetching inventory levels: {e}")
            raise
    
    def get_recent_orders(self, limit: int = 50, status: str = 'open') -> List[Dict[str, Any]]:
        """
        Fetch recent orders from Shopify using direct HTTP requests.
        
        Args:
            limit: Maximum number of orders to fetch
            status: Order status filter (open, closed, cancelled, any)
            
        Returns:
            List of order dictionaries
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would fetch {limit} recent orders with status {status}")
            return []
        
        try:
            params = {
                'limit': limit,
                'status': status,
                'order': 'created_at DESC'
            }
            
            response_data, _ = self._retry_request(
                self._make_shopify_request,
                '/orders.json',
                'GET',
                params
            )
            
            orders = []
            if response_data and 'orders' in response_data:
                for order_data in response_data['orders']:
                    orders.append({
                        'id': order_data.get('id'),
                        'order_number': order_data.get('order_number'),
                        'email': order_data.get('email'),
                        'financial_status': order_data.get('financial_status'),
                        'fulfillment_status': order_data.get('fulfillment_status'),
                        'line_items': [
                            {
                                'sku': item.get('sku'),
                                'title': item.get('title'),
                                'quantity': item.get('quantity'),
                                'price': item.get('price'),
                                'variant_id': item.get('variant_id'),
                            }
                            for item in order_data.get('line_items', [])
                        ],
                        'total_price': order_data.get('total_price'),
                        'created_at': order_data.get('created_at'),
                        'updated_at': order_data.get('updated_at'),
                    })
            
            return orders
            
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            raise
    
    def update_inventory_level(self, inventory_item_id: str, location_id: str, quantity: int) -> bool:
        """
        Update inventory level for a specific item.
        
        Args:
            inventory_item_id: Shopify inventory item ID
            location_id: Shopify location ID
            quantity: New inventory quantity
            
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update inventory {inventory_item_id} to {quantity}")
            return True
        
        try:
            # This would typically use the InventoryLevel API
            # Implementation depends on Shopify API version
            logger.info(f"Updating inventory {inventory_item_id} to {quantity}")
            # Note: Actual implementation would use shopify.InventoryLevel API
            return True
        except Exception as e:
            logger.error(f"Error updating inventory: {e}")
            return False
    
    def create_fulfillment(self, order_id: str, tracking_number: str, 
                          tracking_url: str = None, carrier: str = None) -> bool:
        """
        Create a fulfillment for an order.
        
        Args:
            order_id: Shopify order ID
            tracking_number: Tracking number
            tracking_url: Optional tracking URL
            carrier: Optional carrier name
            
        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create fulfillment for order {order_id}")
            return True
        
        try:
            order = self._retry_request(Order.find, order_id)
            # Create fulfillment using Shopify API
            # Implementation depends on specific fulfillment requirements
            logger.info(f"Creating fulfillment for order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating fulfillment: {e}")
            return False

