/**
 * API client for backend communication
 */
class ApiClient {
    constructor(baseUrl = CONFIG.API_BASE) {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const response = await fetch(url, { ...defaultOptions, ...options });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }

        return response.json();
    }

    // Assets
    async getAssets(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.bbox) queryParams.append('bbox', params.bbox);
        if (params.iso_region) queryParams.append('iso_region', params.iso_region);
        if (params.fuel_type) queryParams.append('fuel_type', params.fuel_type);
        if (params.at_time) queryParams.append('at_time', params.at_time);
        if (params.limit) queryParams.append('limit', params.limit);

        const query = queryParams.toString();
        return this.request(`/assets${query ? '?' + query : ''}`);
    }

    async getAssetDetails(assetId) {
        return this.request(`/assets/${assetId}/details`);
    }

    async getISORegions() {
        return this.request('/assets/regions');
    }

    async getFuelTypeDistribution(isoRegion = null) {
        const query = isoRegion ? `?iso_region=${isoRegion}` : '';
        return this.request(`/assets/fuel-types${query}`);
    }

    // Outages
    async getOutages(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.start) queryParams.append('start', params.start);
        if (params.end) queryParams.append('end', params.end);
        if (params.iso_region) queryParams.append('iso_region', params.iso_region);
        if (params.outage_type) queryParams.append('outage_type', params.outage_type);
        if (params.status) queryParams.append('status', params.status);

        const query = queryParams.toString();
        return this.request(`/outages${query ? '?' + query : ''}`);
    }

    async getActiveOutages(atTime = null, isoRegion = null) {
        const queryParams = new URLSearchParams();
        if (atTime) queryParams.append('at_time', atTime);
        if (isoRegion) queryParams.append('iso_region', isoRegion);

        const query = queryParams.toString();
        return this.request(`/outages/active${query ? '?' + query : ''}`);
    }

    async getOutageStats(atTime = null, isoRegion = null) {
        const queryParams = new URLSearchParams();
        if (atTime) queryParams.append('at_time', atTime);
        if (isoRegion) queryParams.append('iso_region', isoRegion);

        const query = queryParams.toString();
        return this.request(`/outages/stats${query ? '?' + query : ''}`);
    }

    async getAssetOutages(assetId, start = null, end = null) {
        const queryParams = new URLSearchParams();
        if (start) queryParams.append('start', start);
        if (end) queryParams.append('end', end);

        const query = queryParams.toString();
        return this.request(`/outages/asset/${assetId}${query ? '?' + query : ''}`);
    }

    // Pricing
    async getPricingNodes(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.bbox) queryParams.append('bbox', params.bbox);
        if (params.iso_region) queryParams.append('iso_region', params.iso_region);
        if (params.node_type) queryParams.append('node_type', params.node_type);

        const query = queryParams.toString();
        return this.request(`/pricing/nodes${query ? '?' + query : ''}`);
    }

    async getLMPHeatmap(timestamp, params = {}) {
        const queryParams = new URLSearchParams();
        queryParams.append('timestamp', timestamp);
        if (params.iso_region) queryParams.append('iso_region', params.iso_region);
        if (params.market_type) queryParams.append('market_type', params.market_type);
        if (params.bbox) queryParams.append('bbox', params.bbox);
        if (params.component) queryParams.append('component', params.component);

        return this.request(`/pricing/heatmap?${queryParams.toString()}`);
    }

    async getNodeTimeseries(nodeId, start, end, marketType = 'DAM') {
        const queryParams = new URLSearchParams();
        queryParams.append('start', start);
        queryParams.append('end', end);
        queryParams.append('market_type', marketType);

        return this.request(`/pricing/node/${nodeId}/timeseries?${queryParams.toString()}`);
    }

    async getAvailableTimestamps(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.iso_region) queryParams.append('iso_region', params.iso_region);
        if (params.market_type) queryParams.append('market_type', params.market_type);
        if (params.start) queryParams.append('start', params.start);
        if (params.end) queryParams.append('end', params.end);
        if (params.limit) queryParams.append('limit', params.limit);

        const query = queryParams.toString();
        return this.request(`/pricing/timestamps${query ? '?' + query : ''}`);
    }

    // Zones
    async getZones(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.iso_region) queryParams.append('iso_region', params.iso_region);
        if (params.zone_type) queryParams.append('zone_type', params.zone_type);

        const query = queryParams.toString();
        return this.request(`/zones${query ? '?' + query : ''}`);
    }

    async getISOBoundaries() {
        return this.request('/zones/iso-boundaries');
    }

    async getLoadZones(isoRegion = null) {
        const query = isoRegion ? `?iso_region=${isoRegion}` : '';
        return this.request(`/zones/load-zones${query}`);
    }

    // Config
    async getMapConfig() {
        return this.request('/config');
    }

    async healthCheck() {
        return this.request('/health');
    }
}

// Global API client instance
const api = new ApiClient();
