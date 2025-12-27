# Shopify-Only AI Sync Bot with Mock TikTok

A production-ready Python automation tool for syncing inventory and products from Shopify with AI optimization. Designed as an MVP for a ($497 beta) agency service. Runs on Render, syncs Shopify inventory/products with AI optimization, and mocks TikTok API calls until approval (3-5 days). Built for DTC brand agencies requiring low-latency, error-handling, and scalable operations.

## Features

- **Shopify Sync**: Polls Shopify dev store every 5 minutes for product/inventory changes using direct HTTP requests (no external library dependencies)
- **AI Mapping**: Uses OpenAI (gpt-4o-mini, v1.51.0) to optimize Shopify product titles/descriptions with trending hashtags (e.g., #TikTokMadeMeBuyIt). Includes fallback to mock data if OpenAI unavailable.
- **Mock TikTok**: Automatically mocks TikTok API calls if `TIKTOK_APP_KEY` is missing. Logs `[MOCK]` messages until TikTok API approval (3-5 days).
- **Error Prevention**:
  - Validates all env vars on startup (raises ValueError if missing)
  - Handles OpenAI initialization failures with retries (3x) and fallback to mock data
  - Checks Shopify API rate limits (warns if >90% usage via `X-Shopify-Shop-Api-Call-Limit` header)
  - Logs all errors to file + console with timestamps
- **Scheduling**: Configurable polling intervals (default: 5 minutes) using APScheduler
- **Render Optimized**: Includes `runtime.txt` for Python 3.12, Flask health endpoint, auto-restart on crash
- **Testing**: `--dry-run` flag to simulate without API calls, comprehensive unit tests

## Tech Stack

- **Python 3.12+** (specified in `runtime.txt` for Render)
- **Shopify**: Direct HTTP requests via `requests` library (no external Shopify library needed)
- **TikTok Shop**: `requests` for API calls (base URL: `https://partner.tiktokshop.com/api`) - MOCK MODE until API approval
- **OpenAI**: `openai==1.51.0` library (gpt-4o-mini model) with proxy error handling
- **Scheduling**: `APScheduler==3.10.4` for cron-like polling
- **Web Framework**: `flask==3.0.3` for `/health` endpoint (Render deployment)
- **Environment**: `.env` file for configuration
- **Logging**: Python `logging` module (console + file output: `sync_bot.log`)

## Installation

### Prerequisites

- Python 3.12 or higher
- Shopify store with API access (see "Getting Your Shopify Token" below)
- TikTok Shop Partner account with API credentials (optional - will mock if not provided)
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
   # Required: Shopify Configuration
   SHOPIFY_STORE=your-store.myshopify.com
   SHOPIFY_TOKEN=your_shopify_access_token
   # Note: SHOPIFY_ACCESS_TOKEN also works (backward compatibility)

   # Required: OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=gpt-4o-mini

   # Optional: TikTok Shop Configuration (will mock if not provided)
   TIKTOK_APP_KEY=your_tiktok_app_key
   TIKTOK_SECRET=your_tiktok_secret
   TIKTOK_API_BASE=https://partner.tiktokshop.com/api

   # Optional: Sync Settings
   SYNC_INTERVAL=300
   BATCH_SIZE=100
   MAX_RETRIES=3
   RETRY_BACKOFF=2.0
   ```

   **Important**: The bot will automatically run in MOCK MODE for TikTok if `TIKTOK_APP_KEY` is missing or doesn't start with `app_`. This allows you to test and deploy while waiting for TikTok API approval (3-5 days).

### Getting Your Shopify Admin API Access Token

If you don't have a Shopify token yet, follow these steps:

1. **Log into your Shopify Admin** (https://your-store.myshopify.com/admin)

2. **Navigate to Apps**:
   - Click **Settings** (bottom left)
   - Click **Apps and sales channels**
   - Click **Develop apps** (top right)

3. **Create a new app**:
   - Click **Create an app**
   - Enter a name (e.g., "TikTok Sync Bot")
   - Enter your email (optional)
   - Click **Create app**

4. **Configure API scopes**:
   - Click **Configure Admin API scopes**
   - Enable these scopes (minimum required):
     - ✅ `read_products` - Read product information
     - ✅ `read_inventory` - Read inventory levels
     - ✅ `write_inventory` (optional) - Update inventory levels
   - Click **Save**

5. **Install the app**:
   - Click **Install app** (top right)
   - Confirm installation

6. **Copy the Admin API access token**:
   - After installation, you'll see **API credentials**
   - Under **Admin API access token**, click **Reveal token once**
   - **Copy the token** (it starts with `shpat_...`)
   - ⚠️ **Important**: Save this token immediately - you can only see it once!
   - ⚠️ **Note**: Make sure you're copying the **Admin API access token** (starts with `shpat_`), NOT the Session token (starts with `shpss_`) or other tokens

7. **Add to your `.env` file**:
   ```env
   SHOPIFY_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

**Note**: If you lose the token, you'll need to:
- Go back to the app settings
- Click **API credentials**
- Click **Regenerate** to create a new token

## Usage

### Command Line Interface

The bot can be run in several modes:

#### Single Run (One-time sync)

```bash
# Full sync (inventory + products)
python main.py --mode=full

# Inventory sync only
python main.py --mode=inventory

# Product sync only
python main.py --mode=products
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
python main.py --mode=full --dry-run

# Test with limited products
python main.py --mode=products --dry-run --limit=10
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

## Render Deployment

### Setup on Render

1. **Create a new Web Service** on Render
2. **Connect your GitHub repository** (https://github.com/8Kuza/ShopifyTiktokAI)
3. **Configure Build & Start Commands**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py --interval=300`
4. **Add Environment Variables** in Render dashboard:
   - `SHOPIFY_STORE` (required)
   - `SHOPIFY_TOKEN` (required)
   - `OPENAI_API_KEY` (required)
   - (Optional) `TIKTOK_APP_KEY`, `TIKTOK_SECRET` (will mock if not provided)
   - **Note**: `PORT` and `HOST` are automatically set by Render - do NOT set these manually
5. **Health Check**: 
   - Render will automatically check `/health` endpoint
   - The endpoint returns JSON: `{"status": "healthy", "message": "AI Sync Bot Running", ...}`
   - Returns `200` if healthy, `503` if critical services are down
6. **Auto-restart**: Render will automatically restart the service on crash

### Health Endpoint Details

The `/health` endpoint provides:
- **Status**: `healthy`, `degraded`, or `error`
- **Flask**: Always `running` if endpoint is accessible
- **Scheduler**: `running` or `stopped` (shows if sync scheduler is active)
- **OpenAI**: `available` or `unavailable` (shows if AI mapping is working)

Example response:
```json
{
  "status": "healthy",
  "message": "AI Sync Bot Running",
  "flask": "running",
  "scheduler": "running",
  "openai": "available"
}
```

### Render Optimization Tips

- Use **Free tier** for testing, **Starter tier** ($7/month) for production
- Enable **Auto-Deploy** from main branch
- Set up **Health Checks** to monitor service status
- Use **Environment Groups** to manage multiple services

## Future Enhancements

### Recommended Optimizations

1. **Shopify Webhooks Instead of Polling** (High Priority):
   - Implement Shopify webhooks for real-time inventory/product updates
   - Reduces API calls from every 5 minutes to instant updates
   - Endpoints: `/products/create`, `/products/update`, `/inventory_levels/update`
   - Reduces latency and API usage

2. **TikTok Shop Webhooks** (After API Approval):
   - Implement TikTok Shop webhooks for order notifications
   - Real-time order processing instead of polling
   - Endpoints: `/orders/status_change`, `/orders/fulfillment`

3. **Database Integration**:
   - Store sync state in PostgreSQL (Render PostgreSQL addon)
   - Track last sync timestamps per product
   - Enable incremental syncs (only sync changed items)
   - Store mapping cache for faster lookups

4. **Render Auto-Scaling**:
   - Configure auto-scaling based on queue length
   - Handle high-volume syncs during peak times
   - Use Render's background workers for heavy processing

5. **Async/Await**:
   - Convert to async/await for parallel API calls
   - Use `aiohttp` for async HTTP requests
   - Improve throughput for large catalogs (1000+ products)

6. **Redis Caching** (Render Redis addon):
   - Replace in-memory cache with Redis
   - Enable distributed caching across multiple instances
   - Better cache management and TTL
   - Share cache between web service instances

7. **Monitoring & Alerts**:
   - Integrate with Render's built-in monitoring
   - Set up email/Slack alerts for sync failures
   - Dashboard for sync statistics (success/failure rates)

8. **Multi-Store Support**:
   - Support multiple Shopify stores
   - Support multiple TikTok Shop accounts
   - Configuration per store/account via environment groups

## Mock Mode

The bot automatically runs in **MOCK MODE** for TikTok when:
- `TIKTOK_APP_KEY` is not set
- `TIKTOK_APP_KEY` doesn't start with `app_`

In MOCK MODE:
- All TikTok API calls are logged with `[MOCK]` prefix
- No actual TikTok API requests are made
- Perfect for testing and deployment while waiting for TikTok API approval (3-5 days)
- Once TikTok API keys are approved, simply add them to `.env` and the bot will automatically switch to real API calls

Example MOCK output:
```
[MOCK] TikTok Shop: SKU TEST-001 → Stock 100
[MOCK] TikTok Shop: Would create 5 products
```

## Troubleshooting

### Common Issues

1. **Shopify API Authentication Error (401 Unauthorized)**:
   - **Error**: `Invalid API key or access token (unrecognized login or wrong password)`
   - **Fix**: 
     - Verify your `SHOPIFY_TOKEN` is correct in your `.env` file or Render environment variables
     - Ensure the token hasn't expired (regenerate in Shopify Admin if needed)
     - Check that the token has required permissions: `read_products`, `read_inventory`, `write_inventory`
     - To get a new token: Shopify Admin → Settings → Apps and sales channels → Develop apps → Create app → Configure Admin API scopes → Install app → Copy Admin API access token
   - **Note**: The bot will not retry on authentication errors (401/403) as retrying won't help

2. **OpenAI Client Initialization Error (`proxies` parameter)**:
   - **Fixed**: The bot now handles proxy environment variables automatically
   - If you still see this error, check that `openai==1.51.0` is installed correctly
   - The bot will automatically clear proxy env vars during initialization
   - **Fallback**: The bot will use mock AI responses if OpenAI fails to initialize (bot continues to function)

3. **Missing Environment Variables**:
   - **Error**: `Missing required environment variables: SHOPIFY_STORE, SHOPIFY_TOKEN, OPENAI_API_KEY`
   - **Fix**: Ensure all required variables are set in your `.env` file or Render dashboard
   - Run with `--dry-run` to test configuration without API calls

4. **Shopify API Rate Limiting**:
   - The bot automatically monitors rate limits via `X-Shopify-Shop-Api-Call-Limit` header
   - Warnings are logged when usage exceeds 90%
   - **Fix**: Reduce `SYNC_INTERVAL` or `BATCH_SIZE` in `.env`

5. **OpenAI API Failures**:
   - The bot automatically falls back to mock AI responses if OpenAI fails
   - Check OpenAI API key and quota
   - Verify internet connection
   - Check OpenAI API status at https://status.openai.com

6. **Render Deployment Issues / 404 on /health Endpoint**:
   - **Error**: `404 Not Found` when accessing `/health` endpoint
   - **Fix**: 
     - Ensure `runtime.txt` specifies `python-3.12`
     - Check that all environment variables are set in Render dashboard
     - Verify Flask is starting correctly - check Render logs for "Flask health endpoint available"
     - The bot now automatically uses Render's `PORT` environment variable (no need to set it manually)
     - Flask should start on `0.0.0.0` (default) - Render sets this automatically
     - Check Render logs for Flask startup errors
     - Verify the start command is: `python main.py --interval=300`
   - **Debugging Steps**:
     1. Check Render logs for: `"Starting Flask health endpoint on 0.0.0.0:XXXX"`
     2. Verify PORT is being read: Look for log message with the port number
     3. Test locally: `python main.py --dry-run` and visit `http://localhost:5000/health`
     4. Check if Flask thread is starting: Look for "Flask health endpoint available" in logs
     5. If Flask fails to start, the bot will continue running but health endpoint won't be available
   - **Common Causes**:
     - Flask thread not starting (check for exceptions in logs)
     - Port conflict (Render handles this automatically)
     - Missing Flask import (should not happen if requirements.txt is correct)
     - Flask app not registered properly (should be fixed in latest version)

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
