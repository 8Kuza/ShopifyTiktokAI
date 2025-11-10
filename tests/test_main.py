"""
Unit tests for main sync bot module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from main import SyncBot


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

