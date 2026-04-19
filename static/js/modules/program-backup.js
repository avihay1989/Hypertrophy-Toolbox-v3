/**
 * Program Backup / Program Library functionality.
 * 
 * Provides UI interactions for saving, loading, restoring, and deleting program backups.
 */
import { showToast } from './toast.js';
import { api } from './fetch-wrapper.js';

/**
 * Format a date string for display
 * @param {string} dateStr - ISO date string
 * @returns {string} Formatted date string
 */
function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleString('en-GB', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateStr;
    }
}

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
 * Populate the backup list in the modal
 */
export async function populateBackupList() {
    const listContainer = document.getElementById('backup-list');
    if (!listContainer) return;
    
    listContainer.innerHTML = '<div class="text-center py-3"><i class="fas fa-spinner fa-spin"></i> Loading backups...</div>';
    
    try {
        const backups = await fetchBackups();
        
        if (!backups || backups.length === 0) {
            listContainer.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="fas fa-archive fa-2x mb-2"></i>
                    <p class="mb-0">No saved programs yet.</p>
                    <small>Create your first backup using "Save Program".</small>
                </div>
            `;
            return;
        }
        
        listContainer.innerHTML = '';
        
        backups.forEach(backup => {
            const backupItem = document.createElement('div');
            backupItem.className = 'backup-list-item d-flex justify-content-between align-items-center p-3 border-bottom';
            backupItem.dataset.backupId = backup.id;
            
            const typeIcon = backup.backup_type === 'auto' 
                ? '<i class="fas fa-clock text-info me-1" title="Auto-backup"></i>' 
                : '<i class="fas fa-save text-primary me-1" title="Manual backup"></i>';
            
            backupItem.innerHTML = `
                <div class="backup-info flex-grow-1">
                    <div class="backup-name fw-bold">
                        ${typeIcon}
                        ${escapeHtml(backup.name)}
                    </div>
                    <div class="backup-meta small text-muted">
                        <span class="me-3"><i class="fas fa-dumbbell me-1"></i>${backup.item_count} exercises</span>
                        <span><i class="fas fa-calendar me-1"></i>${formatDate(backup.created_at)}</span>
                    </div>
                    ${backup.note ? `<div class="backup-note small fst-italic mt-1">${escapeHtml(backup.note)}</div>` : ''}
                </div>
                <div class="backup-actions btn-group">
                    <button class="btn btn-sm btn-success backup-restore-btn" 
                            data-backup-id="${backup.id}" 
                            data-backup-name="${escapeHtml(backup.name)}"
                            title="Restore this backup">
                        <i class="fas fa-undo"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger backup-delete-btn" 
                            data-backup-id="${backup.id}"
                            data-backup-name="${escapeHtml(backup.name)}"
                            title="Delete this backup">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            
            listContainer.appendChild(backupItem);
        });
        
        // Attach event listeners to buttons
        attachBackupListeners();
        
    } catch (error) {
        listContainer.innerHTML = `
            <div class="alert alert-danger m-3">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load backups: ${escapeHtml(error.message)}
            </div>
        `;
    }
}

// Store pending action data for confirmation modals
let pendingRestoreData = null;
let pendingDeleteData = null;
let programBackupInitialized = false;

/**
 * Attach event listeners to backup list buttons
 */
function attachBackupListeners() {
    // Restore buttons - show confirmation modal
    document.querySelectorAll('.backup-restore-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const backupId = btn.dataset.backupId;
            const backupName = btn.dataset.backupName;
            
            // Store data for confirmation
            pendingRestoreData = { backupId, backupName, button: btn };
            
            // Update modal content
            document.getElementById('restoreBackupName').textContent = backupName;
            
            // Show confirmation modal
            const confirmModal = new bootstrap.Modal(document.getElementById('confirmRestoreModal'));
            confirmModal.show();
        });
    });
    
    // Delete buttons - show confirmation modal
    document.querySelectorAll('.backup-delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const backupId = btn.dataset.backupId;
            const backupName = btn.dataset.backupName;
            
            // Store data for confirmation
            pendingDeleteData = { backupId, backupName, button: btn };
            
            // Update modal content
            document.getElementById('deleteBackupName').textContent = backupName;
            
            // Show confirmation modal
            const confirmModal = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));
            confirmModal.show();
        });
    });
}

/**
 * Handle save backup form submission
 */
export async function handleSaveBackup() {
    const nameInput = document.getElementById('backup-name');
    const noteInput = document.getElementById('backup-note');
    const saveBtn = document.getElementById('saveBackupSubmit');
    
    if (!nameInput || !saveBtn) return;
    
    const name = nameInput.value.trim();
    const note = noteInput ? noteInput.value.trim() : null;
    
    if (!name) {
        showToast('warning', 'Please enter a name for the backup');
        nameInput.focus();
        return;
    }
    
    const originalText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
    
    try {
        const backup = await createBackup(name, note || null);
        
        showToast('success', `Backup "${backup.name}" created with ${backup.item_count} exercises`);
        
        // Clear form
        nameInput.value = '';
        if (noteInput) noteInput.value = '';
        
        // Close save modal
        const saveModal = bootstrap.Modal.getInstance(document.getElementById('saveBackupModal'));
        if (saveModal) saveModal.hide();
        
        // Refresh backup list if library modal is open
        const libraryModal = document.getElementById('programLibraryModal');
        if (libraryModal && libraryModal.classList.contains('show')) {
            populateBackupList();
        }
        
    } catch (error) {
        showToast('error', `Failed to create backup: ${error.message}`);
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalText;
    }
}

/**
 * Show auto-backup restore banner after erase
 * @param {Object} autoBackup - Auto-backup info from erase response
 */
export function showAutoBackupBanner(autoBackup) {
    if (!autoBackup || !autoBackup.id) return;
    
    // Remove any existing banner
    const existingBanner = document.getElementById('auto-backup-banner');
    if (existingBanner) existingBanner.remove();
    
    const banner = document.createElement('div');
    banner.id = 'auto-backup-banner';
    banner.className = 'alert alert-info alert-dismissible fade show d-flex align-items-center justify-content-between';
    banner.innerHTML = `
        <div>
            <i class="fas fa-info-circle me-2"></i>
            <strong>Auto-backup created:</strong> "${escapeHtml(autoBackup.name)}" 
            with ${autoBackup.item_count} exercises
        </div>
        <div class="d-flex gap-2 align-items-center">
            <button type="button" class="btn btn-sm btn-primary" id="restore-auto-backup-btn">
                <i class="fas fa-undo me-1"></i>Restore Now
            </button>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    // Insert at top of main content
    const main = document.querySelector('main') || document.querySelector('.container-fluid');
    if (main) {
        main.insertBefore(banner, main.firstChild);
        
        // Attach restore handler
        document.getElementById('restore-auto-backup-btn').addEventListener('click', async () => {
            const btn = document.getElementById('restore-auto-backup-btn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Restoring...';
            
            try {
                const result = await restoreBackup(autoBackup.id);
                showToast('success', `Restored ${result.restored_count} exercises`);
                banner.remove();
                
                // Refresh workout plan
                if (typeof window.fetchWorkoutPlan === 'function') {
                    window.fetchWorkoutPlan();
                } else {
                    window.location.reload();
                }
            } catch (error) {
                showToast('error', `Failed to restore: ${error.message}`);
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-undo me-1"></i>Restore Now';
            }
        });
    }
}

/**
 * Initialize program backup UI handlers
 */
export function initializeProgramBackup() {
    const libraryModalEl = document.getElementById('programLibraryModal');
    if (!libraryModalEl || programBackupInitialized) {
        return;
    }

    programBackupInitialized = true;

    // Save backup button handler
    const saveBtn = document.getElementById('saveBackupSubmit');
    if (saveBtn) {
        saveBtn.addEventListener('click', handleSaveBackup);
    }
    
    // Load backups when library modal is shown (Bootstrap event)
    libraryModalEl.addEventListener('show.bs.modal', () => {
        populateBackupList();
    });
    
    // Handle "Save Current Program" button from within library modal
    const openSaveFromLibrary = document.getElementById('openSaveFromLibrary');
    if (openSaveFromLibrary) {
        openSaveFromLibrary.addEventListener('click', () => {
            // Close library modal first using Bootstrap
            const libraryModal = bootstrap.Modal.getInstance(libraryModalEl);
            if (libraryModal) {
                libraryModal.hide();
            }
            // Wait for close animation, then open save modal
            setTimeout(() => {
                const saveModalEl = document.getElementById('saveBackupModal');
                const saveModal = new bootstrap.Modal(saveModalEl);
                saveModal.show();
            }, 300);
        });
    }
    
    // Allow Enter key to submit save form
    const nameInput = document.getElementById('backup-name');
    if (nameInput) {
        nameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSaveBackup();
            }
        });
    }
    
    // Confirm Restore button handler
    const confirmRestoreBtn = document.getElementById('confirmRestoreBtn');
    if (confirmRestoreBtn) {
        confirmRestoreBtn.addEventListener('click', async () => {
            if (!pendingRestoreData) return;
            
            const { backupId, backupName, button } = pendingRestoreData;
            
            // Close confirmation modal
            const confirmModal = bootstrap.Modal.getInstance(document.getElementById('confirmRestoreModal'));
            if (confirmModal) confirmModal.hide();
            
            // Disable the original button and show spinner
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            }
            
            try {
                const result = await restoreBackup(backupId);
                
                let message = `Restored ${result.restored_count} exercises from "${result.backup_name}"`;
                if (result.skipped && result.skipped.length > 0) {
                    message += ` (${result.skipped.length} skipped)`;
                    console.warn('Skipped exercises:', result.skipped);
                }
                
                showToast('success', message);
                
                // Close library modal
                const libraryModal = bootstrap.Modal.getInstance(document.getElementById('programLibraryModal'));
                if (libraryModal) libraryModal.hide();
                
                // Refresh workout plan if function exists
                if (typeof window.fetchWorkoutPlan === 'function') {
                    window.fetchWorkoutPlan();
                } else {
                    // Fallback: reload page
                    window.location.reload();
                }
                
            } catch (error) {
                showToast('error', `Failed to restore backup: ${error.message}`);
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-undo"></i>';
                }
            }
            
            pendingRestoreData = null;
        });
    }
    
    // Confirm Delete button handler
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', async () => {
            if (!pendingDeleteData) return;
            
            const { backupId, backupName, button } = pendingDeleteData;
            
            // Close confirmation modal
            const confirmModal = bootstrap.Modal.getInstance(document.getElementById('confirmDeleteModal'));
            if (confirmModal) confirmModal.hide();
            
            // Disable the original button and show spinner
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            }
            
            try {
                await deleteBackup(backupId);
                showToast('success', 'Backup deleted successfully');
                
                // Remove the item from the list
                if (button) {
                    const listItem = button.closest('.backup-list-item');
                    if (listItem) {
                        listItem.remove();
                    }
                }
                
                // Check if list is now empty
                const listContainer = document.getElementById('backup-list');
                if (listContainer && listContainer.children.length === 0) {
                    populateBackupList();
                }
                
            } catch (error) {
                showToast('error', `Failed to delete backup: ${error.message}`);
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-trash"></i>';
                }
            }
            
            pendingDeleteData = null;
        });
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
