/**
 * Application configuration
 */
const CONFIG = {
    // API Base URL
    API_BASE: '/api',

    // Map settings
    map: {
        defaultCenter: [39.8283, -98.5795], // US center
        defaultZoom: 5,
        minZoom: 3,
        maxZoom: 18,
    },

    // Tile layers
    tileLayers: {
        osm: {
            url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attribution: '&copy; OpenStreetMap contributors',
        },
        dark: {
            url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        },
        satellite: {
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attribution: '&copy; Esri',
        },
    },

    // Asset status colors
    statusColors: {
        available: '#27ae60',
        derated: '#f39c12',
        forced_outage: '#e74c3c',
        planned_maintenance: '#3498db',
        maintenance: '#3498db',
    },

    // Fuel type colors
    fuelColors: {
        coal: '#4a4a4a',
        natural_gas: '#f39c12',
        nuclear: '#9b59b6',
        hydro: '#3498db',
        wind: '#1abc9c',
        solar: '#f1c40f',
        oil: '#8b4513',
        biomass: '#27ae60',
        geothermal: '#e74c3c',
        battery: '#2ecc71',
        other: '#95a5a6',
    },

    // Zone colors
    zoneColors: {
        PJM: '#1f77b4',
        MISO: '#ff7f0e',
        SPP: '#2ca02c',
        ERCOT: '#d62728',
        NYISO: '#9467bd',
        ISONE: '#8c564b',
        CAISO: '#e377c2',
    },

    // LMP color scale
    lmpColorScale: {
        min: 0,
        max: 100,
        colors: ['#27ae60', '#f39c12', '#e74c3c'], // green -> yellow -> red
    },

    // Clustering settings
    clustering: {
        enabled: true,
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true,
        disableClusteringAtZoom: 10,
    },

    // Refresh intervals (ms)
    refreshIntervals: {
        assets: 300000, // 5 minutes
        pricing: 60000, // 1 minute
    },

    // Performance limits
    limits: {
        maxAssetsPerRequest: 5000,
        maxPricingRecords: 10000,
    },
};

// Status display names
const STATUS_LABELS = {
    available: 'Available',
    derated: 'Derated',
    forced_outage: 'Forced Outage',
    planned_maintenance: 'Planned Maintenance',
    maintenance: 'Maintenance',
};

// Fuel type display names
const FUEL_LABELS = {
    coal: 'Coal',
    natural_gas: 'Natural Gas',
    nuclear: 'Nuclear',
    hydro: 'Hydro',
    wind: 'Wind',
    solar: 'Solar',
    oil: 'Oil',
    biomass: 'Biomass',
    geothermal: 'Geothermal',
    battery: 'Battery Storage',
    other: 'Other',
};
