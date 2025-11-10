"""
Unit tests for AI mapper module.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from ai_mapper import AIMapper


@pytest.fixture
def sample_shopify_product():
    """Sample Shopify product for testing."""
    return {
        'id': '12345',
        'title': 'Test Product',
        'description': 'A test product description',
        'product_type': 'Fashion',
        'vendor': 'Test Vendor',
        'tags': ['test', 'fashion', 'trendy'],
        'handle': 'test-product',
        'variants': [
            {
                'id': '67890',
                'sku': 'TEST-SKU-001',
                'title': 'Test Variant',
                'price': '29.99',
                'inventory_quantity': 100,
                'barcode': '1234567890',
            }
        ],
        'images': ['https://example.com/image.jpg'],
    }


@pytest.fixture
def ai_mapper_dry_run():
    """AI mapper in dry run mode."""
    return AIMapper(dry_run=True)


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        'category': 'Fashion',
        'hashtags': ['#fashion', '#trending', '#y2k', '#aesthetic'],
        'keywords': ['trendy', 'fashionable', 'stylish', 'viral'],
        'optimized_title': 'Test Product - Trending Fashion Item',
        'optimized_description': 'A trendy test product optimized for TikTok Shop with viral potential.',
    }


def test_ai_mapper_init_dry_run(ai_mapper_dry_run):
    """Test AI mapper initialization in dry run mode."""
    assert ai_mapper_dry_run.dry_run is True
    assert ai_mapper_dry_run.client is None


def test_ai_mapper_map_product_dry_run(ai_mapper_dry_run, sample_shopify_product):
    """Test product mapping in dry run mode."""
    result = ai_mapper_dry_run.map_product(sample_shopify_product)
    
    assert result is not None
    assert 'title' in result
    assert 'description' in result
    assert 'category' in result
    assert 'hashtags' in result
    assert 'keywords' in result
    assert 'variants' in result
    assert result['_shopify_id'] == sample_shopify_product['id']


def test_ai_mapper_fallback_mapping(ai_mapper_dry_run, sample_shopify_product):
    """Test fallback mapping when AI fails."""
    result = ai_mapper_dry_run._fallback_mapping(sample_shopify_product)
    
    assert result['title'] == sample_shopify_product['title']
    assert result['description'] == sample_shopify_product['description']
    assert result['category'] == sample_shopify_product['product_type']
    assert len(result['variants']) == len(sample_shopify_product['variants'])


def test_ai_mapper_cache_key_generation(ai_mapper_dry_run, sample_shopify_product):
    """Test cache key generation."""
    key1 = ai_mapper_dry_run._generate_cache_key(sample_shopify_product)
    key2 = ai_mapper_dry_run._generate_cache_key(sample_shopify_product)
    
    # Same product should generate same key
    assert key1 == key2
    
    # Different product should generate different key
    different_product = sample_shopify_product.copy()
    different_product['title'] = 'Different Product'
    key3 = ai_mapper_dry_run._generate_cache_key(different_product)
    assert key1 != key3


@patch('ai_mapper.OpenAI')
def test_ai_mapper_map_product_with_openai(mock_openai_class, sample_shopify_product, mock_openai_response):
    """Test product mapping with OpenAI API."""
    # Mock OpenAI client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(mock_openai_response)
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai_class.return_value = mock_client
    
    # Create mapper (not in dry run)
    with patch('ai_mapper.init_openai_client', return_value=mock_client):
        mapper = AIMapper(dry_run=False)
        mapper.client = mock_client
        
        result = mapper.map_product(sample_shopify_product)
        
        assert result is not None
        assert result['category'] == mock_openai_response['category']
        assert result['hashtags'] == mock_openai_response['hashtags']
        assert result['keywords'] == mock_openai_response['keywords']
        assert result['title'] == mock_openai_response['optimized_title']


def test_ai_mapper_batch_map_products(ai_mapper_dry_run, sample_shopify_product):
    """Test batch product mapping."""
    products = [sample_shopify_product] * 3
    
    results = ai_mapper_dry_run.batch_map_products(products)
    
    assert len(results) == len(products)
    for result in results:
        assert result is not None
        assert '_shopify_id' in result


def test_ai_mapper_clear_cache(ai_mapper_dry_run, sample_shopify_product):
    """Test cache clearing."""
    # Map a product to populate cache
    ai_mapper_dry_run.map_product(sample_shopify_product, use_cache=True)
    
    # Clear cache
    ai_mapper_dry_run.clear_cache()
    
    # Cache should be empty
    assert not hasattr(ai_mapper_dry_run, '_cache') or len(ai_mapper_dry_run._cache) == 0

