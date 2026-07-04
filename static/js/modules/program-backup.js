/**
 * Program backup utilities shared by the Backup Center and auto-recovery flows.
 */
import { api } from './fetch-wrapper.js';

/**
 * Fetch all backups from the API
 * @returns {Promise<Array>} Array of backup objects
 */
export async function fetchBackups() {
    try {
        const data = await api.get('/api/backups', { showErrorToast: false });
        return data.data !== undefined ? data.data : data;
    } catch (error) {
        console.error('Error fetching backups:', error);
        throw error;
    }
}

/**
 * Fetch a single backup with item details
 * @param {number} backupId - Backup ID
 * @returns {Promise<Object>} Backup details with items
 */
export async function fetchBackupDetails(backupId) {
    try {
        const data = await api.get(`/api/backups/${backupId}`, { showErrorToast: false });
        return data.data !== undefined ? data.data : data;
    } catch (error) {
        console.error('Error fetching backup details:', error);
        throw error;
    }
}

/**
 * Create a new backup
 * @param {string} name - Backup name
 * @param {string} note - Optional note
 * @returns {Promise<Object>} Created backup object
 */
export async function createBackup(name, note = null) {
    try {
        const data = await api.post('/api/backups', { name, note }, { showErrorToast: false });
        return data.data !== undefined ? data.data : data;
    } catch (error) {
        console.error('Error creating backup:', error);
        throw error;
    }
}

/**
 * Update backup metadata
 * @param {number} backupId - Backup ID
 * @param {Object} fields - Editable metadata fields
 * @param {string} [fields.name] - New backup name
 * @param {string} [fields.note] - New backup note
 * @returns {Promise<Object>} Updated backup object
 */
export async function updateBackupMetadata(backupId, { name, note }) {
    const payload = {};
    if (name !== undefined) payload.name = name;
    if (note !== undefined) payload.note = note;

    try {
        const data = await api.patch(`/api/backups/${backupId}`, payload, { showErrorToast: false });
        return data.data !== undefined ? data.data : data;
    } catch (error) {
        console.error('Error updating backup metadata:', error);
        throw error;
    }
}

/**
 * Restore a backup
 * @param {number} backupId - ID of the backup to restore
 * @returns {Promise<Object>} Restore result
 */
export async function restoreBackup(backupId) {
    try {
        const data = await api.post(`/api/backups/${backupId}/restore`, {}, { showErrorToast: false });
        return data.data !== undefined ? data.data : data;
    } catch (error) {
        console.error('Error restoring backup:', error);
        throw error;
    }
}

/**
 * Delete a backup
 * @param {number} backupId - ID of the backup to delete
 * @returns {Promise<void>}
 */
export async function deleteBackup(backupId) {
    try {
        await api.delete(`/api/backups/${backupId}`, { showErrorToast: false });
    } catch (error) {
        console.error('Error deleting backup:', error);
        throw error;
    }
}

/**
 * Show a banner referencing the pre-erase file-copy snapshot written to
 * data/auto_backup/ (see utils/auto_backup.py). This is informational only —
 * there is no in-app restore action for this raw file snapshot; recovery is a
 * manual file-copy operation, distinct from the Backup Center's DB-table
 * backups (see restoreBackup() above).
 * @param {Object|null} autoBackup - Snapshot info from the /erase-data response,
 *   e.g. `{ filename: "database_20260704_153012.db" }`. No-op if falsy (the
 *   erase route returns null when no snapshot was taken).
 */
export function showAutoBackupBanner(autoBackup) {
    if (!autoBackup || !autoBackup.filename) return;

    // Remove any existing banner
    const existingBanner = document.getElementById('auto-backup-banner');
    if (existingBanner) existingBanner.remove();

    const banner = document.createElement('div');
    banner.id = 'auto-backup-banner';
    banner.setAttribute('data-testid', 'auto-backup-banner');
    banner.className = 'alert alert-info alert-dismissible fade show d-flex align-items-center justify-content-between';
    banner.innerHTML = `
        <div>
            <i class="fas fa-info-circle me-2"></i>
            <strong>Auto-backup created:</strong> your data was saved to
            <code>data/auto_backup/${escapeHtml(autoBackup.filename)}</code> before erasing.
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    // Insert at top of main content
    const main = document.querySelector('main') || document.querySelector('.container-fluid');
    if (main) {
        main.insertBefore(banner, main.firstChild);
    }
}

/**
 * Escape HTML to prevent XSS
 * @param {string} str - String to escape
 * @returns {string} Escaped string
 */
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
