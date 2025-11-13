"""
Unit tests for main sync bot module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from main import SyncBot, app, _sync_bot_instance


@pytest.fixture
def sync_bot_dry_run():
    """Sync bot in dry run mode."""
    return SyncBot(dry_run=True)


def test_sync_bot_init_dry_run(sync_bot_dry_run):
    """Test sync bot initialization in dry run mode."""
    assert sync_bot_dry_run.dry_run is True
    assert sync_bot_dry_run.shopify is not None
    assert sync_bot_dry_run.tiktok is not None
    assert sync_bot_dry_run.ai_mapper is not None


def test_sync_bot_sync_inventory_dry_run(sync_bot_dry_run):
    """Test inventory sync in dry run mode."""
    results = sync_bot_dry_run.sync_inventory()
    assert 'success' in results
    assert 'failed' in results
    assert 'total' in results


def test_sync_bot_sync_products_dry_run(sync_bot_dry_run):
    """Test product sync in dry run mode."""
    results = sync_bot_dry_run.sync_products(limit=5)
    assert 'success' in results
    assert 'failed' in results
    assert 'total' in results


def test_sync_bot_sync_orders_dry_run(sync_bot_dry_run):
    """Test order sync in dry run mode."""
    results = sync_bot_dry_run.sync_orders()
    assert 'success' in results
    assert 'failed' in results
    assert 'total' in results


def test_sync_bot_run_full_sync_dry_run(sync_bot_dry_run):
    """Test full sync in dry run mode."""
    # Should not raise any exceptions
    sync_bot_dry_run.run_full_sync()


def test_sync_bot_update_order_tracking_dry_run(sync_bot_dry_run):
    """Test updating order tracking in dry run mode."""
    result = sync_bot_dry_run.update_order_tracking('order123', 'TRACK123')
    assert isinstance(result, bool)


def test_sync_bot_start_scheduler(sync_bot_dry_run):
    """Test starting scheduler."""
    sync_bot_dry_run.start_scheduler(interval=60)
    assert sync_bot_dry_run.scheduler is not None
    assert sync_bot_dry_run.scheduler.running is True
    sync_bot_dry_run.stop_scheduler()


def test_sync_bot_stop_scheduler(sync_bot_dry_run):
    """Test stopping scheduler."""
    sync_bot_dry_run.start_scheduler(interval=60)
    sync_bot_dry_run.stop_scheduler()
    # Scheduler should be stopped (shutdown)
    assert sync_bot_dry_run.scheduler is not None


def test_root_endpoint():
    """Test root endpoint returns 200 and proper JSON."""
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None
        assert 'service' in data
        assert 'status' in data
        assert 'endpoints' in data
        assert data['service'] == 'Shopify TikTok AI Sync Bot'


def test_health_endpoint_basic():
    """Test health endpoint returns 200 and proper JSON."""
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None
        assert 'status' in data
        assert 'message' in data
        assert 'flask' in data
        assert data['flask'] == 'running'


def test_health_endpoint_with_bot(sync_bot_dry_run):
    """Test health endpoint with bot instance."""
    # Set global bot instance
    import main
    main._sync_bot_instance = sync_bot_dry_run
    
    # Start scheduler
    sync_bot_dry_run.start_scheduler(interval=60)
    
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None
        assert 'status' in data
        assert 'scheduler' in data
        assert data['scheduler'] == 'running'
    
    # Cleanup
    sync_bot_dry_run.stop_scheduler()
    main._sync_bot_instance = None


def test_health_endpoint_openai_status(sync_bot_dry_run):
    """Test health endpoint checks OpenAI availability."""
    import main
    main._sync_bot_instance = sync_bot_dry_run
    
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None
        # OpenAI status should be present if bot instance exists
        if sync_bot_dry_run.ai_mapper:
            assert 'openai' in data
    
    main._sync_bot_instance = None

