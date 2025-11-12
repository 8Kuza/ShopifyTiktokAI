# TikTok Shop AI Sync Bot

A production-ready Python automation tool that syncs inventory and products from Shopify to TikTok Shop in real-time, with AI-enhanced mapping for categories, tags, and hashtags. Built for DTC brand agencies requiring low-latency, error-handling, and scalable operations.

## Features

- **Inventory Sync**: Polls Shopify for stock changes on variants/SKUs and pushes updates to TikTok Shop API to prevent oversells. Handles bulk operations for 100+ products.
- **Product Sync**: Pulls product data (title, description, images, variants) from Shopify, uses OpenAI to "smart map" to TikTok categories (auto-adds trending hashtags like "Y2K aesthetic" based on description), then bulk-uploads/edits on TikTok.
- **Order Sync**: Listens for new TikTok orders, routes to Shopify for fulfillment, and updates tracking back to TikTok.
- **AI Layer**: Uses OpenAI (gpt-4o-mini) for intelligent mapping: Input Shopify product JSON → Output optimized TikTok payload (categories, keywords, hashtags). Includes error retries and caching.
- **Scheduling**: Configurable polling intervals (default: 5 minutes) using APScheduler.
- **Error Handling**: Retry logic with exponential backoff, comprehensive logging, and optional notifications.
- **Testing**: Dry-run mode for testing without API calls, comprehensive unit tests.

## Tech Stack

- **Python 3.12+**
- **Shopify**: `shopify-python-api` library
- **TikTok Shop**: `requests` for API calls (base URL: `https://partner.tiktokshop.com/api`)
- **OpenAI**: `openai` library (gpt-4o-mini model)
- **Scheduling**: `APScheduler` for cron-like polling
- **Environment**: `.env` file for configuration
- **Logging**: Python `logging` module (console + file output)

## Installation

### Prerequisites

- Python 3.12 or higher
- Shopify store with API access
- TikTok Shop Partner account with API credentials
- OpenAI API key

### Setup

1. **Clone or download this repository**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create `.env` file** (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

4. **Configure your `.env` file** with your API keys:
   ```env
   # Shopify Configuration
   SHOPIFY_STORE=your-store.myshopify.com
   SHOPIFY_TOKEN=your_shopify_access_token
   # Note: SHOPIFY_ACCESS_TOKEN also works (backward compatibility)

   # TikTok Shop Configuration
   TIKTOK_APP_KEY=your_tiktok_app_key
   TIKTOK_SECRET=your_tiktok_secret
   TIKTOK_ACCESS_TOKEN=your_tiktok_access_token
   TIKTOK_API_BASE=https://partner.tiktokshop.com/api

   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=gpt-4o-mini

   # Sync Settings
   SYNC_INTERVAL=300
   BATCH_SIZE=100

   # Retry Settings
   MAX_RETRIES=3
   RETRY_BACKOFF=2.0
   ```

## Usage

### Command Line Interface

The bot can be run in several modes:

#### Single Run (One-time sync)

```bash
# Full sync (inventory + products + orders)
python main.py --mode=full

# Inventory sync only
python main.py --mode=inventory

# Product sync only
python main.py --mode=products

# Order sync only
python main.py --mode=orders
```

#### Continuous Mode (Scheduled polling)

```bash
# Run full sync every 5 minutes (300 seconds)
python main.py --mode=full --interval=300

# Run inventory sync every 1 minute (60 seconds)
python main.py --mode=inventory --interval=60
```

#### Dry Run Mode (Testing without API calls)

```bash
# Test the sync without making actual API calls
python main.py --mode=full --dry

# Test with limited products
python main.py --mode=products --dry --limit=10
```

#### Additional Options

```bash
# Set logging level
python main.py --mode=full --log-level=DEBUG

# Limit number of products to sync (for testing)
python main.py --mode=products --limit=50
```

### Command Line Arguments

- `--mode`: Sync mode - `full`, `inventory`, `products`, or `orders` (default: `full`)
- `--interval`: Sync interval in seconds for continuous mode (if not set, runs once)
- `--dry`: Dry run mode (simulate without API calls)
- `--limit`: Limit number of products to sync (for testing)
- `--log-level`: Logging level - `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

## Project Structure

```
ShopifyTiktokAI/
├── config.py              # Configuration and environment setup
├── shopify_handler.py      # Shopify API interactions
├── tiktok_handler.py       # TikTok Shop API interactions
├── ai_mapper.py            # OpenAI product mapping with caching
├── main.py                 # Main orchestration and CLI
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment variables
├── README.md              # This file
├── tests/                 # Unit tests
│   ├── __init__.py
│   ├── test_ai_mapper.py
│   ├── test_shopify_handler.py
│   ├── test_tiktok_handler.py
│   └── test_main.py
└── sync_bot.log           # Log file (created at runtime)
```

## API Endpoints Used

### Shopify API
- `GET /admin/api/2024-01/products.json` - Fetch products
- `GET /admin/api/2024-01/inventory_levels.json` - Fetch inventory levels
- `GET /admin/api/2024-01/orders.json` - Fetch orders
- `POST /admin/api/2024-01/fulfillments.json` - Create fulfillments

### TikTok Shop API
- `POST /inventory/update` - Update single inventory item
- `POST /inventory/bulk_update` - Bulk update inventory
- `POST /products/create` - Create single product
- `POST /products/bulk_create` - Bulk create products
- `PUT /products/update` - Update product
- `GET /orders/list` - Fetch orders
- `POST /orders/update_tracking` - Update order tracking

## Example Payloads

### Shopify Product (Input)
```json
{
  "id": "12345",
  "title": "Y2K Aesthetic Crop Top",
  "description": "Trendy crop top with Y2K vibes",
  "product_type": "Fashion",
  "tags": ["y2k", "trendy", "fashion"],
  "variants": [
    {
      "sku": "CROP-001",
      "price": "29.99",
      "inventory_quantity": 100
    }
  ],
  "images": ["https://example.com/image.jpg"]
}
```

### TikTok Product (AI-Enhanced Output)
```json
{
  "title": "Y2K Aesthetic Crop Top - Trending Fashion Item",
  "description": "Get the Y2K aesthetic with this trendy crop top! Perfect for TikTok fashion hauls. Limited stock!",
  "category": "Fashion",
  "hashtags": ["#y2k", "#aesthetic", "#fashion", "#trending", "#crop top", "#tiktokfashion"],
  "keywords": ["y2k", "aesthetic", "trendy", "fashion", "crop top", "viral"],
  "variants": [
    {
      "sku": "CROP-001",
      "price": "29.99",
      "inventory_quantity": 100
    }
  ],
  "images": ["https://example.com/image.jpg"]
}
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_ai_mapper.py

# Run in verbose mode
pytest -v
```

## Logging

Logs are written to both console and `sync_bot.log` file. Log levels:
- `DEBUG`: Detailed debugging information
- `INFO`: General information about operations
- `WARNING`: Warning messages
- `ERROR`: Error messages

Example log output:
```
2024-01-01 12:00:00 - INFO - Starting inventory sync...
2024-01-01 12:00:05 - INFO - Successfully updated inventory for SKU TEST-SKU-001 to 100
2024-01-01 12:00:10 - INFO - Inventory sync completed: 50 items updated
```

## Error Handling

The bot includes comprehensive error handling:

- **Retry Logic**: Automatic retries with exponential backoff (configurable via `MAX_RETRIES` and `RETRY_BACKOFF`)
- **Fallback Mapping**: If AI mapping fails, falls back to basic mapping using Shopify data
- **Logging**: All errors are logged with context
- **Graceful Degradation**: Continues processing other items if one fails

## Performance Optimization

- **Batch Processing**: Products and inventory updates are processed in batches (default: 100 items)
- **Caching**: AI mapping results are cached to avoid redundant API calls
- **Efficient Polling**: Only syncs changed items (can be enhanced with webhooks)
- **Parallel Processing**: Can be extended to use async/await for parallel API calls

## Future Enhancements

### Recommended Optimizations

1. **Webhooks Instead of Polling**: 
   - Implement Shopify webhooks for real-time inventory/product updates
   - Implement TikTok Shop webhooks for order notifications
   - Reduces API calls and latency

2. **Database Integration**:
   - Store sync state in database (PostgreSQL, MongoDB)
   - Track last sync timestamps
   - Enable incremental syncs

3. **Async/Await**:
   - Convert to async/await for parallel API calls
   - Use `aiohttp` for async HTTP requests
   - Improve throughput for large catalogs

4. **Redis Caching**:
   - Replace in-memory cache with Redis
   - Enable distributed caching across multiple instances
   - Better cache management and TTL

5. **Monitoring & Alerts**:
   - Integrate with monitoring tools (Datadog, New Relic)
   - Set up alerts for sync failures
   - Dashboard for sync statistics

6. **Rate Limiting**:
   - Implement rate limiting for API calls
   - Respect API rate limits from Shopify and TikTok
   - Queue system for high-volume operations

7. **Multi-Store Support**:
   - Support multiple Shopify stores
   - Support multiple TikTok Shop accounts
   - Configuration per store/account

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify API keys in `.env` file
   - Check token expiration
   - Ensure correct store URL format

2. **Rate Limiting**:
   - Reduce `SYNC_INTERVAL` or `BATCH_SIZE`
   - Implement rate limiting (see Future Enhancements)

3. **AI Mapping Failures**:
   - Check OpenAI API key and quota
   - Verify internet connection
   - Check OpenAI API status

4. **Inventory Sync Issues**:
   - Verify SKU mapping between Shopify and TikTok
   - Check inventory item IDs
   - Ensure warehouse/location IDs are correct

## License

This project is provided as-is for DTC brand agency use. Modify as needed for your specific requirements.

## Support

For issues or questions:
1. Check the logs in `sync_bot.log`
2. Run in dry-run mode to test: `python main.py --dry`
3. Review API documentation for Shopify and TikTok Shop
4. Check OpenAI API status and quota

## Contributing

To contribute improvements:
1. Add unit tests for new features
2. Follow PEP 8 style guidelines
3. Update README with new features
4. Test in dry-run mode before production use

---

**Note**: This bot is designed for production use but should be thoroughly tested in a staging environment before deploying to production. Always use dry-run mode first to verify configuration.
