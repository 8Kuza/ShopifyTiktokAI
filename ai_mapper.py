"""
AI mapping module for enhancing Shopify products with TikTok-optimized data.
Uses OpenAI GPT-4o-mini for smart category mapping, hashtag generation, and optimization.
Includes caching for performance.
"""

import logging
import json
import hashlib
from typing import Dict, Any, Optional
from functools import lru_cache
from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)


class AIMapper:
    """AI mapper for converting Shopify products to TikTok-optimized format."""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize AI mapper.
        
        Args:
            dry_run: If True, simulate operations without making API calls
        """
        self.dry_run = dry_run
        self.client = None
        if not dry_run:
            try:
                from config import init_openai_client
                self.client = init_openai_client()
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise
    
    def _generate_cache_key(self, product_data: Dict[str, Any]) -> str:
        """
        Generate cache key for product data.
        
        Args:
            product_data: Product data dictionary
            
        Returns:
            Cache key string
        """
        # Create a stable representation for hashing
        key_data = {
            'id': product_data.get('id'),
            'title': product_data.get('title'),
            'description': product_data.get('description', '')[:100],  # First 100 chars
            'product_type': product_data.get('product_type'),
            'tags': sorted(product_data.get('tags', [])),
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _call_openai(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Call OpenAI API with retry logic.
        
        Args:
            prompt: Prompt string
            max_retries: Maximum number of retries
            
        Returns:
            Parsed JSON response
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would call OpenAI with prompt: {prompt[:100]}...")
            return {
                'category': 'Fashion',
                'hashtags': ['#fashion', '#trending', '#y2k'],
                'keywords': ['trendy', 'fashionable', 'stylish'],
                'optimized_title': 'Sample Product Title',
                'optimized_description': 'Sample product description optimized for TikTok Shop',
            }
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=Config.OPENAI_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert at optimizing e-commerce products for TikTok Shop.
                            Analyze the Shopify product data and provide:
                            1. Optimized TikTok title (max 100 chars, catchy and TikTok-friendly)
                            2. Optimized TikTok description (max 500 chars, engaging with trending hashtags)
                            3. Trending hashtags (5 trending hashtags like #TikTokMadeMeBuyIt, #Y2K, #Aesthetic, etc.)
                            
                            Return your response as valid JSON with these keys:
                            - tiktok_title: string (optimized title)
                            - tiktok_description: string (optimized description with hashtags)
                            - hashtags: array of 5 trending hashtag strings
                            
                            Focus on trending TikTok aesthetics, viral product descriptions, and include hashtags like #TikTokMadeMeBuyIt where relevant."""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=1000,
                )
                
                content = response.choices[0].message.content.strip()
                
                # Try to parse JSON (handle markdown code blocks)
                if content.startswith('```'):
                    # Remove markdown code blocks
                    lines = content.split('\n')
                    content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                
                result = json.loads(content)
                return result
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse OpenAI response (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error("Max retries reached for OpenAI API call")
                    raise
                continue
                
            except Exception as e:
                logger.warning(f"OpenAI API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error("Max retries reached for OpenAI API call")
                    raise
                continue
    
    def map_product(self, shopify_product: Dict[str, Any], use_cache: bool = True) -> Dict[str, Any]:
        """
        Map Shopify product to TikTok-optimized format using AI.
        
        Args:
            shopify_product: Shopify product dictionary
            use_cache: Whether to use caching (default: True)
            
        Returns:
            TikTok-optimized product dictionary
        """
        cache_key = self._generate_cache_key(shopify_product) if use_cache else None
        
        # Check cache (using simple in-memory cache for demo)
        # In production, consider using Redis or similar
        if use_cache and hasattr(self, '_cache'):
            if cache_key in self._cache:
                logger.debug(f"Using cached mapping for product {shopify_product.get('id')}")
                return self._cache[cache_key]
        
        # Prepare prompt
        product_summary = {
            'title': shopify_product.get('title', ''),
            'description': shopify_product.get('description', '')[:500],  # Limit description length
            'product_type': shopify_product.get('product_type', ''),
            'vendor': shopify_product.get('vendor', ''),
            'tags': shopify_product.get('tags', []),
            'variants': [
                {
                    'title': v.get('title', ''),
                    'price': v.get('price', ''),
                }
                for v in shopify_product.get('variants', [])[:3]  # Limit variants
            ],
        }
        
        prompt = f"""Optimize this Shopify product for TikTok Shop:

{json.dumps(product_summary, indent=2)}

Provide TikTok-optimized title, description with hashtags, and trending hashtags.
Include hashtags like #TikTokMadeMeBuyIt where relevant. Consider current TikTok trends."""
        
        try:
            # Call OpenAI
            ai_result = self._call_openai(prompt)
            
            # Build TikTok product payload (simplified for MVP)
            tiktok_product = {
                'title': ai_result.get('tiktok_title', shopify_product.get('title', '')),
                'description': ai_result.get('tiktok_description', shopify_product.get('description', '')),
                'hashtags': ai_result.get('hashtags', []),
                'images': shopify_product.get('images', []),
                'variants': [],
            }
            
            # Map variants
            for variant in shopify_product.get('variants', []):
                tiktok_variant = {
                    'sku': variant.get('sku', ''),
                    'title': variant.get('title', ''),
                    'price': variant.get('price', ''),
                    'inventory_quantity': variant.get('inventory_quantity', 0),
                    'barcode': variant.get('barcode', ''),
                }
                tiktok_product['variants'].append(tiktok_variant)
            
            # Add original Shopify metadata for reference
            tiktok_product['_shopify_id'] = shopify_product.get('id')
            tiktok_product['_shopify_handle'] = shopify_product.get('handle')
            
            # Cache result
            if use_cache:
                if not hasattr(self, '_cache'):
                    self._cache = {}
                self._cache[cache_key] = tiktok_product
            
            logger.info(f"Successfully mapped product {shopify_product.get('id')} to TikTok format")
            return tiktok_product
            
        except Exception as e:
            logger.error(f"Error mapping product {shopify_product.get('id')}: {e}")
            # Return fallback mapping
            return self._fallback_mapping(shopify_product)
    
    def _fallback_mapping(self, shopify_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback mapping when AI fails.
        
        Args:
            shopify_product: Shopify product dictionary
            
        Returns:
            Basic TikTok product dictionary
        """
        logger.warning(f"Using fallback mapping for product {shopify_product.get('id')}")
        
        # Add trending hashtags to description
        tags = shopify_product.get('tags', [])[:5]
        hashtags = [f"#{tag.strip().replace(' ', '')}" if not tag.startswith('#') else tag for tag in tags]
        if not hashtags:
            hashtags = ['#TikTokMadeMeBuyIt', '#Trending', '#ShopNow']
        
        description = shopify_product.get('description', '')
        if hashtags:
            description += f"\n\n{' '.join(hashtags)}"
        
        return {
            'title': shopify_product.get('title', ''),
            'description': description,
            'hashtags': hashtags,
            'images': shopify_product.get('images', []),
            'variants': [
                {
                    'sku': v.get('sku', ''),
                    'title': v.get('title', ''),
                    'price': v.get('price', ''),
                    'inventory_quantity': v.get('inventory_quantity', 0),
                    'barcode': v.get('barcode', ''),
                }
                for v in shopify_product.get('variants', [])
            ],
            '_shopify_id': shopify_product.get('id'),
            '_shopify_handle': shopify_product.get('handle'),
        }
    
    def batch_map_products(self, products: list[Dict[str, Any]], 
                          use_cache: bool = True) -> list[Dict[str, Any]]:
        """
        Batch map multiple products.
        
        Args:
            products: List of Shopify product dictionaries
            use_cache: Whether to use caching
            
        Returns:
            List of TikTok-optimized product dictionaries
        """
        results = []
        total = len(products)
        
        for i, product in enumerate(products, 1):
            logger.info(f"Mapping product {i}/{total}: {product.get('title', 'Unknown')}")
            try:
                mapped = self.map_product(product, use_cache=use_cache)
                results.append(mapped)
            except Exception as e:
                logger.error(f"Failed to map product {product.get('id')}: {e}")
                # Add fallback
                results.append(self._fallback_mapping(product))
        
        return results
    
    def clear_cache(self):
        """Clear the mapping cache."""
        if hasattr(self, '_cache'):
            self._cache.clear()
            logger.info("Mapping cache cleared")

