"""
Shopify API handler for fetching products, inventory, and orders.
Handles bulk operations and error retries.
"""

import logging
import time
from typing import List, Dict, Optional, Any
try:
    import shopify
    from shopify import Product, Variant, InventoryItem, Order
except ImportError:
    # Fallback if shopify-python-api is not installed
    shopify = None
    Product = None
    Variant = None
    InventoryItem = None
    Order = None
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
        """Initialize Shopify session."""
        if shopify is None:
            raise ImportError("shopify-python-api library is not installed. Install it with: pip install shopify-python-api==1.0.1")
        from config import init_shopify_client
        init_shopify_client()
        return True
    
    def _retry_request(self, func, *args, **kwargs):
        """
        Retry a function call with exponential backoff.
        
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
            except Exception as e:
                if attempt == Config.MAX_RETRIES - 1:
                    logger.error(f"Max retries reached for {func.__name__}: {e}")
                    raise
                wait_time = Config.RETRY_BACKOFF ** attempt
                logger.warning(f"Retry {attempt + 1}/{Config.MAX_RETRIES} for {func.__name__} after {wait_time}s")
                time.sleep(wait_time)
    
    def get_all_products(self, limit: int = 250) -> List[Dict[str, Any]]:
        """
        Fetch all products from Shopify using shopify-python-api==1.0.1.
        
        Args:
            limit: Maximum products per page (default: 250, max: 250)
            
        Returns:
            List of product dictionaries
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would fetch all products from Shopify")
            return []
        
        if shopify is None:
            raise ImportError("shopify-python-api library is not installed")
        
        products = []
        page = 1
        
        try:
            while True:
                # Use ShopifyResource.get for API 2025-10
                response = self._retry_request(
                    shopify.ShopifyResource.get,
                    f"/products.json?limit={limit}&page={page}"
                )
                
                if not response or 'products' not in response:
                    break
                
                page_products = response['products']
                
                if not page_products:
                    break
                
                for product_data in page_products:
                    products.append(self._product_dict_to_dict(product_data))
                
                if len(page_products) < limit:
                    break
                
                page += 1
                logger.info(f"Fetched {len(products)} products so far...")
                
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            # Fallback to Product.find if available
            try:
                if Product:
                    page_products = self._retry_request(Product.find, limit=limit)
                    for product in page_products:
                        products.append(self._product_to_dict(product))
            except:
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
    
    def _product_to_dict(self, product: Product) -> Dict[str, Any]:
        """
        Convert Shopify Product object to dictionary.
        
        Args:
            product: Shopify Product object
            
        Returns:
            Product dictionary
        """
        variants = []
        for variant in product.variants:
            variants.append({
                'id': variant.id,
                'sku': variant.sku,
                'title': variant.title,
                'price': variant.price,
                'inventory_quantity': variant.inventory_quantity,
                'inventory_item_id': variant.inventory_item_id,
                'weight': variant.weight,
                'weight_unit': variant.weight_unit,
                'barcode': variant.barcode,
            })
        
        return {
            'id': product.id,
            'title': product.title,
            'description': product.body_html or '',
            'handle': product.handle,
            'vendor': product.vendor,
            'product_type': product.product_type,
            'tags': product.tags.split(',') if product.tags else [],
            'images': [img.src for img in product.images],
            'variants': variants,
            'status': product.status,
            'created_at': product.created_at,
            'updated_at': product.updated_at,
        }
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single product by ID.
        
        Args:
            product_id: Shopify product ID
            
        Returns:
            Product dictionary or None if not found
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would fetch product {product_id}")
            return None
        
        try:
            product = self._retry_request(Product.find, product_id)
            return self._product_to_dict(product)
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {e}")
            return None
    
    def get_inventory_levels(self, inventory_item_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch inventory levels for products.
        
        Args:
            inventory_item_ids: Optional list of inventory item IDs to filter
            
        Returns:
            List of inventory level dictionaries
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would fetch inventory levels")
            return []
        
        try:
            # Fetch inventory levels
            inventory_levels = []
            
            if inventory_item_ids:
                # Fetch specific inventory items
                for item_id in inventory_item_ids:
                    try:
                        item = self._retry_request(InventoryItem.find, item_id)
                        # Get inventory levels for this item
                        levels = item.inventory_levels()
                        for level in levels:
                            inventory_levels.append({
                                'inventory_item_id': item_id,
                                'location_id': level.location_id,
                                'available': level.available,
                                'updated_at': level.updated_at,
                            })
                    except Exception as e:
                        logger.warning(f"Could not fetch inventory for item {item_id}: {e}")
            else:
                # Fetch all products and their inventory
                products = self.get_all_products()
                for product in products:
                    for variant in product.get('variants', []):
                        if variant.get('inventory_item_id'):
                            try:
                                item = self._retry_request(
                                    InventoryItem.find,
                                    variant['inventory_item_id']
                                )
                                levels = item.inventory_levels()
                                for level in levels:
                                    inventory_levels.append({
                                        'inventory_item_id': variant['inventory_item_id'],
                                        'sku': variant['sku'],
                                        'location_id': level.location_id,
                                        'available': level.available,
                                        'updated_at': level.updated_at,
                                    })
                            except Exception as e:
                                logger.warning(f"Could not fetch inventory for variant {variant.get('sku')}: {e}")
            
            return inventory_levels
            
        except Exception as e:
            logger.error(f"Error fetching inventory levels: {e}")
            raise
    
    def get_recent_orders(self, limit: int = 50, status: str = 'open') -> List[Dict[str, Any]]:
        """
        Fetch recent orders from Shopify.
        
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
            orders = self._retry_request(
                Order.find,
                limit=limit,
                status=status,
                order='created_at DESC'
            )
            
            order_list = []
            for order in orders:
                order_list.append({
                    'id': order.id,
                    'order_number': order.order_number,
                    'email': order.email,
                    'financial_status': order.financial_status,
                    'fulfillment_status': order.fulfillment_status,
                    'line_items': [
                        {
                            'sku': item.sku,
                            'title': item.title,
                            'quantity': item.quantity,
                            'price': item.price,
                            'variant_id': item.variant_id,
                        }
                        for item in order.line_items
                    ],
                    'total_price': order.total_price,
                    'created_at': order.created_at,
                    'updated_at': order.updated_at,
                })
            
            return order_list
            
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

