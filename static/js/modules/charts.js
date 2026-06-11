import { showToast } from './toast.js';

export function createVolumeChart(container, data) {
    try {
        return new Chart(container, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Volume per Muscle Group',
                    data: data.values,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error creating volume chart:', error);
        showToast('Failed to create volume chart', true);
    }
}

export function createProgressChart(container, data) {
    try {
        return new Chart(container, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: 'Progress Over Time',
                    data: data.values,
                    fill: false,
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error creating progress chart:', error);
        showToast('Failed to create progress chart', true);
    }
}
