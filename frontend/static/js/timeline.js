/**
 * Timeline/time slider management
 */
class Timeline {
    constructor(layerManager) {
        this.layerManager = layerManager;
        this.isPlaying = false;
        this.playInterval = null;
        this.playSpeed = 1000; // ms between steps

        this.slider = document.getElementById('time-slider');
        this.datePicker = document.getElementById('date-picker');
        this.timeDisplay = document.getElementById('selected-time');
        this.playBtn = document.getElementById('play-btn');
        this.stepBackBtn = document.getElementById('step-back-btn');
        this.stepForwardBtn = document.getElementById('step-forward-btn');

        this.init();
    }

    init() {
        // Set default date to today
        const today = new Date();
        this.datePicker.value = today.toISOString().split('T')[0];

        // Event listeners
        this.slider.addEventListener('input', () => this.onSliderChange());
        this.slider.addEventListener('change', () => this.onSliderChangeEnd());
        this.datePicker.addEventListener('change', () => this.onDateChange());
        this.playBtn.addEventListener('click', () => this.togglePlay());
        this.stepBackBtn.addEventListener('click', () => this.stepBack());
        this.stepForwardBtn.addEventListener('click', () => this.stepForward());

        // Initialize display
        this.updateTimeDisplay();
    }

    onSliderChange() {
        this.updateTimeDisplay();
    }

    async onSliderChangeEnd() {
        await this.refreshData();
    }

    async onDateChange() {
        await this.refreshData();
    }

    updateTimeDisplay() {
        const hour = parseInt(this.slider.value);
        const timeStr = `${hour.toString().padStart(2, '0')}:00`;
        this.timeDisplay.textContent = timeStr;
    }

    getSelectedDateTime() {
        const dateStr = this.datePicker.value;
        const hour = parseInt(this.slider.value);

        if (!dateStr) return new Date();

        const date = new Date(dateStr);
        date.setHours(hour, 0, 0, 0);
        return date;
    }

    async refreshData() {
        const dateTime = this.getSelectedDateTime();

        // Refresh assets with the selected time
        await this.layerManager.refreshAssets();

        // If LMP heatmap is visible, refresh it too
        const lmpCheckbox = document.getElementById('layer-lmp-heatmap');
        if (lmpCheckbox && lmpCheckbox.checked) {
            const component = document.getElementById('lmp-component').value;
            await this.layerManager.loadLMPHeatmap(dateTime.toISOString(), {
                component,
            });
        }
    }

    togglePlay() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }

    play() {
        this.isPlaying = true;
        this.playBtn.classList.add('playing');
        this.playBtn.innerHTML = '&#10074;&#10074;'; // Pause icon

        this.playInterval = setInterval(() => {
            this.stepForward();

            // Loop back to start if at end
            if (parseInt(this.slider.value) >= parseInt(this.slider.max)) {
                this.slider.value = this.slider.min;
            }
        }, this.playSpeed);
    }

    pause() {
        this.isPlaying = false;
        this.playBtn.classList.remove('playing');
        this.playBtn.innerHTML = '&#9658;'; // Play icon

        if (this.playInterval) {
            clearInterval(this.playInterval);
            this.playInterval = null;
        }
    }

    stepBack() {
        const currentValue = parseInt(this.slider.value);
        if (currentValue > parseInt(this.slider.min)) {
            this.slider.value = currentValue - 1;
            this.updateTimeDisplay();
            this.refreshData();
        }
    }

    stepForward() {
        const currentValue = parseInt(this.slider.value);
        if (currentValue < parseInt(this.slider.max)) {
            this.slider.value = currentValue + 1;
            this.updateTimeDisplay();
            this.refreshData();
        }
    }

    setSpeed(speedMs) {
        this.playSpeed = speedMs;
        if (this.isPlaying) {
            this.pause();
            this.play();
        }
    }

    destroy() {
        this.pause();
    }
}

// Global instance
window.timeline = null;
