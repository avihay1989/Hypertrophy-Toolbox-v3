import { showToast } from './toast.js';
import { api } from './fetch-wrapper.js';

// Check if the page already has its own updateWeeklySummary function defined
// If so, skip the module's version to avoid conflicts
function pageHasOwnUpdater() {
    return typeof window.updateWeeklySummary === 'function' ||
           typeof window.updateSessionSummary === 'function';
}

export async function fetchWeeklySummary(method = 'Total') {
    // Skip if page has its own update handler (new effective sets UI)
    if (pageHasOwnUpdater()) {
        return;
    }
    
    try {
        const data = await api.get(`/weekly_summary?method=${method}`, { showLoading: false, showErrorToast: false });
        
        if (!data) {
            throw new Error('No data received from server');
        }
        
        updateSummaryUI(data.data || data);
    } catch (error) {
        console.error('Error fetching weekly summary:', error);
        showToast('Failed to fetch weekly summary', true);
    }
}

export async function fetchSessionSummary(method = 'Total') {
    // Skip if page has its own update handler (new effective sets UI)
    if (pageHasOwnUpdater()) {
        return;
    }
    
    try {
        const data = await api.get(`/session_summary?method=${method}`, { showLoading: false, showErrorToast: false });
        
        if (!data) {
            throw new Error('No data received from server');
        }
        
        updateSummaryUI(data.data || data);
    } catch (error) {
        console.error('Error fetching session summary:', error);
        showToast('Failed to fetch session summary', true);
    }
}

function updateSummaryUI(data) {
    const summaryData = data.session_summary || data.weekly_summary || [];
    
    // Update summary tables
    updateSummaryTable(summaryData);
    
    // Update category breakdown
    updateCategoryTable(data.categories || []);
    
    // Update isolated muscles stats
    updateIsolatedMusclesTable(data.isolated_muscles || []);
}

function updateSummaryTable(summaryData) {
    const tbody = document.querySelector('#session-summary-table, #weekly-summary-table');
    if (!tbody || !summaryData) return;

    tbody.innerHTML = summaryData.map(item => `
        <tr>
            ${item.routine ? `<td>${item.routine}</td>` : ''}
            <td>${item.muscle_group || 'N/A'}</td>
            <td>${item.total_sets || 0}</td>
            <td>${item.total_reps || 0}</td>
            <td>${item.total_volume || 0}</td>
            <td>
                <div class="volume-classification">
                    <span class="volume-badge ${getVolumeClass(item.total_sets)}">
                        ${getVolumeLabel(item.total_sets)}
                    </span>
                </div>
            </td>
        </tr>
    `).join('');
}

function updateCategoryTable(categories) {
    const tbody = document.querySelector('#categories-table tbody');
    if (!tbody || !categories) return;

    tbody.innerHTML = categories.map(cat => `
        <tr>
            <td>${cat.category || 'N/A'}</td>
            <td>${cat.subcategory || 'N/A'}</td>
            <td>${cat.total_exercises || 0}</td>
        </tr>
    `).join('');
}

function updateIsolatedMusclesTable(stats) {
    const tbody = document.querySelector('#isolated-muscles-table tbody');
    if (!tbody || !stats) return;

    tbody.innerHTML = stats.map(stat => `
        <tr>
            <td>${stat.isolated_muscle || 'N/A'}</td>
            <td>${stat.exercise_count || 0}</td>
            <td>${stat.total_sets || 0}</td>
            <td>${stat.total_reps || 0}</td>
            <td>${stat.total_volume || 0}</td>
            <td>
                <div class="volume-classification">
                    <span class="volume-badge ${getVolumeClass(stat.total_sets)}">
                        ${getVolumeLabel(stat.total_sets)}
                    </span>
                </div>
            </td>
        </tr>
    `).join('');
}

function getVolumeClass(sets) {
    if (sets >= 30) return 'ultra-volume';
    if (sets >= 20) return 'high-volume';
    if (sets >= 10) return 'medium-volume';
    return 'low-volume';
}

function getVolumeLabel(sets) {
    if (sets >= 30) return 'Excessive Volume';
    if (sets >= 20) return 'High Volume';
    if (sets >= 10) return 'Medium Volume';
    return 'Low Volume';
}
