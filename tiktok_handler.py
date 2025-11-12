"""
TikTok Shop API handler for pushing inventory, products, and order updates.
Handles bulk operations and error retries.
"""

import logging
import time
import requests
import hmac
import hashlib
import json
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode
from config import Config

logger = logging.getLogger(__name__)


class TikTokHandler:
    """Handler for TikTok Shop API operations."""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize TikTok handler.
        
        Args:
            dry_run: If True, simulate operations without making API calls
        """
        self.dry_run = dry_run
        self.app_key = Config.TIKTOK_APP_KEY
        self.app_secret = Config.TIKTOK_SECRET
        self.base_url = Config.TIKTOK_API_BASE
        self.mock_mode = Config.MOCK_MODE or not self.app_key or not self.app_key.startswith('app_')
        
        if self.mock_mode:
            logger.info("TikTok handler initialized in MOCK MODE - API calls will be logged only")
    
    def _generate_signature(self, method: str, path: str, params: Dict[str, Any], 
                           timestamp: int, body: str = '') -> str:
        """
        Generate TikTok Shop API signature.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            params: Query parameters
            timestamp: Request timestamp
            body: Request body (for POST requests)
            
        Returns:
            Signature string
        """
        # Sort parameters
        sorted_params = sorted(params.items())
        query_string = urlencode(sorted_params)
        
        # Build string to sign
        string_to_sign = f"{method}\n{path}\n{query_string}\n{timestamp}\n{body}"
        
        # Generate signature
        signature = hmac.new(
            self.app_secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None,
                     params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make authenticated request to TikTok Shop API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            API response as dictionary
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would {method} {endpoint} with data: {data}")
            return {'code': 0, 'message': 'success', 'data': {}}
        
        url = f"{self.base_url}{endpoint}"
        timestamp = int(time.time() * 1000)
        
        # Prepare parameters
        if params is None:
            params = {}
        params.update({
            'app_key': self.app_key,
            'timestamp': str(timestamp),
        })
        
        # Prepare body
        body = ''
        if data:
            body = json.dumps(data)
        
        # Generate signature
        signature = self._generate_signature(method, endpoint, params, timestamp, body)
        params['sign'] = signature
        
        # Add access token if available
        headers = {
            'Content-Type': 'application/json',
        }
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        # Make request
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, params=params, json=data, headers=headers, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, params=params, json=data, headers=headers, timeout=30)
            else:
                response = requests.request(method, url, params=params, json=data, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TikTok API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
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
    
    def update_inventory(self, sku: str, quantity: int, warehouse_id: str = None) -> bool:
        """
        Update inventory for a single SKU.
        
        Args:
            sku: Product SKU
            quantity: New inventory quantity
            warehouse_id: Optional warehouse ID
            
        Returns:
            True if successful, False otherwise
        """
        if self.mock_mode or self.dry_run:
            logger.info(f"[MOCK] TikTok Shop: SKU {sku} → Stock {quantity}")
            return True
        
        try:
            payload = {
                'sku_id': sku,
                'quantity': quantity,
            }
            if warehouse_id:
                payload['warehouse_id'] = warehouse_id
            
            response = self._retry_request(
                self._make_request,
                'POST',
                '/inventory/update',
                data=payload
            )
            
            if response.get('code') == 0:
                logger.info(f"Successfully updated inventory for SKU {sku} to {quantity}")
                return True
            else:
                logger.error(f"Failed to update inventory: {response.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating inventory for SKU {sku}: {e}")
            return False
    
    def bulk_update_inventory(self, inventory_updates: List[Dict[str, Any]]) -> bool:
        """
        Bulk update inventory for multiple SKUs.
        
        Args:
            inventory_updates: List of dicts with 'sku' and 'quantity' keys
            
        Returns:
            True if successful, False otherwise
        """
        if self.mock_mode or self.dry_run:
            logger.info(f"[MOCK] TikTok Shop: Bulk update {len(inventory_updates)} inventory items")
            for item in inventory_updates[:5]:  # Log first 5
                logger.info(f"[MOCK]   SKU {item.get('sku')} → Stock {item.get('quantity')}")
            if len(inventory_updates) > 5:
                logger.info(f"[MOCK]   ... and {len(inventory_updates) - 5} more items")
            return True
        
        try:
            # Split into batches
            batch_size = Config.BATCH_SIZE
            total_batches = (len(inventory_updates) + batch_size - 1) // batch_size
            
            for i in range(0, len(inventory_updates), batch_size):
                batch = inventory_updates[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                logger.info(f"Processing inventory batch {batch_num}/{total_batches} ({len(batch)} items)")
                
                payload = {
                    'inventory_list': [
                        {
                            'sku_id': item['sku'],
                            'quantity': item['quantity'],
                        }
                        for item in batch
                    ]
                }
                
                response = self._retry_request(
                    self._make_request,
                    'POST',
                    '/inventory/bulk_update',
                    data=payload
                )
                
                if response.get('code') != 0:
                    logger.error(f"Failed to update inventory batch {batch_num}: {response.get('message')}")
                    return False
                
                logger.info(f"Successfully updated inventory batch {batch_num}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error bulk updating inventory: {e}")
            return False
    
    def create_product(self, product_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a single product on TikTok Shop.
        
        Args:
            product_data: Product data dictionary
            
        Returns:
            TikTok product ID if successful, None otherwise
        """
        try:
            response = self._retry_request(
                self._make_request,
                'POST',
                '/products/create',
                data=product_data
            )
            
            if response.get('code') == 0:
                product_id = response.get('data', {}).get('product_id')
                logger.info(f"Successfully created product: {product_id}")
                return product_id
            else:
                logger.error(f"Failed to create product: {response.get('message')}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            return None
    
    def bulk_create_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk create products on TikTok Shop.
        
        Args:
            products: List of product data dictionaries
            
        Returns:
            Dictionary with success/failure counts
        """
        results = {
            'success': 0,
            'failed': 0,
            'product_ids': []
        }
        
        if self.mock_mode or self.dry_run:
            logger.info(f"[MOCK] TikTok Shop: Would create {len(products)} products")
            for i, product in enumerate(products[:3], 1):  # Log first 3
                logger.info(f"[MOCK]   Product {i}: {product.get('title', 'Unknown')}")
            if len(products) > 3:
                logger.info(f"[MOCK]   ... and {len(products) - 3} more products")
            results['success'] = len(products)
            results['product_ids'] = [f'mock_id_{i}' for i in range(len(products))]
            return results
        
        try:
            # Split into batches
            batch_size = Config.BATCH_SIZE
            total_batches = (len(products) + batch_size - 1) // batch_size
            
            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                logger.info(f"Processing product batch {batch_num}/{total_batches} ({len(batch)} products)")
                
                payload = {
                    'products': batch
                }
                
                response = self._retry_request(
                    self._make_request,
                    'POST',
                    '/products/bulk_create',
                    data=payload
                )
                
                if response.get('code') == 0:
                    batch_results = response.get('data', {}).get('results', [])
                    for result in batch_results:
                        if result.get('success'):
                            results['success'] += 1
                            results['product_ids'].append(result.get('product_id'))
                        else:
                            results['failed'] += 1
                            logger.warning(f"Failed to create product: {result.get('message')}")
                else:
                    logger.error(f"Failed to create product batch {batch_num}: {response.get('message')}")
                    results['failed'] += len(batch)
            
            logger.info(f"Bulk create completed: {results['success']} success, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Error bulk creating products: {e}")
            results['failed'] += len(products)
            return results
    
    def update_product(self, product_id: str, product_data: Dict[str, Any]) -> bool:
        """
        Update an existing product on TikTok Shop.
        
        Args:
            product_id: TikTok product ID
            product_data: Updated product data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                'product_id': product_id,
                **product_data
            }
            
            response = self._retry_request(
                self._make_request,
                'PUT',
                '/products/update',
                data=payload
            )
            
            if response.get('code') == 0:
                logger.info(f"Successfully updated product: {product_id}")
                return True
            else:
                logger.error(f"Failed to update product: {response.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            return False
    
    def get_orders(self, start_time: int = None, end_time: int = None, 
                   limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch orders from TikTok Shop.
        
        Args:
            start_time: Start timestamp (milliseconds)
            end_time: End timestamp (milliseconds)
            limit: Maximum number of orders to fetch
            
        Returns:
            List of order dictionaries
        """
        try:
            params = {
                'limit': limit,
            }
            if start_time:
                params['start_time'] = start_time
            if end_time:
                params['end_time'] = end_time
            
            response = self._retry_request(
                self._make_request,
                'GET',
                '/orders/list',
                params=params
            )
            
            if response.get('code') == 0:
                orders = response.get('data', {}).get('orders', [])
                logger.info(f"Fetched {len(orders)} orders from TikTok Shop")
                return orders
            else:
                logger.error(f"Failed to fetch orders: {response.get('message')}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []
    
    def update_order_tracking(self, order_id: str, tracking_number: str,
                             tracking_url: str = None, carrier: str = None) -> bool:
        """
        Update tracking information for an order.
        
        Args:
            order_id: TikTok order ID
            tracking_number: Tracking number
            tracking_url: Optional tracking URL
            carrier: Optional carrier name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                'order_id': order_id,
                'tracking_number': tracking_number,
            }
            if tracking_url:
                payload['tracking_url'] = tracking_url
            if carrier:
                payload['carrier'] = carrier
            
            response = self._retry_request(
                self._make_request,
                'POST',
                '/orders/update_tracking',
                data=payload
            )
            
            if response.get('code') == 0:
                logger.info(f"Successfully updated tracking for order {order_id}")
                return True
            else:
                logger.error(f"Failed to update tracking: {response.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating tracking for order {order_id}: {e}")
            return False

