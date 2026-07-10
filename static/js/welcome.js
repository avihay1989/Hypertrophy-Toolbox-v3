/**
 * Welcome page - Erase All Data flow
 * Wires the erase-data modal + confirmation to POST /erase-data, shows a
 * success/error toast, surfaces the auto-backup banner (WPB.8) when present,
 * then reloads. Classic script at the same template position as the former
 * inline block; the bootstrap globals and window.showAutoBackupBanner are
 * available by DOMContentLoaded.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        const eraseDataBtn = document.getElementById('eraseDataBtn');
        const eraseDataModal = new bootstrap.Modal(document.getElementById('eraseDataModal'));
        const confirmEraseBtn = document.getElementById('confirmEraseBtn');

        eraseDataBtn.addEventListener('click', function() {
            eraseDataModal.show();
        });

        confirmEraseBtn.addEventListener('click', async function() {
            try {
                const response = await fetch('/erase-data', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ confirm: 'ERASE_ALL_DATA' })
                });

                const data = await response.json();

                if (data.ok) {
                    eraseDataModal.hide();
                    const toast = new bootstrap.Toast(document.getElementById('successToast'));
                    document.querySelector('#successToast .toast-body span').textContent = data.message;
                    toast.show();

                    const autoBackup = data.data && data.data.auto_backup;
                    if (autoBackup && typeof window.showAutoBackupBanner === 'function') {
                        window.showAutoBackupBanner(autoBackup);
                    }

                    setTimeout(() => window.location.reload(), 2000);
                } else {
                    throw new Error(data.message);
                }
            } catch (error) {
                eraseDataModal.hide();
                const toast = new bootstrap.Toast(document.getElementById('errorToast'));
                document.querySelector('#errorToast .toast-body span').textContent = `Failed to erase data: ${error.message}`;
                toast.show();
            }
        });
    });
})();
