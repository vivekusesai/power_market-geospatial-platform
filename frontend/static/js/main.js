/**
 * Main application initialization
 */
let map = null;
let layerManager = null;
let currentTileLayer = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', async () => {
    showLoading();

    try {
        // Initialize map
        initMap();

        // Initialize layer manager
        layerManager = new LayerManager(map);

        // Initialize details panel
        window.detailsPanel = new DetailsPanel();

        // Initialize timeline
        window.timeline = new Timeline(layerManager);

        // Load initial data
        await loadInitialData();

        // Set up event listeners
        setupEventListeners();

        // Start time display
        updateCurrentTime();
        setInterval(updateCurrentTime, 1000);

        hideLoading();
    } catch (error) {
        console.error('Error initializing application:', error);
        hideLoading();
        alert('Error loading application. Please refresh the page.');
    }
});

function initMap() {
    // Create map
    map = L.map('map', {
        center: CONFIG.map.defaultCenter,
        zoom: CONFIG.map.defaultZoom,
        minZoom: CONFIG.map.minZoom,
        maxZoom: CONFIG.map.maxZoom,
        zoomControl: true,
    });

    // Add default tile layer
    setTileLayer('dark');

    // Add scale control
    L.control.scale({ position: 'bottomleft' }).addTo(map);
}

function setTileLayer(layerName) {
    const tileConfig = CONFIG.tileLayers[layerName];
    if (!tileConfig) return;

    if (currentTileLayer) {
        map.removeLayer(currentTileLayer);
    }

    currentTileLayer = L.tileLayer(tileConfig.url, {
        attribution: tileConfig.attribution,
    }).addTo(map);
}

async function loadInitialData() {
    // Load ISO regions for dropdown
    try {
        const regions = await api.getISORegions();
        const isoSelect = document.getElementById('iso-select');
        regions.regions.forEach((region) => {
            const option = document.createElement('option');
            option.value = region;
            option.textContent = region;
            isoSelect.appendChild(option);
        });
    } catch (error) {
        console.log('No ISO regions available yet');
    }

    // Load ISO boundaries
    try {
        await layerManager.loadISOBoundaries();
    } catch (error) {
        console.log('No ISO boundaries available yet');
    }

    // Load assets
    const assetCount = await layerManager.refreshAssets();
    updateAssetCount(assetCount);

    // Set up map move handler
    map.on('moveend', debounce(async () => {
        const count = await layerManager.refreshAssets();
        updateAssetCount(count);
    }, 500));
}

function setupEventListeners() {
    // Base map selector
    document.querySelectorAll('input[name="basemap"]').forEach((input) => {
        input.addEventListener('change', (e) => {
            setTileLayer(e.target.value);
        });
    });

    // Asset layer toggle
    document.getElementById('layer-assets').addEventListener('change', (e) => {
        layerManager.toggleLayer('assets', e.target.checked);
    });

    // Fuel type filters
    document.querySelectorAll('#fuel-type-filters input').forEach((input) => {
        input.addEventListener('change', () => {
            layerManager.refreshAssets();
        });
    });

    // Status filters
    ['status-available', 'status-derated', 'status-forced', 'status-planned'].forEach((id) => {
        document.getElementById(id).addEventListener('change', () => {
            layerManager.refreshAssets();
        });
    });

    // ISO boundaries toggle
    document.getElementById('layer-iso-boundaries').addEventListener('change', async (e) => {
        if (e.target.checked) {
            await layerManager.loadISOBoundaries();
        } else {
            layerManager.hideLayer('iso_boundaries');
        }
    });

    // Load zones toggle
    document.getElementById('layer-load-zones').addEventListener('change', async (e) => {
        if (e.target.checked) {
            const isoRegion = document.getElementById('iso-select').value || null;
            await layerManager.loadLoadZones(isoRegion);
        } else {
            layerManager.hideLayer('load_zones');
        }
    });

    // Transmission zones toggle
    document.getElementById('layer-transmission-zones').addEventListener('change', async (e) => {
        if (e.target.checked) {
            const isoRegion = document.getElementById('iso-select').value || null;
            await layerManager.loadZones('transmission_zone', isoRegion);
        } else {
            layerManager.hideLayer('transmission_zone');
        }
    });

    // LMP heatmap toggle
    document.getElementById('layer-lmp-heatmap').addEventListener('change', async (e) => {
        const lmpLegend = document.getElementById('lmp-legend');
        if (e.target.checked) {
            lmpLegend.classList.remove('hidden');
            const dateTime = window.timeline.getSelectedDateTime();
            const component = document.getElementById('lmp-component').value;
            await layerManager.loadLMPHeatmap(dateTime.toISOString(), { component });
        } else {
            lmpLegend.classList.add('hidden');
            layerManager.hideLayer('lmp_heatmap');
        }
    });

    // LMP component selector
    document.getElementById('lmp-component').addEventListener('change', async (e) => {
        const lmpCheckbox = document.getElementById('layer-lmp-heatmap');
        if (lmpCheckbox.checked) {
            const dateTime = window.timeline.getSelectedDateTime();
            await layerManager.loadLMPHeatmap(dateTime.toISOString(), {
                component: e.target.value,
            });
        }
    });

    // Pricing nodes toggle
    document.getElementById('layer-pricing-nodes').addEventListener('change', async (e) => {
        if (e.target.checked) {
            await layerManager.loadPricingNodes();
            layerManager.showLayer('pricing_nodes');
        } else {
            layerManager.hideLayer('pricing_nodes');
        }
    });

    // ISO region selector
    document.getElementById('iso-select').addEventListener('change', async (e) => {
        await layerManager.refreshAssets();

        // Refresh zones if visible
        if (document.getElementById('layer-load-zones').checked) {
            await layerManager.loadLoadZones(e.target.value || null);
        }
    });

    // Panel toggles
    document.getElementById('toggle-left-panel').addEventListener('click', () => {
        const panel = document.getElementById('left-panel');
        panel.classList.toggle('collapsed');
    });

    document.getElementById('toggle-right-panel').addEventListener('click', () => {
        const panel = document.getElementById('right-panel');
        panel.classList.toggle('collapsed');
    });
}

function updateAssetCount(count) {
    document.getElementById('asset-count').textContent = `${count.toLocaleString()} assets`;
}

function updateCurrentTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleString();
}

function showLoading() {
    document.getElementById('loading-overlay').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

// Utility: Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
