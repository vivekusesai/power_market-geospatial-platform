/**
 * Details panel management
 */
class DetailsPanel {
    constructor() {
        this.placeholder = document.getElementById('details-placeholder');
        this.content = document.getElementById('details-content');
        this.assetSection = document.getElementById('asset-details');
        this.zoneSection = document.getElementById('zone-details');
        this.pricingChart = null;

        this.initChart();
    }

    initChart() {
        const ctx = document.getElementById('pricing-chart');
        if (!ctx) return;

        this.pricingChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Total LMP',
                        data: [],
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        fill: true,
                        tension: 0.3,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false,
                    },
                },
                scales: {
                    x: {
                        display: true,
                        ticks: {
                            maxTicksLimit: 6,
                            color: '#a0a0a0',
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)',
                        },
                    },
                    y: {
                        display: true,
                        ticks: {
                            color: '#a0a0a0',
                            callback: (value) => '$' + value,
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)',
                        },
                    },
                },
            },
        });
    }

    showAssetDetails(props) {
        // Hide placeholder and zone section
        this.placeholder.classList.add('hidden');
        this.zoneSection.classList.add('hidden');
        this.content.classList.remove('hidden');
        this.assetSection.classList.remove('hidden');

        // Update asset info
        document.getElementById('asset-name').textContent = props.asset_name;
        document.getElementById('detail-asset-id').textContent = props.asset_id;
        document.getElementById('detail-fuel-type').textContent =
            FUEL_LABELS[props.fuel_type] || props.fuel_type;
        document.getElementById('detail-capacity').textContent =
            `${props.capacity_mw.toFixed(1)} MW`;
        document.getElementById('detail-owner').textContent = props.owner || 'N/A';
        document.getElementById('detail-iso').textContent = props.iso_region;
        document.getElementById('detail-zone').textContent = props.zone || 'N/A';

        // Update outage info
        const outageInfo = document.getElementById('outage-info');
        if (props.outage_type) {
            outageInfo.classList.remove('hidden');
            document.getElementById('detail-outage-type').textContent =
                props.outage_type.charAt(0).toUpperCase() + props.outage_type.slice(1);
            document.getElementById('detail-outage-status').textContent =
                props.outage_status || 'Active';
            document.getElementById('detail-outage-start').textContent =
                props.outage_start ? new Date(props.outage_start).toLocaleString() : 'N/A';
            document.getElementById('detail-outage-end').textContent =
                props.outage_end ? new Date(props.outage_end).toLocaleString() : 'Ongoing';
            document.getElementById('detail-cause-code').textContent =
                props.cause_code || 'N/A';
        } else {
            outageInfo.classList.add('hidden');
        }

        // Load pricing data
        this.loadAssetPricing(props.asset_id);
    }

    showZoneDetails(props) {
        // Hide placeholder and asset section
        this.placeholder.classList.add('hidden');
        this.assetSection.classList.add('hidden');
        this.content.classList.remove('hidden');
        this.zoneSection.classList.remove('hidden');

        // Update zone info
        document.getElementById('zone-name').textContent = props.zone_name;
        document.getElementById('detail-zone-id').textContent = props.zone_id;
        document.getElementById('detail-zone-type').textContent =
            props.zone_type.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase());
        document.getElementById('detail-zone-iso').textContent = props.iso_region;
    }

    async loadAssetPricing(assetId) {
        if (!this.pricingChart) return;

        try {
            // Get last 24 hours of pricing data
            const end = new Date();
            const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);

            const data = await api.getNodeTimeseries(
                assetId,
                start.toISOString(),
                end.toISOString()
            );

            if (data && data.data && data.data.length > 0) {
                this.updatePricingChart(data.data);
            } else {
                this.clearPricingChart();
            }
        } catch (error) {
            console.log('No pricing data available for this asset');
            this.clearPricingChart();
        }
    }

    updatePricingChart(data) {
        if (!this.pricingChart) return;

        const labels = data.map((d) => {
            const date = new Date(d.timestamp);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        });

        const values = data.map((d) => d.lmp_total);

        this.pricingChart.data.labels = labels;
        this.pricingChart.data.datasets[0].data = values;
        this.pricingChart.update();
    }

    clearPricingChart() {
        if (!this.pricingChart) return;

        this.pricingChart.data.labels = [];
        this.pricingChart.data.datasets[0].data = [];
        this.pricingChart.update();
    }

    reset() {
        this.placeholder.classList.remove('hidden');
        this.content.classList.add('hidden');
        this.assetSection.classList.add('hidden');
        this.zoneSection.classList.add('hidden');
        this.clearPricingChart();
    }
}

// Global instance
window.detailsPanel = null;
