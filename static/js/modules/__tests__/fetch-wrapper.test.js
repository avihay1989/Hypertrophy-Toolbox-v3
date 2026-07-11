// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../toast.js', () => ({ showToast: vi.fn() }));

import { apiFetch } from '../fetch-wrapper.js';

describe('apiFetch request compatibility options', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it('can preserve an existing caller header set exactly', async () => {
        const response = {
            ok: true,
            headers: { get: () => 'application/json' },
            json: vi.fn().mockResolvedValue({ ok: true, status: 'success', data: {} }),
        };
        const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response);
        const headers = {
            Accept: 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        };

        await apiFetch('/example', {
            headers,
            useDefaultHeaders: false,
            showLoading: false,
            showErrorToast: false,
            retries: 0,
        });

        expect(fetchMock).toHaveBeenCalledWith('/example', {
            method: 'GET',
            headers,
        });
    });

    it('preserves a top-level message from a non-standard JSON error response', async () => {
        vi.spyOn(globalThis, 'fetch').mockResolvedValue({
            ok: false,
            status: 400,
            headers: { get: () => 'application/json' },
            json: vi.fn().mockResolvedValue({ message: 'Existing caller message' }),
        });

        await expect(apiFetch('/example', {
            showLoading: false,
            showErrorToast: false,
            retries: 0,
        })).rejects.toMatchObject({
            code: 'UNKNOWN_ERROR',
            message: 'Existing caller message',
        });
    });

    it('retains the existing NETWORK_ERROR classification for rejected fetches', async () => {
        vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Connection lost'));

        await expect(apiFetch('/example', {
            showLoading: false,
            showErrorToast: false,
            retries: 0,
        })).rejects.toMatchObject({
            code: 'NETWORK_ERROR',
            message: 'Connection lost',
        });
    });
});
