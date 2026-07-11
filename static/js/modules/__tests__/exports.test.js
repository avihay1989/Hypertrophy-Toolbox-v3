// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../toast.js', () => ({ showToast: vi.fn() }));
vi.mock('../fetch-wrapper.js', () => ({
    api: { post: vi.fn() },
    isHandledApiError: vi.fn(() => false),
    logApiError: vi.fn(),
}));

import { exportSummary, exportToExcel } from '../exports.js';

describe('raw blob export transport', () => {
    let clickedFilename;

    beforeEach(() => {
        vi.restoreAllMocks();
        clickedFilename = null;
        document.body.innerHTML = `
            <table><tbody id="workout_plan_table_body"><tr><td>Squat</td></tr></tbody></table>
        `;
        localStorage.clear();
        vi.spyOn(console, 'log').mockImplementation(() => {});
        vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
            clickedFilename = this.download;
        });
    });

    it('keeps workout-plan export on raw blob transport and the server filename', async () => {
        const headers = new Headers({
            'Content-Disposition': 'attachment; filename="workout_plan_test.xlsx"',
        });
        const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
            ok: true,
            status: 200,
            statusText: 'OK',
            headers,
            blob: vi.fn().mockResolvedValue(new Blob(['workbook'])),
        });

        await exportToExcel();

        expect(fetchMock).toHaveBeenCalledWith('/export_to_excel?view_mode=simple', {
            method: 'GET',
            headers: {
                Accept: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            },
        });
        expect(clickedFilename).toBe('workout_plan_test.xlsx');
    });

    it('keeps the public summary export helper on raw blob transport and its filename', async () => {
        const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
            ok: true,
            blob: vi.fn().mockResolvedValue(new Blob(['workbook'])),
        });

        await exportSummary('session');

        expect(fetchMock).toHaveBeenCalledWith('/export_session_summary', { method: 'GET' });
        expect(clickedFilename).toBe('session_summary.xlsx');
    });
});
