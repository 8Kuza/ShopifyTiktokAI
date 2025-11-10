"""
Unit tests for Shopify handler module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from shopify_handler import ShopifyHandler


@pytest.fixture
def shopify_handler_dry_run():
    """Shopify handler in dry run mode."""
    return ShopifyHandler(dry_run=True)


def test_shopify_handler_init_dry_run(shopify_handler_dry_run):
    """Test Shopify handler initialization in dry run mode."""
    assert shopify_handler_dry_run.dry_run is True
    assert shopify_handler_dry_run.session is None


def test_shopify_handler_get_all_products_dry_run(shopify_handler_dry_run):
    """Test getting all products in dry run mode."""
    products = shopify_handler_dry_run.get_all_products()
    assert products == []


def test_shopify_handler_get_product_by_id_dry_run(shopify_handler_dry_run):
    """Test getting product by ID in dry run mode."""
    product = shopify_handler_dry_run.get_product_by_id('12345')
    assert product is None


def test_shopify_handler_get_inventory_levels_dry_run(shopify_handler_dry_run):
    """Test getting inventory levels in dry run mode."""
    levels = shopify_handler_dry_run.get_inventory_levels()
    assert levels == []


def test_shopify_handler_get_recent_orders_dry_run(shopify_handler_dry_run):
    """Test getting recent orders in dry run mode."""
    orders = shopify_handler_dry_run.get_recent_orders()
    assert orders == []


def test_shopify_handler_update_inventory_level_dry_run(shopify_handler_dry_run):
    """Test updating inventory level in dry run mode."""
    result = shopify_handler_dry_run.update_inventory_level('item123', 'loc456', 100)
    assert result is True


def test_shopify_handler_create_fulfillment_dry_run(shopify_handler_dry_run):
    """Test creating fulfillment in dry run mode."""
    result = shopify_handler_dry_run.create_fulfillment('order123', 'TRACK123')
    assert result is True


def test_shopify_handler_product_to_dict():
    """Test product to dictionary conversion."""
    handler = ShopifyHandler(dry_run=True)
    
    # Mock Shopify product object
    mock_product = MagicMock()
    mock_product.id = '12345'
    mock_product.title = 'Test Product'
    mock_product.body_html = 'Test description'
    mock_product.handle = 'test-product'
    mock_product.vendor = 'Test Vendor'
    mock_product.product_type = 'Fashion'
    mock_product.tags = 'tag1,tag2'
    mock_product.status = 'active'
    mock_product.created_at = '2024-01-01T00:00:00Z'
    mock_product.updated_at = '2024-01-01T00:00:00Z'
    
    # Mock variant
    mock_variant = MagicMock()
    mock_variant.id = '67890'
    mock_variant.sku = 'TEST-SKU'
    mock_variant.title = 'Test Variant'
    mock_variant.price = '29.99'
    mock_variant.inventory_quantity = 100
    mock_variant.inventory_item_id = 'item123'
    mock_variant.weight = 1.0
    mock_variant.weight_unit = 'kg'
    mock_variant.barcode = '1234567890'
    
    # Mock image
    mock_image = MagicMock()
    mock_image.src = 'https://example.com/image.jpg'
    
    mock_product.variants = [mock_variant]
    mock_product.images = [mock_image]
    
    result = handler._product_to_dict(mock_product)
    
    assert result['id'] == '12345'
    assert result['title'] == 'Test Product'
    assert result['description'] == 'Test description'
    assert result['handle'] == 'test-product'
    assert len(result['variants']) == 1
    assert result['variants'][0]['sku'] == 'TEST-SKU'
    assert len(result['images']) == 1
    assert result['images'][0] == 'https://example.com/image.jpg'

