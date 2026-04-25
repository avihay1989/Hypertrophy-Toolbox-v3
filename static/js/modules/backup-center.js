import { showToast } from './toast.js';
import {
    fetchBackups,
    fetchBackupDetails,
    createBackup,
    restoreBackup,
    deleteBackup,
    updateBackupMetadata
} from './program-backup.js';
import { notifyVolumeAffectingPlanChange } from './workout-plan-events.js';

let backupCenterInitialized = false;
let backupsCache = [];
let selectedBackupId = null;
let selectedBackupDetails = null;
let pendingAction = null;
let detailRequestSequence = 0;
let inlineEditField = null;
let emptyWarningShown = false;

const SORT_PREF_KEY = 'backupCenter.sortPreference';

function getNavigationIntent() {
    const intent = new URLSearchParams(window.location.search).get('intent');
    return intent === 'save' || intent === 'browse' ? intent : null;
}

function updateActiveProgramCount(count) {
    const normalizedCount = Number.isFinite(Number(count)) ? Number(count) : 0;
    const activeCountEl = document.getElementById('backup-active-count');
    const activePillEl = document.querySelector('.backup-active-pill');

    if (activeCountEl) {
        activeCountEl.textContent = String(normalizedCount);
    }

    if (activePillEl) {
        activePillEl.textContent = `${normalizedCount} active exercises`;
    }
}

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
    } catch (error) {
        return dateStr;
    }
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function getPageRoot() {
    return document.querySelector('[data-page="backup-center"]');
}

function getVisibleBackups() {
    const root = getPageRoot();
    if (!root) return [];

    const activeFilter = root.querySelector('.backup-filter-btn.active')?.dataset.filter || 'all';
    const searchValue = root.querySelector('#backup-search')?.value.trim().toLowerCase() || '';
    const sortValue = root.querySelector('#backup-sort')?.value || 'newest';

    const visibleBackups = backupsCache.filter((backup) => {
        const matchesFilter = activeFilter === 'all' || backup.backup_type === activeFilter;
        const haystack = `${backup.name || ''} ${backup.note || ''}`.toLowerCase();
        const matchesSearch = !searchValue || haystack.includes(searchValue);
        return matchesFilter && matchesSearch;
    });

    const compareNames = (left, right) => (left.name || '').localeCompare(right.name || '', undefined, { sensitivity: 'base' });

    switch (sortValue) {
        case 'oldest':
            return [...visibleBackups].sort((left, right) => new Date(left.created_at) - new Date(right.created_at));
        case 'name-asc':
            return [...visibleBackups].sort(compareNames);
        case 'name-desc':
            return [...visibleBackups].sort((left, right) => compareNames(right, left));
        case 'newest':
        default:
            return [...visibleBackups].sort((left, right) => new Date(right.created_at) - new Date(left.created_at));
    }
}

function updateSummaryCards(backups) {
    const totalCount = backups.length;
    const manualBackups = backups.filter((backup) => backup.backup_type !== 'auto');
    const autoBackups = backups.filter((backup) => backup.backup_type === 'auto');
    const latestManual = manualBackups[0];
    const latestAuto = autoBackups[0];

    const totalCountEl = document.getElementById('backup-total-count');
    const manualCountEl = document.getElementById('backup-manual-count');
    const autoCountEl = document.getElementById('backup-auto-count');
    const latestManualEl = document.getElementById('backup-latest-manual');
    const latestAutoEl = document.getElementById('backup-latest-auto');

    if (totalCountEl) totalCountEl.textContent = String(totalCount);
    if (manualCountEl) manualCountEl.textContent = String(manualBackups.length);
    if (autoCountEl) autoCountEl.textContent = String(autoBackups.length);

    if (latestManualEl) {
        latestManualEl.textContent = latestManual ? `Latest: ${latestManual.name}` : 'Latest: none yet';
    }

    if (latestAutoEl) {
        latestAutoEl.textContent = latestAuto ? `Latest: ${latestAuto.name}` : 'Latest: none yet';
    }
}

function applyNavigationIntent() {
    const intent = getNavigationIntent();
    const savePanel = document.getElementById('backup-save-panel');
    const libraryPanel = document.getElementById('backup-library-panel');
    const saveInput = document.getElementById('backup-center-name');
    const searchInput = document.getElementById('backup-search');

    if (savePanel) savePanel.classList.toggle('is-targeted', intent === 'save');
    if (libraryPanel) libraryPanel.classList.toggle('is-targeted', intent === 'browse');

    if (intent === 'save' && savePanel && saveInput instanceof HTMLElement) {
        savePanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        window.setTimeout(() => saveInput.focus(), 180);
        return;
    }

    if (intent === 'browse' && libraryPanel && searchInput instanceof HTMLElement) {
        libraryPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        window.setTimeout(() => searchInput.focus(), 180);
    }
}

function clearPendingAction() {
    pendingAction = null;

    const confirmWrap = document.getElementById('backup-action-confirm');
    const confirmBtn = document.getElementById('backup-action-confirm-btn');
    const saveFirstBtn = document.getElementById('backup-restore-save-first');
    const titleEl = document.getElementById('backup-action-title');
    const textEl = document.getElementById('backup-action-text');

    if (confirmWrap) confirmWrap.hidden = true;
    if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.className = 'btn btn-primary btn-calm-primary';
        confirmBtn.innerHTML = 'Confirm';
    }
    if (saveFirstBtn) {
        saveFirstBtn.hidden = true;
        saveFirstBtn.disabled = false;
        saveFirstBtn.innerHTML = '<i class="fas fa-shield-alt" aria-hidden="true"></i> Save current plan first';
    }
    if (titleEl) titleEl.textContent = 'Confirm action';
    if (textEl) textEl.textContent = '';
}

function clearRestoreResultPanel() {
    const container = document.getElementById('backup-restore-result');
    const titleEl = document.getElementById('backup-restore-result-title');
    const listEl = document.getElementById('backup-restore-result-list');

    if (container) {
        container.hidden = true;
        container.classList.remove('is-warning');
    }
    if (titleEl) titleEl.textContent = '';
    if (listEl) listEl.innerHTML = '';
}

function clearEmptySaveWarning() {
    const warningEl = document.getElementById('backup-save-empty-warning');
    if (warningEl) warningEl.hidden = true;
    emptyWarningShown = false;
}

function clearInlineEditState() {
    inlineEditField = null;

    const nameEditor = document.getElementById('backup-detail-name-editor');
    const noteEditor = document.getElementById('backup-detail-note-editor');
    const nameButton = document.getElementById('backup-detail-edit-name');
    const noteButton = document.getElementById('backup-detail-edit-note');

    if (nameEditor) {
        nameEditor.hidden = true;
        nameEditor.innerHTML = '';
    }
    if (noteEditor) {
        noteEditor.hidden = true;
        noteEditor.innerHTML = '';
    }
    if (nameButton) nameButton.hidden = false;
    if (noteButton) noteButton.hidden = false;
}

function setDetailActionDisabled(disabled) {
    const controls = [
        document.getElementById('backup-detail-restore'),
        document.getElementById('backup-detail-delete'),
        document.getElementById('backup-detail-edit-name'),
        document.getElementById('backup-detail-edit-note'),
        document.getElementById('backup-action-cancel'),
        document.getElementById('backup-action-confirm-btn'),
        document.getElementById('backup-restore-save-first'),
    ];

    controls.forEach((control) => {
        if (control instanceof HTMLButtonElement) {
            control.disabled = disabled;
        }
    });

    const listContainer = document.getElementById('backup-center-list');
    if (listContainer instanceof HTMLElement) {
        listContainer.style.pointerEvents = disabled ? 'none' : '';
    }
}

function getInlineEditConfig(field) {
    if (field === 'name') {
        return {
            editorId: 'backup-detail-name-editor',
            buttonId: 'backup-detail-edit-name',
            inputId: 'backup-detail-name-input',
            saveId: 'backup-detail-name-save',
            cancelId: 'backup-detail-name-cancel',
            label: 'backup name',
            maxlength: 100,
            multiline: false,
            value: selectedBackupDetails?.name || '',
        };
    }

    return {
        editorId: 'backup-detail-note-editor',
        buttonId: 'backup-detail-edit-note',
        inputId: 'backup-detail-note-input',
        saveId: 'backup-detail-note-save',
        cancelId: 'backup-detail-note-cancel',
        label: 'backup note',
        maxlength: 500,
        multiline: true,
        value: selectedBackupDetails?.note || '',
    };
}

function renderInlineEditor(field) {
    const config = getInlineEditConfig(field);
    const editor = document.getElementById(config.editorId);
    const button = document.getElementById(config.buttonId);
    if (!editor || !button) return;

    inlineEditField = field;
    button.hidden = true;
    editor.hidden = false;
    editor.innerHTML = config.multiline
        ? `
            <textarea id="${config.inputId}" class="form-control input-calm-inset" rows="4" maxlength="${config.maxlength}">${escapeHtml(config.value)}</textarea>
            <div class="backup-detail-inline-actions">
                <button type="button" id="${config.saveId}" class="btn btn-sm btn-primary btn-calm-primary">
                    <i class="fas fa-check" aria-hidden="true"></i> Save
                </button>
                <button type="button" id="${config.cancelId}" class="btn btn-sm btn-calm-ghost">
                    <i class="fas fa-times" aria-hidden="true"></i> Cancel
                </button>
            </div>
        `
        : `
            <input id="${config.inputId}" class="form-control input-calm-inset" type="text" maxlength="${config.maxlength}" value="${escapeHtml(config.value)}">
            <div class="backup-detail-inline-actions">
                <button type="button" id="${config.saveId}" class="btn btn-sm btn-primary btn-calm-primary">
                    <i class="fas fa-check" aria-hidden="true"></i> Save
                </button>
                <button type="button" id="${config.cancelId}" class="btn btn-sm btn-calm-ghost">
                    <i class="fas fa-times" aria-hidden="true"></i> Cancel
                </button>
            </div>
        `;

    const input = document.getElementById(config.inputId);
    const saveBtn = document.getElementById(config.saveId);
    const cancelBtn = document.getElementById(config.cancelId);

    if (input instanceof HTMLElement) {
        window.setTimeout(() => input.focus(), 0);
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            const fieldInput = document.getElementById(config.inputId);
            const nextValue = fieldInput instanceof HTMLInputElement || fieldInput instanceof HTMLTextAreaElement
                ? fieldInput.value
                : '';
            commitBackupEdit(field, nextValue);
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            clearInlineEditState();
        });
    }

    if (input) {
        input.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                clearInlineEditState();
            }

            if (!config.multiline && event.key === 'Enter') {
                event.preventDefault();
                commitBackupEdit(field, input.value);
            }
        });
    }
}

async function commitBackupEdit(field, nextValue) {
    if (!selectedBackupDetails || !inlineEditField) return;

    const backupId = selectedBackupDetails.id;
    const currentBackupSnapshot = { ...selectedBackupDetails };
    const cacheIndex = backupsCache.findIndex((backup) => Number(backup.id) === Number(backupId));
    const cacheSnapshot = cacheIndex >= 0 ? { ...backupsCache[cacheIndex] } : null;
    const normalizedValue = field === 'name' ? nextValue.trim() : nextValue.trim();

    if (field === 'name' && !normalizedValue) {
        showToast('warning', 'Backup name is required.');
        return;
    }

    const optimisticBackup = { ...currentBackupSnapshot };

    if (field === 'name') {
        optimisticBackup.name = normalizedValue;
    } else {
        optimisticBackup.note = normalizedValue ? normalizedValue : null;
    }

    selectedBackupDetails = optimisticBackup;
    if (cacheIndex >= 0) {
        backupsCache[cacheIndex] = { ...backupsCache[cacheIndex], ...optimisticBackup };
    }

    renderBackupDetails(optimisticBackup);
    renderBackupList();
    setDetailActionDisabled(true);

    try {
        const payload = field === 'name'
            ? { name: normalizedValue }
            : { note: normalizedValue };
        const updated = await updateBackupMetadata(backupId, payload);
        const stillSelected = Number(selectedBackupId) === Number(backupId);
        if (cacheIndex >= 0) {
            backupsCache[cacheIndex] = { ...backupsCache[cacheIndex], ...updated };
        }
        if (stillSelected) {
            selectedBackupDetails = updated;
            renderBackupDetails(updated);
        } else {
            clearInlineEditState();
        }
        renderBackupList();
        showToast('success', field === 'name' ? 'Backup renamed successfully.' : 'Backup note updated successfully.');
    } catch (error) {
        const stillSelected = Number(selectedBackupId) === Number(backupId);
        if (cacheIndex >= 0 && cacheSnapshot) {
            backupsCache[cacheIndex] = cacheSnapshot;
        }
        if (stillSelected) {
            selectedBackupDetails = currentBackupSnapshot;
            renderBackupDetails(currentBackupSnapshot);
        } else {
            clearInlineEditState();
        }
        renderBackupList();
        showToast('error', `Failed to update backup: ${error.message}`);
    } finally {
        setDetailActionDisabled(false);
    }
}

function renderRestoreResult(result) {
    const container = document.getElementById('backup-restore-result');
    const titleEl = document.getElementById('backup-restore-result-title');
    const listEl = document.getElementById('backup-restore-result-list');

    if (!container || !titleEl || !listEl) return;

    const restoredCount = Number(result?.restored_count) || 0;
    const skipped = Array.isArray(result?.skipped) ? result.skipped : [];
    const backupName = result?.backup_name || 'this backup';

    titleEl.textContent = '';
    listEl.innerHTML = '';
    container.classList.remove('is-warning');

    if (restoredCount === 0) {
        titleEl.textContent = 'Nothing was restored - every exercise is missing from the catalog.';
        container.classList.add('is-warning');
        listEl.innerHTML = skipped.map((name) => `<li>${escapeHtml(name)}</li>`).join('');
    } else if (skipped.length > 0) {
        titleEl.textContent = `${restoredCount} exercises restored. ${skipped.length} skipped because they are no longer in the catalog:`;
        listEl.innerHTML = skipped.map((name) => `<li>${escapeHtml(name)}</li>`).join('');
    } else {
        titleEl.textContent = `Restored ${restoredCount} exercises from "${backupName}".`;
    }

    container.hidden = false;
}

function renderLibraryState(iconClass, message) {
    const listContainer = document.getElementById('backup-center-list');
    if (!listContainer) return;

    listContainer.innerHTML = `
        <div class="backup-library-state">
            <i class="${iconClass}" aria-hidden="true"></i>
            <span>${escapeHtml(message)}</span>
        </div>
    `;
}

function renderBackupList() {
    const listContainer = document.getElementById('backup-center-list');
    if (!listContainer) return;

    const visibleBackups = getVisibleBackups();

    if (backupsCache.length === 0) {
        renderLibraryState('fas fa-archive', 'No backups yet. Save your current program to create the first snapshot.');
        return;
    }

    if (visibleBackups.length === 0) {
        renderLibraryState('fas fa-search', 'No backups match the current search or filter.');
        return;
    }

    listContainer.innerHTML = visibleBackups.map((backup) => {
        const isSelected = Number(backup.id) === Number(selectedBackupId);
        const badgeClass = backup.backup_type === 'auto' ? 'is-auto' : 'is-manual';
        const badgeLabel = backup.backup_type === 'auto' ? 'Auto' : 'Manual';

        return `
            <button type="button"
                    class="backup-record ${isSelected ? 'is-selected' : ''}"
                    data-role="backup-record"
                    data-backup-id="${backup.id}">
                <div class="backup-record-head">
                    <p class="backup-record-name">${escapeHtml(backup.name)}</p>
                    <span class="backup-record-badge ${badgeClass}">${badgeLabel}</span>
                </div>
                <div class="backup-record-meta">
                    <span>${backup.item_count} exercises</span>
                    <span>${escapeHtml(formatDate(backup.created_at))}</span>
                </div>
                ${backup.note ? `<p class="backup-record-note">${escapeHtml(backup.note)}</p>` : ''}
            </button>
        `;
    }).join('');
}

function renderEmptyDetail() {
    const emptyState = document.getElementById('backup-detail-empty');
    const detailPanel = document.getElementById('backup-detail-panel');

    if (emptyState) emptyState.hidden = false;
    if (detailPanel) detailPanel.hidden = true;

    selectedBackupDetails = null;
    clearInlineEditState();
    clearPendingAction();
    clearRestoreResultPanel();
    clearEmptySaveWarning();
}

function renderDetailLoading() {
    const emptyState = document.getElementById('backup-detail-empty');
    const detailPanel = document.getElementById('backup-detail-panel');

    if (emptyState) emptyState.hidden = true;
    if (detailPanel) detailPanel.hidden = false;

    const itemsBody = document.getElementById('backup-detail-items-body');
    if (itemsBody) {
        itemsBody.innerHTML = `
            <tr>
                <td colspan="8" class="backup-empty-table">Loading backup details...</td>
            </tr>
        `;
    }
}

function renderDetailError(message) {
    const emptyState = document.getElementById('backup-detail-empty');
    const detailPanel = document.getElementById('backup-detail-panel');
    const itemsBody = document.getElementById('backup-detail-items-body');

    if (emptyState) emptyState.hidden = true;
    if (detailPanel) detailPanel.hidden = false;
    if (itemsBody) {
        itemsBody.innerHTML = `
            <tr>
                <td colspan="8" class="backup-empty-table">${escapeHtml(message)}</td>
            </tr>
        `;
    }
    clearInlineEditState();
    clearPendingAction();
    clearRestoreResultPanel();
    clearEmptySaveWarning();
}

function renderBackupDetails(backup) {
    const emptyState = document.getElementById('backup-detail-empty');
    const detailPanel = document.getElementById('backup-detail-panel');
    const typeEl = document.getElementById('backup-detail-type');
    const nameEl = document.getElementById('backup-detail-name');
    const createdEl = document.getElementById('backup-detail-created');
    const countEl = document.getElementById('backup-detail-count');
    const schemaEl = document.getElementById('backup-detail-schema');
    const noteEl = document.getElementById('backup-detail-note');
    const itemsBody = document.getElementById('backup-detail-items-body');

    clearInlineEditState();
    if (emptyState) emptyState.hidden = true;
    if (detailPanel) detailPanel.hidden = false;
    if (typeEl) typeEl.textContent = backup.backup_type === 'auto' ? 'Auto recovery backup' : 'Manual backup';
    if (nameEl) nameEl.textContent = backup.name || 'Untitled backup';
    if (createdEl) createdEl.textContent = `Created ${formatDate(backup.created_at)}`;
    if (countEl) countEl.textContent = String(backup.item_count ?? backup.items?.length ?? 0);
    if (schemaEl) schemaEl.textContent = String(backup.schema_version ?? 1);

    if (noteEl) {
        if (backup.note) {
            noteEl.hidden = false;
            noteEl.textContent = backup.note;
        } else {
            noteEl.hidden = true;
            noteEl.textContent = '';
        }
    }

    if (itemsBody) {
        const items = Array.isArray(backup.items) ? backup.items : [];

        if (items.length === 0) {
            itemsBody.innerHTML = `
                <tr>
                    <td colspan="8" class="backup-empty-table">This backup does not contain any exercises.</td>
                </tr>
            `;
        } else {
            itemsBody.innerHTML = items.map((item) => `
                <tr>
                    <td data-label="Routine">${escapeHtml(item.routine || '')}</td>
                    <td data-label="Exercise">${escapeHtml(item.exercise || '')}</td>
                    <td data-label="Sets" class="is-num">${item.sets ?? ''}</td>
                    <td data-label="Rep Range">${item.min_rep_range ?? ''}-${item.max_rep_range ?? ''}</td>
                    <td data-label="Weight" class="is-num">${item.weight ?? ''}</td>
                    <td data-label="RIR" class="is-num">${item.rir ?? '-'}</td>
                    <td data-label="RPE" class="is-num">${item.rpe ?? '-'}</td>
                    <td data-label="Superset">${escapeHtml(item.superset_group || '-')}</td>
                </tr>
            `).join('');
        }
    }

    clearPendingAction();
    clearRestoreResultPanel();
}

async function loadBackupDetails(backupId) {
    if (!backupId) {
        renderEmptyDetail();
        return;
    }

    selectedBackupId = Number(backupId);
    renderBackupList();
    renderDetailLoading();

    const requestId = ++detailRequestSequence;

    try {
        const details = await fetchBackupDetails(selectedBackupId);
        if (requestId !== detailRequestSequence) {
            return;
        }

        selectedBackupDetails = details;
        renderBackupDetails(details);
    } catch (error) {
        if (requestId !== detailRequestSequence) {
            return;
        }

        selectedBackupDetails = null;
        renderDetailError(`Failed to load this backup: ${error.message}`);
    }
}

async function refreshBackupCenter(options = {}) {
    const {
        preserveSelection = true,
        preferredSelectionId = null
    } = options;

    renderLibraryState('fas fa-spinner fa-spin', 'Loading backups...');

    try {
        backupsCache = await fetchBackups();
        updateSummaryCards(backupsCache);

        const visibleBackups = getVisibleBackups();
        const availableIds = new Set(backupsCache.map((backup) => Number(backup.id)));
        const visibleIds = new Set(visibleBackups.map((backup) => Number(backup.id)));

        if (preferredSelectionId && availableIds.has(Number(preferredSelectionId))) {
            selectedBackupId = Number(preferredSelectionId);
        } else if (!preserveSelection || !availableIds.has(Number(selectedBackupId))) {
            selectedBackupId = visibleBackups[0]?.id ?? backupsCache[0]?.id ?? null;
        } else if (!visibleIds.has(Number(selectedBackupId)) && visibleBackups.length > 0) {
            selectedBackupId = visibleBackups[0].id;
        }

        renderBackupList();

        if (selectedBackupId) {
            await loadBackupDetails(selectedBackupId);
        } else {
            renderEmptyDetail();
        }
    } catch (error) {
        renderLibraryState('fas fa-exclamation-triangle', `Failed to load backups: ${error.message}`);
        renderEmptyDetail();
    }
}

function showPendingAction(type) {
    if (!selectedBackupDetails) return;

    pendingAction = type;
    clearInlineEditState();

    const confirmWrap = document.getElementById('backup-action-confirm');
    const titleEl = document.getElementById('backup-action-title');
    const textEl = document.getElementById('backup-action-text');
    const confirmBtn = document.getElementById('backup-action-confirm-btn');
    const saveFirstBtn = document.getElementById('backup-restore-save-first');

    if (!confirmWrap || !titleEl || !textEl || !confirmBtn) return;

    if (type === 'restore') {
        titleEl.textContent = 'Confirm restore';
        textEl.textContent = `Restore "${selectedBackupDetails.name}"? The current workout plan and all logged sessions will be cleared.`;
        confirmBtn.className = 'btn btn-primary btn-calm-primary';
        confirmBtn.innerHTML = '<i class="fas fa-undo" aria-hidden="true"></i> Confirm Restore';
        if (saveFirstBtn) {
            saveFirstBtn.hidden = false;
            saveFirstBtn.disabled = false;
            saveFirstBtn.innerHTML = '<i class="fas fa-shield-alt" aria-hidden="true"></i> Save current plan first';
        }
    } else {
        titleEl.textContent = 'Confirm delete';
        textEl.textContent = `Delete "${selectedBackupDetails.name}" permanently from the library?`;
        confirmBtn.className = 'btn btn-danger btn-calm-danger';
        confirmBtn.innerHTML = '<i class="fas fa-trash" aria-hidden="true"></i> Confirm Delete';
        if (saveFirstBtn) {
            saveFirstBtn.hidden = true;
        }
    }

    confirmWrap.hidden = false;
}

async function handleSaveSubmit(event) {
    event.preventDefault();

    const nameInput = document.getElementById('backup-center-name');
    const noteInput = document.getElementById('backup-center-note');
    const submitBtn = document.getElementById('backup-center-save-submit');
    const warningEl = document.getElementById('backup-save-empty-warning');
    const activeCountEl = document.getElementById('backup-active-count');

    if (!nameInput || !submitBtn) return;

    const name = nameInput.value.trim();
    const note = noteInput ? noteInput.value.trim() : '';
    const activeCount = Number.parseInt(activeCountEl?.textContent || '0', 10) || 0;

    if (!name) {
        showToast('warning', 'Please enter a name for the backup.');
        nameInput.focus();
        return;
    }

    if (activeCount > 0) {
        clearEmptySaveWarning();
    } else if (!emptyWarningShown) {
        emptyWarningShown = true;
        if (warningEl) warningEl.hidden = false;
        return;
    }

    const originalHtml = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Saving...';

    try {
        const backup = await createBackup(name, note || null);
        showToast('success', `Backup "${backup.name}" created with ${backup.item_count} exercises.`);

        nameInput.value = '';
        if (noteInput) noteInput.value = '';

        const searchInput = document.getElementById('backup-search');
        if (searchInput) searchInput.value = '';

        const allFilterBtn = document.querySelector('.backup-filter-btn[data-filter="all"]');
        if (allFilterBtn instanceof HTMLButtonElement) {
            document.querySelectorAll('.backup-filter-btn').forEach((btn) => {
                btn.classList.remove('active', 'btn-calm-primary');
                btn.classList.add('btn-calm-ghost');
                btn.setAttribute('aria-pressed', 'false');
            });
            allFilterBtn.classList.add('active', 'btn-calm-primary');
            allFilterBtn.classList.remove('btn-calm-ghost');
            allFilterBtn.setAttribute('aria-pressed', 'true');
        }

        await refreshBackupCenter({ preserveSelection: false, preferredSelectionId: backup.id });
    } catch (error) {
        showToast('error', `Failed to create backup: ${error.message}`);
    } finally {
        clearEmptySaveWarning();
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHtml;
    }
}

async function handleConfirmAction() {
    if (!pendingAction || !selectedBackupDetails) return;

    const confirmBtn = document.getElementById('backup-action-confirm-btn');
    const saveFirstBtn = document.getElementById('backup-restore-save-first');
    if (!confirmBtn) return;

    const originalHtml = confirmBtn.innerHTML;
    const originalSaveFirstHtml = saveFirstBtn ? saveFirstBtn.innerHTML : '';
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Working...';
    if (saveFirstBtn) {
        saveFirstBtn.disabled = true;
        saveFirstBtn.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Saving...';
    }

    try {
        if (pendingAction === 'restore') {
            const restoredBackupId = selectedBackupDetails.id;
            const result = await restoreBackup(selectedBackupDetails.id);
            updateActiveProgramCount(result.restored_count ?? 0);

            renderRestoreResult(result);

            const toastLevel = Number(result.restored_count) === 0 ? 'warning' : 'success';
            let message;
            if (Number(result.restored_count) === 0) {
                message = 'Nothing was restored. Every exercise from this backup is missing from the catalog.';
            } else if (Array.isArray(result.skipped) && result.skipped.length > 0) {
                message = `Restored ${result.restored_count} exercises from "${result.backup_name}". ${result.skipped.length} exercises were skipped because they no longer exist in the catalog.`;
            } else {
                message = `Restored ${result.restored_count} exercises from "${result.backup_name}".`;
            }

            showToast(toastLevel, message);
            notifyVolumeAffectingPlanChange('program-backup-restore');
            clearPendingAction();
            await refreshBackupCenter({ preserveSelection: true, preferredSelectionId: restoredBackupId });
            renderRestoreResult(result);
        } else if (pendingAction === 'delete') {
            const deletedBackupId = selectedBackupDetails.id;
            await deleteBackup(deletedBackupId);
            showToast('success', 'Backup deleted successfully.');

            selectedBackupId = null;
            selectedBackupDetails = null;
            clearPendingAction();
            await refreshBackupCenter({ preserveSelection: false });
        }
    } catch (error) {
        showToast('error', `Failed to ${pendingAction} backup: ${error.message}`);
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalHtml;
        if (saveFirstBtn) {
            saveFirstBtn.disabled = false;
            saveFirstBtn.innerHTML = originalSaveFirstHtml;
        }
    }
}

function handleListClick(event) {
    const target = event.target instanceof HTMLElement ? event.target.closest('[data-role="backup-record"]') : null;
    if (!target) return;

    const backupId = Number(target.getAttribute('data-backup-id'));
    if (!backupId || backupId === selectedBackupId) return;

    clearPendingAction();
    loadBackupDetails(backupId);
}

function handleFilterClick(event) {
    const button = event.target instanceof HTMLElement ? event.target.closest('.backup-filter-btn') : null;
    if (!button || !(button instanceof HTMLButtonElement)) return;

    document.querySelectorAll('.backup-filter-btn').forEach((btn) => {
        btn.classList.remove('active', 'btn-calm-primary');
        btn.classList.add('btn-calm-ghost');
        btn.setAttribute('aria-pressed', 'false');
    });

    button.classList.add('active', 'btn-calm-primary');
    button.classList.remove('btn-calm-ghost');
    button.setAttribute('aria-pressed', 'true');

    const visibleBackups = getVisibleBackups();
    if (!visibleBackups.some((backup) => Number(backup.id) === Number(selectedBackupId))) {
        selectedBackupId = visibleBackups[0]?.id ?? null;
    }

    renderBackupList();

    if (selectedBackupId) {
        loadBackupDetails(selectedBackupId);
    } else {
        renderEmptyDetail();
    }
}

export function initializeBackupCenter() {
    const root = getPageRoot();
    if (!root || backupCenterInitialized) {
        return;
    }

    backupCenterInitialized = true;

    const saveForm = document.getElementById('backup-center-save-form');
    const searchInput = document.getElementById('backup-search');
    const listContainer = document.getElementById('backup-center-list');
    const filterGroup = root.querySelector('.backup-filter-group');
    const sortSelect = document.getElementById('backup-sort');
    const restoreBtn = document.getElementById('backup-detail-restore');
    const editNameBtn = document.getElementById('backup-detail-edit-name');
    const editNoteBtn = document.getElementById('backup-detail-edit-note');
    const saveFirstBtn = document.getElementById('backup-restore-save-first');
    const deleteBtn = document.getElementById('backup-detail-delete');
    const cancelBtn = document.getElementById('backup-action-cancel');
    const confirmBtn = document.getElementById('backup-action-confirm-btn');

    if (sortSelect instanceof HTMLSelectElement) {
        const storedSort = window.localStorage.getItem(SORT_PREF_KEY);
        const allowedSorts = new Set(['newest', 'oldest', 'name-asc', 'name-desc']);
        sortSelect.value = allowedSorts.has(storedSort || '') ? storedSort : 'newest';
        if (!allowedSorts.has(storedSort || '')) {
            window.localStorage.setItem(SORT_PREF_KEY, sortSelect.value);
        }
    }

    if (saveForm) {
        saveForm.addEventListener('submit', handleSaveSubmit);
    }

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const visibleBackups = getVisibleBackups();
            if (!visibleBackups.some((backup) => Number(backup.id) === Number(selectedBackupId))) {
                selectedBackupId = visibleBackups[0]?.id ?? null;
            }

            renderBackupList();

            if (selectedBackupId) {
                loadBackupDetails(selectedBackupId);
            } else {
                renderEmptyDetail();
            }
        });
    }

    if (listContainer) {
        listContainer.addEventListener('click', handleListClick);
    }

    if (filterGroup) {
        filterGroup.addEventListener('click', handleFilterClick);
    }

    if (sortSelect) {
        sortSelect.addEventListener('change', () => {
            window.localStorage.setItem(SORT_PREF_KEY, sortSelect.value);

            const visibleBackups = getVisibleBackups();
            if (!visibleBackups.some((backup) => Number(backup.id) === Number(selectedBackupId))) {
                selectedBackupId = visibleBackups[0]?.id ?? null;
            }

            renderBackupList();

            if (selectedBackupId) {
                loadBackupDetails(selectedBackupId);
            } else {
                renderEmptyDetail();
            }
        });
    }

    if (restoreBtn) {
        restoreBtn.addEventListener('click', () => showPendingAction('restore'));
    }

    if (editNameBtn) {
        editNameBtn.addEventListener('click', () => {
            if (!selectedBackupDetails) return;
            if (inlineEditField) return;
            renderInlineEditor('name');
        });
    }

    if (editNoteBtn) {
        editNoteBtn.addEventListener('click', () => {
            if (!selectedBackupDetails) return;
            if (inlineEditField) return;
            renderInlineEditor('note');
        });
    }

    if (saveFirstBtn) {
        saveFirstBtn.addEventListener('click', async () => {
            if (!selectedBackupDetails) return;

            const restoreConfirmBtn = document.getElementById('backup-action-confirm-btn');
            const originalSaveFirstHtml = saveFirstBtn.innerHTML;
            const originalConfirmHtml = restoreConfirmBtn ? restoreConfirmBtn.innerHTML : '';

            saveFirstBtn.disabled = true;
            saveFirstBtn.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Saving...';
            if (restoreConfirmBtn) {
                restoreConfirmBtn.disabled = true;
                restoreConfirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Working...';
            }

            try {
                const stamp = new Date().toISOString().replace('T', ' ').slice(0, 19);
                const backup = await createBackup(`Pre-restore snapshot (${stamp})`, 'Automatic snapshot taken before restore');
                showToast('success', `Current plan saved as "${backup.name}".`);
                const preferredSelectionId = selectedBackupDetails.id;
                await refreshBackupCenter({ preserveSelection: true, preferredSelectionId });
            } catch (error) {
                showToast('error', `Failed to save current plan first: ${error.message}`);
                saveFirstBtn.disabled = false;
                saveFirstBtn.innerHTML = originalSaveFirstHtml;
                if (restoreConfirmBtn) {
                    restoreConfirmBtn.disabled = false;
                    restoreConfirmBtn.innerHTML = originalConfirmHtml;
                }
            }
        });
    }

    if (deleteBtn) {
        deleteBtn.addEventListener('click', () => showPendingAction('delete'));
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', clearPendingAction);
    }

    if (confirmBtn) {
        confirmBtn.addEventListener('click', handleConfirmAction);
    }

    refreshBackupCenter({ preserveSelection: false }).then(() => {
        applyNavigationIntent();
    });
}
