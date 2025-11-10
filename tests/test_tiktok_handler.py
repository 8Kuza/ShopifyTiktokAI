"""
Unit tests for TikTok handler module.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from tiktok_handler import TikTokHandler


@pytest.fixture
def tiktok_handler_dry_run():
    """TikTok handler in dry run mode."""
    return TikTokHandler(dry_run=True)


def test_tiktok_handler_init_dry_run(tiktok_handler_dry_run):
    """Test TikTok handler initialization in dry run mode."""
    assert tiktok_handler_dry_run.dry_run is True


def test_tiktok_handler_update_inventory_dry_run(tiktok_handler_dry_run):
    """Test updating inventory in dry run mode."""
    result = tiktok_handler_dry_run.update_inventory('TEST-SKU', 100)
    assert result is True


def test_tiktok_handler_bulk_update_inventory_dry_run(tiktok_handler_dry_run):
    """Test bulk updating inventory in dry run mode."""
    updates = [
        {'sku': 'SKU1', 'quantity': 100},
        {'sku': 'SKU2', 'quantity': 50},
    ]
    result = tiktok_handler_dry_run.bulk_update_inventory(updates)
    assert result is True


def test_tiktok_handler_create_product_dry_run(tiktok_handler_dry_run):
    """Test creating product in dry run mode."""
    product_data = {
        'title': 'Test Product',
        'description': 'Test description',
        'category': 'Fashion',
    }
    product_id = tiktok_handler_dry_run.create_product(product_data)
    assert product_id is not None


def test_tiktok_handler_bulk_create_products_dry_run(tiktok_handler_dry_run):
    """Test bulk creating products in dry run mode."""
    products = [
        {
            'title': 'Product 1',
            'description': 'Description 1',
            'category': 'Fashion',
        },
        {
            'title': 'Product 2',
            'description': 'Description 2',
            'category': 'Beauty',
        },
    ]
    results = tiktok_handler_dry_run.bulk_create_products(products)
    assert 'success' in results
    assert 'failed' in results


def test_tiktok_handler_get_orders_dry_run(tiktok_handler_dry_run):
    """Test getting orders in dry run mode."""
    orders = tiktok_handler_dry_run.get_orders()
    assert orders == []


def test_tiktok_handler_update_order_tracking_dry_run(tiktok_handler_dry_run):
    """Test updating order tracking in dry run mode."""
    result = tiktok_handler_dry_run.update_order_tracking('order123', 'TRACK123')
    assert result is True


def test_tiktok_handler_generate_signature(tiktok_handler_dry_run):
    """Test signature generation."""
    method = 'POST'
    path = '/test/endpoint'
    params = {'param1': 'value1', 'param2': 'value2'}
    timestamp = int(time.time() * 1000)
    body = '{"test": "data"}'
    
    signature = tiktok_handler_dry_run._generate_signature(method, path, params, timestamp, body)
    
    assert signature is not None
    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256 hex digest length


@patch('tiktok_handler.requests.post')
def test_tiktok_handler_make_request_post(mock_post, tiktok_handler_dry_run):
    """Test making POST request."""
    mock_response = MagicMock()
    mock_response.json.return_value = {'code': 0, 'message': 'success', 'data': {}}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    # Temporarily disable dry run
    tiktok_handler_dry_run.dry_run = False
    
    try:
        result = tiktok_handler_dry_run._make_request('POST', '/test', data={'test': 'data'})
        assert result['code'] == 0
    finally:
        tiktok_handler_dry_run.dry_run = True

