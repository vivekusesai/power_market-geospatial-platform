# Power Market Geospatial Platform

A production-ready Python web application for visualizing power market geospatial data, including transmission/generation assets, unit outages, settlement pricing, market zones, and time-based replay of grid events.

## Features

- **Interactive Map**: Leaflet-based map with zoom/pan, layer toggling, hover tooltips, and click selection
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
│   ├── models/                 # SQLAlchemy + GeoAlchemy2 models
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
│       └── js/                 # Map, API client, layers
├── alembic/                    # Database migrations
├── scripts/
│   └── seed_data.py            # Sample data generator
└── pyproject.toml              # Python dependencies
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, GeoAlchemy2, Pydantic v2
- **Database**: PostgreSQL 14+ with PostGIS extension
- **Frontend**: Leaflet.js, Leaflet.markercluster, Chart.js

---

## Local Development Setup

### Prerequisites

1. **Python 3.11+**
2. **PostgreSQL 14+** with PostGIS extension installed

### Step 1: Install PostgreSQL with PostGIS

#### Windows
Download and install from https://www.postgresql.org/download/windows/

During installation, use Stack Builder to add PostGIS extension, or install separately from https://postgis.net/windows_downloads/

#### macOS
```bash
brew install postgresql@16 postgis
brew services start postgresql@16
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib postgis
sudo systemctl start postgresql
```

### Step 2: Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and enable PostGIS
CREATE DATABASE power_market;
\c power_market
CREATE EXTENSION postgis;
\q
```

### Step 3: Clone and Setup Python Environment

```bash
cd power_market-geospatial-platform

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -e .
```

### Step 4: Configure Environment

Edit `.env` file with your PostgreSQL credentials:

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/power_market
DATABASE_URL_SYNC=postgresql://postgres:YOUR_PASSWORD@localhost:5432/power_market
```

### Step 5: Run Database Migrations

```bash
alembic upgrade head
```

### Step 6: Generate Sample Data

```bash
python scripts/seed_data.py
```

This creates:
- **1,200 generator assets** across 6 ISOs (PJM, MISO, SPP, ERCOT, NYISO, ISONE)
- **250 outages** (active and historical)
- **24 hours of LMP pricing data**
- **Zone boundaries** for each ISO

### Step 7: Start Development Server

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 8: Open Application

Navigate to **http://localhost:8000** in your browser.

---

## API Endpoints

### Assets
| Endpoint | Description |
|----------|-------------|
| `GET /api/assets` | Get assets as GeoJSON (supports `bbox`, `iso_region`, `fuel_type`, `at_time`) |
| `GET /api/assets/{asset_id}` | Get asset details |
| `GET /api/assets/regions` | List available ISO regions |
| `GET /api/assets/fuel-types` | Get capacity distribution by fuel type |

### Outages
| Endpoint | Description |
|----------|-------------|
| `GET /api/outages` | Get outages as GeoJSON (supports `start`, `end`, `iso_region`, `outage_type`) |
| `GET /api/outages/active` | Get currently active outages |
| `GET /api/outages/stats` | Get outage statistics |
| `GET /api/outages/asset/{asset_id}` | Get outage history for an asset |

### Pricing
| Endpoint | Description |
|----------|-------------|
| `GET /api/pricing/heatmap` | Get LMP heatmap data for a timestamp |
| `GET /api/pricing/nodes` | Get pricing nodes as GeoJSON |
| `GET /api/pricing/node/{node_id}/timeseries` | Get LMP time series |
| `GET /api/pricing/timestamps` | Get available pricing timestamps |

### Zones
| Endpoint | Description |
|----------|-------------|
| `GET /api/zones` | Get zones as GeoJSON |
| `GET /api/zones/iso-boundaries` | Get ISO boundary polygons |
| `GET /api/zones/load-zones` | Get load zone polygons |

---

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

---

## Connecting Real ISO Data

To integrate with actual ISO market data:

1. **Obtain API credentials** from your target ISO (e.g., PJM Data Miner, ERCOT MIS)

2. **Create a data fetcher** in `backend/ingestion/`:
```python
class PJMDataFetcher:
    async def fetch_assets(self): ...
    async def fetch_outages(self, start, end): ...
    async def fetch_lmp(self, timestamp): ...
```

3. **Map ISO data formats** using the ingestion utilities:
```python
loader = CSVLoader(db)
await loader.load_assets(
    "pjm_assets.csv",
    iso_region="PJM",
    column_mapping={"unit_id": "asset_id", "unit_name": "asset_name"}
)
```

---

## Troubleshooting

### "PostGIS extension not found"
```sql
-- Connect to your database and run:
CREATE EXTENSION postgis;
```

### "Connection refused to localhost:5432"
Ensure PostgreSQL service is running:
```bash
# Windows
net start postgresql-x64-16

# macOS
brew services start postgresql@16

# Linux
sudo systemctl start postgresql
```

### "Password authentication failed"
Check your `.env` file has the correct PostgreSQL password.

---

## License

MIT License
