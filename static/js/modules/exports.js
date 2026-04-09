import { showToast } from './toast.js';
import { api, isHandledApiError, logApiError } from './fetch-wrapper.js';

/**
 * Check if the workout plan table has any exercises
 * @returns {boolean} True if table has exercises, false if empty
 */
function hasExercisesInPlan() {
    const tableBody = document.getElementById('workout_plan_table_body');
    if (!tableBody) return false;
    
    const rows = tableBody.querySelectorAll('tr');
    // Check if any rows exist (excluding empty state row)
    for (const row of rows) {
        // Skip rows that are empty state messages
        if (row.querySelector('td[colspan]')) continue;
        if (row.classList.contains('empty-state')) continue;
        // If we find a real exercise row, return true
        if (row.querySelector('td')) return true;
    }
    return false;
}

export async function exportToExcel() {
    try {
        console.log('=== Starting export to Excel ===');
        
        // Check for empty plan before export
        if (!hasExercisesInPlan()) {
            showToast('warning', 'No exercises to export. Add exercises to your workout plan first.');
            return;
        }
        
        // Get the current view mode from localStorage (matches filter-view-mode.js storage key)
        const viewMode = localStorage.getItem('hypertrophy_filter_view_mode') || 'simple';
        console.log('Current view mode:', viewMode);
        
        // Build URL with view_mode parameter
        const exportUrl = `/export_to_excel?view_mode=${encodeURIComponent(viewMode)}`;
        console.log('Making fetch request to:', exportUrl);
        
        const response = await fetch(exportUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        });

        console.log('=== Response received ===');
        console.log('Status:', response.status, response.statusText);
        console.log('Response ok:', response.ok);
        console.log('Response headers:', [...response.headers.entries()]);

        if (!response.ok) {
            const error = await response.json();
            console.error('Error response:', error);
            throw new Error(error.message || error.error?.message || 'Failed to export to Excel');
        }

        // Get filename from Content-Disposition header
        const contentDisposition = response.headers.get('Content-Disposition');
        console.log('Content-Disposition:', contentDisposition);
        const filename = contentDisposition
            ? contentDisposition.split('filename=')[1].replace(/"/g, '')
            : 'workout_plan.xlsx';

        console.log('Creating blob from response...');
        // Create blob from response
        const blob = await response.blob();
        console.log('Blob created, size:', blob.size, 'bytes');
        const url = window.URL.createObjectURL(blob);
        
        // Create temporary link and trigger download
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showToast('success', 'Successfully exported to Excel');
    } catch (error) {
        console.error('Error exporting to Excel:', error);
        showToast('error', 'Failed to export to Excel');
    }
}

export async function exportToWorkoutLog() {
    try {
        // Check for empty plan before export
        if (!hasExercisesInPlan()) {
            showToast('warning', 'No exercises to export. Add exercises to your workout plan first.');
            return;
        }

        await api.post('/export_to_workout_log', {}, { showLoading: false, showErrorToast: false });

        showToast('success', 'Successfully exported to workout log');
        
        // Redirect to workout log page after short delay
        setTimeout(() => {
            window.location.href = '/workout_log';
        }, 1500);
    } catch (error) {
        logApiError('Error exporting to workout log:', error);
        showToast(isHandledApiError(error) ? 'warning' : 'error', error.message || 'Failed to export to workout log');
    }
}

export async function exportSummary(type = 'weekly') {
    try {
        const response = await fetch(`/export_${type}_summary`, {
            method: 'GET'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || `Failed to export ${type} summary`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `${type}_summary.xlsx`;
        document.body.appendChild(a);
        a.click();
        
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showToast('success', `Successfully exported ${type} summary`);
    } catch (error) {
        console.error(`Error exporting ${type} summary:`, error);
        showToast('error', `Failed to export ${type} summary`);
    }
} 
