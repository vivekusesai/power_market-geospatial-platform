# Power Market Geospatial Platform

A production-ready Python web application for visualizing power market geospatial data, including transmission/generation assets, unit outages, settlement pricing, market zones, and time-based replay of grid events.

## Features

- **Interactive Map**: Leaflet-based map with zoom, pan, layer toggling, hover tooltips, and click selection
- **Asset Visualization**: Generator units displayed with status colors (Available, Derated, Forced Outage, Planned Maintenance)
- **Outage Management**: View and filter outages by type, status, and time range
- **LMP Heatmap**: Nodal/zonal LMP visualization with congestion and loss components
- **Market Geography**: ISO boundaries, load zones, transmission zones, and pricing nodes
- **Time Slider**: Replay historical outages and price intervals
- **Multi-ISO Support**: Modular design supporting PJM, MISO, SPP, ERCOT, NYISO, ISONE, and more

## Architecture

```
power_market-geospatial-platform/
├── backend/                    # FastAPI backend
│   ├── api/                    # API route handlers
│   │   ├── assets.py          # GET /assets, /assets/{id}
│   │   ├── outages.py         # GET /outages, /outages/active
│   │   ├── pricing.py         # GET /pricing/heatmap, /pricing/nodes
│   │   └── zones.py           # GET /zones, /zones/iso-boundaries
│   ├── models/                 # SQLAlchemy + GeoAlchemy2 models
│   │   ├── asset.py           # Asset model with PostGIS Point
│   │   ├── outage.py          # Outage model with time ranges
│   │   ├── pricing.py         # PricingNode and PricingRecord
│   │   └── zone.py            # Zone model with PostGIS MultiPolygon
│   ├── schemas/                # Pydantic request/response models
│   ├── services/               # Business logic layer
│   ├── ingestion/              # Data loaders (CSV, GeoJSON, Parquet)
│   ├── config.py               # Application settings
│   ├── database.py             # Async database connection
│   └── main.py                 # FastAPI application
├── frontend/                   # Leaflet + vanilla JS frontend
│   ├── index.html              # Main HTML template
│   └── static/
│       ├── css/main.css        # Styling
│       └── js/
│           ├── config.js       # Configuration
│           ├── api.js          # API client
│           ├── layers.js       # Map layer management
│           ├── details.js      # Details panel
│           ├── timeline.js     # Time slider control
│           └── main.js         # Application initialization
├── alembic/                    # Database migrations
├── scripts/
│   └── seed_data.py            # Sample data generator
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Container build
└── pyproject.toml              # Python dependencies
```

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, GeoAlchemy2, Pydantic v2
- **Database**: PostgreSQL 16 + PostGIS 3.4
- **Frontend**: Leaflet.js, Leaflet.markercluster, Chart.js
- **Deployment**: Docker, Docker Compose

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
cd power_market-geospatial-platform

# Start PostgreSQL with PostGIS
docker-compose up -d db

# Wait for database to be ready, then run migrations and seed data
docker-compose --profile setup run migrate

# Start the API server
docker-compose up -d api

# Open http://localhost:8000 in your browser
```

### Option 2: Local Development

#### Prerequisites
- Python 3.11+
- PostgreSQL 14+ with PostGIS extension
- Node.js (optional, for frontend development)

#### Setup

1. **Create and activate virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

2. **Install dependencies**:
```bash
pip install -e .
```

3. **Set up PostgreSQL with PostGIS**:
```sql
CREATE DATABASE power_market;
\c power_market
CREATE EXTENSION postgis;
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. **Run database migrations**:
```bash
alembic upgrade head
```

6. **Generate sample data**:
```bash
python scripts/seed_data.py
```

7. **Start the development server**:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

8. **Open in browser**: http://localhost:8000

## API Endpoints

### Assets
- `GET /api/assets` - Get assets as GeoJSON (supports `bbox`, `iso_region`, `fuel_type`, `at_time`)
- `GET /api/assets/{asset_id}` - Get asset details
- `GET /api/assets/regions` - List available ISO regions
- `GET /api/assets/fuel-types` - Get capacity distribution by fuel type

### Outages
- `GET /api/outages` - Get outages as GeoJSON (supports `start`, `end`, `iso_region`, `outage_type`)
- `GET /api/outages/active` - Get currently active outages
- `GET /api/outages/stats` - Get outage statistics
- `GET /api/outages/asset/{asset_id}` - Get outage history for an asset

### Pricing
- `GET /api/pricing/heatmap` - Get LMP heatmap data for a timestamp
- `GET /api/pricing/nodes` - Get pricing nodes as GeoJSON
- `GET /api/pricing/node/{node_id}/timeseries` - Get LMP time series
- `GET /api/pricing/timestamps` - Get available pricing timestamps

### Zones
- `GET /api/zones` - Get zones as GeoJSON
- `GET /api/zones/iso-boundaries` - Get ISO boundary polygons
- `GET /api/zones/load-zones` - Get load zone polygons

## Data Model

### Assets
| Column | Type | Description |
|--------|------|-------------|
| asset_id | VARCHAR(50) | Unique identifier |
| asset_name | VARCHAR(255) | Plant name |
| fuel_type | ENUM | coal, natural_gas, nuclear, wind, solar, etc. |
| capacity_mw | FLOAT | Nameplate capacity |
| latitude, longitude | FLOAT | Location |
| geom | GEOMETRY(Point) | PostGIS geometry |
| iso_region | VARCHAR(20) | ISO/RTO region |
| zone | VARCHAR(50) | Load zone |

### Outages
| Column | Type | Description |
|--------|------|-------------|
| outage_id | VARCHAR(50) | Unique identifier |
| asset_id | VARCHAR(50) | Foreign key to assets |
| outage_type | ENUM | planned, forced, maintenance, derate |
| start_time, end_time | TIMESTAMPTZ | Outage duration |
| status | ENUM | active, scheduled, completed, cancelled |
| cause_code | VARCHAR(50) | Outage cause category |

### Pricing
| Column | Type | Description |
|--------|------|-------------|
| node_id | VARCHAR(50) | Pricing node ID |
| timestamp | TIMESTAMPTZ | Price interval |
| lmp_total | FLOAT | Total LMP ($/MWh) |
| lmp_energy | FLOAT | Energy component |
| lmp_congestion | FLOAT | Congestion component |
| lmp_loss | FLOAT | Loss component |

## Performance Optimizations

- **Spatial Indexing**: GiST indexes on all geometry columns for fast bounding box queries
- **BRIN Indexes**: Block Range Indexes on timestamp columns for efficient time series queries
- **Clustering**: Leaflet.markercluster for handling 10,000+ assets without performance degradation
- **Lazy Loading**: Assets loaded dynamically based on map viewport
- **Async I/O**: FastAPI with asyncpg for non-blocking database operations
- **Connection Pooling**: SQLAlchemy async connection pool (20 connections, 10 overflow)

## Connecting Real ISO Data

To integrate with actual ISO market data:

1. **Obtain API credentials** from your target ISO (e.g., PJM Data Miner, ERCOT MIS)

2. **Create a data fetcher** in `backend/ingestion/`:
```python
# backend/ingestion/iso_fetchers/pjm.py
class PJMDataFetcher:
    async def fetch_assets(self): ...
    async def fetch_outages(self, start, end): ...
    async def fetch_lmp(self, timestamp): ...
```

3. **Set up scheduled ingestion** using APScheduler or Celery:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(fetch_pjm_lmp, 'interval', minutes=5)
```

4. **Map ISO data formats** to the application schema using the ingestion utilities:
```python
loader = CSVLoader(db)
await loader.load_assets(
    "pjm_assets.csv",
    iso_region="PJM",
    column_mapping={"unit_id": "asset_id", "unit_name": "asset_name"}
)
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
