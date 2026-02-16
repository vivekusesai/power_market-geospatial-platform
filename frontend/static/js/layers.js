/**
 * Layer management for the map
 */
class LayerManager {
    constructor(map) {
        this.map = map;
        this.layers = {};
        this.assetCluster = null;
        this.pricingCluster = null;

        this.initClusterGroups();
    }

    initClusterGroups() {
        // Asset cluster group
        this.assetCluster = L.markerClusterGroup({
            maxClusterRadius: CONFIG.clustering.maxClusterRadius,
            spiderfyOnMaxZoom: CONFIG.clustering.spiderfyOnMaxZoom,
            disableClusteringAtZoom: CONFIG.clustering.disableClusteringAtZoom,
            iconCreateFunction: (cluster) => {
                const childCount = cluster.getChildCount();
                let c = ' marker-cluster-';
                if (childCount < 10) {
                    c += 'small';
                } else if (childCount < 100) {
                    c += 'medium';
                } else {
                    c += 'large';
                }
                return L.divIcon({
                    html: '<div>' + childCount + '</div>',
                    className: 'marker-cluster' + c,
                    iconSize: new L.Point(40, 40),
                });
            },
        });
        this.map.addLayer(this.assetCluster);

        // Pricing nodes cluster
        this.pricingCluster = L.markerClusterGroup({
            maxClusterRadius: 30,
            disableClusteringAtZoom: 8,
        });
    }

    // Load assets as GeoJSON
    async loadAssets(params = {}) {
        try {
            const data = await api.getAssets(params);
            this.updateAssetLayer(data);
            return data.features.length;
        } catch (error) {
            console.error('Error loading assets:', error);
            return 0;
        }
    }

    updateAssetLayer(geojson) {
        this.assetCluster.clearLayers();

        if (!geojson || !geojson.features) return;

        const assetLayer = L.geoJSON(geojson, {
            pointToLayer: (feature, latlng) => {
                const props = feature.properties;
                const status = props.status || 'available';
                const color = CONFIG.statusColors[status] || CONFIG.statusColors.available;

                const marker = L.circleMarker(latlng, {
                    radius: this.getMarkerRadius(props.capacity_mw),
                    fillColor: color,
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8,
                });

                // Bind popup
                marker.bindPopup(this.createAssetPopup(props));

                // Click handler
                marker.on('click', () => {
                    window.detailsPanel.showAssetDetails(props);
                });

                return marker;
            },
            filter: (feature) => this.shouldShowAsset(feature.properties),
        });

        this.assetCluster.addLayer(assetLayer);
        this.layers.assets = assetLayer;
    }

    getMarkerRadius(capacityMw) {
        if (capacityMw > 1000) return 10;
        if (capacityMw > 500) return 8;
        if (capacityMw > 100) return 6;
        return 5;
    }

    createAssetPopup(props) {
        const status = props.status || 'available';
        const statusLabel = STATUS_LABELS[status] || status;
        const fuelLabel = FUEL_LABELS[props.fuel_type] || props.fuel_type;

        return `
            <div class="asset-popup">
                <h4>${props.asset_name}</h4>
                <p><strong>Fuel:</strong> ${fuelLabel}</p>
                <p><strong>Capacity:</strong> ${props.capacity_mw.toFixed(1)} MW</p>
                <p><strong>Zone:</strong> ${props.zone || 'N/A'}</p>
                <span class="status ${status}">${statusLabel}</span>
            </div>
        `;
    }

    shouldShowAsset(props) {
        // Check fuel type filter
        const fuelFilter = document.querySelector(`[data-fuel="${props.fuel_type}"]`);
        if (fuelFilter && !fuelFilter.checked) return false;

        // Check status filter
        const status = props.status || 'available';
        const statusMap = {
            available: 'status-available',
            derated: 'status-derated',
            forced_outage: 'status-forced',
            planned_maintenance: 'status-planned',
            maintenance: 'status-planned',
        };

        const statusFilter = document.getElementById(statusMap[status]);
        if (statusFilter && !statusFilter.checked) return false;

        return true;
    }

    // Load zone boundaries
    async loadZones(zoneType = null, isoRegion = null) {
        try {
            const params = {};
            if (zoneType) params.zone_type = zoneType;
            if (isoRegion) params.iso_region = isoRegion;

            const data = await api.getZones(params);
            this.updateZoneLayer(data, zoneType || 'zones');
            return data.features.length;
        } catch (error) {
            console.error('Error loading zones:', error);
            return 0;
        }
    }

    async loadISOBoundaries() {
        try {
            const data = await api.getISOBoundaries();
            this.updateZoneLayer(data, 'iso_boundaries');
            return data.features.length;
        } catch (error) {
            console.error('Error loading ISO boundaries:', error);
            return 0;
        }
    }

    async loadLoadZones(isoRegion = null) {
        try {
            const data = await api.getLoadZones(isoRegion);
            this.updateZoneLayer(data, 'load_zones');
            return data.features.length;
        } catch (error) {
            console.error('Error loading load zones:', error);
            return 0;
        }
    }

    updateZoneLayer(geojson, layerName) {
        // Remove existing layer
        if (this.layers[layerName]) {
            this.map.removeLayer(this.layers[layerName]);
        }

        if (!geojson || !geojson.features || geojson.features.length === 0) return;

        const zoneLayer = L.geoJSON(geojson, {
            style: (feature) => {
                const props = feature.properties;
                return {
                    fillColor: props.fill_color || CONFIG.zoneColors[props.iso_region] || '#3388ff',
                    color: props.stroke_color || props.fill_color || '#3388ff',
                    weight: 2,
                    opacity: 0.8,
                    fillOpacity: props.fill_opacity || 0.2,
                };
            },
            onEachFeature: (feature, layer) => {
                const props = feature.properties;

                layer.bindPopup(`
                    <div class="zone-popup">
                        <h4>${props.zone_name}</h4>
                        <p><strong>Type:</strong> ${props.zone_type}</p>
                        <p><strong>ISO:</strong> ${props.iso_region}</p>
                    </div>
                `);

                layer.on('click', () => {
                    window.detailsPanel.showZoneDetails(props);
                });
            },
        });

        this.layers[layerName] = zoneLayer;

        // Add to map (below assets)
        zoneLayer.addTo(this.map);
        if (this.assetCluster) {
            this.assetCluster.bringToFront();
        }
    }

    // LMP Heatmap
    async loadLMPHeatmap(timestamp, params = {}) {
        try {
            const data = await api.getLMPHeatmap(timestamp, params);
            this.updateLMPHeatmap(data);
            return data.points.length;
        } catch (error) {
            console.error('Error loading LMP heatmap:', error);
            return 0;
        }
    }

    updateLMPHeatmap(data) {
        // Remove existing layer
        if (this.layers.lmp_heatmap) {
            this.map.removeLayer(this.layers.lmp_heatmap);
        }

        if (!data || !data.points || data.points.length === 0) return;

        const { min_lmp, max_lmp, points } = data;

        // Update legend
        document.getElementById('lmp-min').textContent = `$${min_lmp.toFixed(0)}`;
        document.getElementById('lmp-max').textContent = `$${max_lmp.toFixed(0)}`;

        const heatmapLayer = L.layerGroup();

        points.forEach((point) => {
            const color = this.getLMPColor(point.lmp_total, min_lmp, max_lmp);

            const circle = L.circleMarker([point.latitude, point.longitude], {
                radius: 6,
                fillColor: color,
                color: color,
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.6,
            });

            circle.bindPopup(`
                <div class="lmp-popup">
                    <h4>${point.node_id}</h4>
                    <p><strong>Total LMP:</strong> $${point.lmp_total.toFixed(2)}/MWh</p>
                    <p><strong>Energy:</strong> $${(point.lmp_energy || 0).toFixed(2)}/MWh</p>
                    <p><strong>Congestion:</strong> $${(point.lmp_congestion || 0).toFixed(2)}/MWh</p>
                    <p><strong>Loss:</strong> $${(point.lmp_loss || 0).toFixed(2)}/MWh</p>
                </div>
            `);

            heatmapLayer.addLayer(circle);
        });

        this.layers.lmp_heatmap = heatmapLayer;
        heatmapLayer.addTo(this.map);
    }

    getLMPColor(value, min, max) {
        const ratio = (value - min) / (max - min || 1);

        // Green -> Yellow -> Red gradient
        if (ratio < 0.5) {
            // Green to Yellow
            const r = Math.round(255 * (ratio * 2));
            const g = 200;
            const b = 50;
            return `rgb(${r}, ${g}, ${b})`;
        } else {
            // Yellow to Red
            const r = 255;
            const g = Math.round(200 * (1 - (ratio - 0.5) * 2));
            const b = 50;
            return `rgb(${r}, ${g}, ${b})`;
        }
    }

    // Pricing nodes
    async loadPricingNodes(params = {}) {
        try {
            const data = await api.getPricingNodes(params);
            this.updatePricingNodes(data);
            return data.features.length;
        } catch (error) {
            console.error('Error loading pricing nodes:', error);
            return 0;
        }
    }

    updatePricingNodes(geojson) {
        this.pricingCluster.clearLayers();

        if (!geojson || !geojson.features) return;

        const nodeLayer = L.geoJSON(geojson, {
            pointToLayer: (feature, latlng) => {
                const props = feature.properties;

                return L.circleMarker(latlng, {
                    radius: 4,
                    fillColor: '#9b59b6',
                    color: '#fff',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.7,
                });
            },
            onEachFeature: (feature, layer) => {
                const props = feature.properties;
                layer.bindPopup(`
                    <div class="node-popup">
                        <h4>${props.node_name}</h4>
                        <p><strong>ID:</strong> ${props.node_id}</p>
                        <p><strong>Type:</strong> ${props.node_type}</p>
                    </div>
                `);
            },
        });

        this.pricingCluster.addLayer(nodeLayer);
        this.layers.pricing_nodes = nodeLayer;
    }

    // Layer visibility
    showLayer(layerName) {
        if (layerName === 'assets') {
            this.map.addLayer(this.assetCluster);
        } else if (layerName === 'pricing_nodes') {
            this.map.addLayer(this.pricingCluster);
        } else if (this.layers[layerName]) {
            this.map.addLayer(this.layers[layerName]);
        }
    }

    hideLayer(layerName) {
        if (layerName === 'assets') {
            this.map.removeLayer(this.assetCluster);
        } else if (layerName === 'pricing_nodes') {
            this.map.removeLayer(this.pricingCluster);
        } else if (this.layers[layerName]) {
            this.map.removeLayer(this.layers[layerName]);
        }
    }

    toggleLayer(layerName, visible) {
        if (visible) {
            this.showLayer(layerName);
        } else {
            this.hideLayer(layerName);
        }
    }

    // Refresh assets with current filters
    async refreshAssets() {
        const bounds = this.map.getBounds();
        const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;

        const isoSelect = document.getElementById('iso-select');
        const isoRegion = isoSelect.value || null;

        const atTime = window.timeline ? window.timeline.getSelectedDateTime() : null;

        return this.loadAssets({
            bbox,
            iso_region: isoRegion,
            at_time: atTime ? atTime.toISOString() : null,
        });
    }
}
