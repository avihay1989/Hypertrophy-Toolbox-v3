import { api } from './fetch-wrapper.js';

const STORAGE_KEY = 'vpDrawer.open';

function debounce(fn, delay) {
    let timer = null;
    return (...args) => {
        window.clearTimeout(timer);
        timer = window.setTimeout(() => fn(...args), delay);
    };
}

function unwrapPayload(payload) {
    return payload && typeof payload === 'object' && 'data' in payload ? payload.data : payload;
}

function formatSets(value) {
    const number = Number(value || 0);
    return Number.isInteger(number) ? String(number) : number.toFixed(1);
}

function setDrawerOpen(open) {
    const drawer = document.getElementById('vpDrawer');
    const toggle = document.getElementById('vpToggle');
    const backdrop = document.getElementById('vpBackdrop');
    if (!drawer || !toggle || !backdrop) {
        return;
    }

    drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    backdrop.hidden = !open;
    localStorage.setItem(STORAGE_KEY, open ? 'true' : 'false');
}

function moveOverlayNodesToBody() {
    const drawer = document.getElementById('vpDrawer');
    const backdrop = document.getElementById('vpBackdrop');
    if (backdrop && backdrop.parentElement !== document.body) {
        document.body.appendChild(backdrop);
    }
    if (drawer && drawer.parentElement !== document.body) {
        document.body.appendChild(drawer);
    }
}

function wireDrawer() {
    const drawer = document.getElementById('vpDrawer');
    if (!drawer || drawer.dataset.initialized === 'true') {
        return;
    }
    drawer.dataset.initialized = 'true';

    document.getElementById('vpToggle')?.addEventListener('click', () => {
        setDrawerOpen(drawer.getAttribute('aria-hidden') !== 'false');
    });
    document.getElementById('vpActiveSummary')?.addEventListener('click', () => setDrawerOpen(true));
    drawer.querySelector('.vp-close')?.addEventListener('click', () => setDrawerOpen(false));
    document.getElementById('vpBackdrop')?.addEventListener('click', () => setDrawerOpen(false));
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && drawer.getAttribute('aria-hidden') === 'false') {
            setDrawerOpen(false);
        }
    });

    setDrawerOpen(localStorage.getItem(STORAGE_KEY) === 'true');
}

function renderLoading(body) {
    body.innerHTML = '<div class="vp-state">Loading volume targets...</div>';
}

function renderError(body) {
    body.innerHTML = '<div class="vp-state vp-state--error">Volume targets could not be loaded.</div>';
}

function renderEmpty(body) {
    body.innerHTML = `
        <div class="vp-state">
            <p>No active volume plan. Activate one from Volume Splitter to track remaining weekly sets.</p>
            <a href="/volume_splitter">Open Volume Splitter</a>
        </div>
    `;
}

function updateHeaderSummary(data) {
    const summary = document.getElementById('vpActiveSummary');
    if (!summary) {
        return;
    }
    if (!data?.active_plan_exists || !data.active_plan) {
        summary.textContent = 'No active plan - activate one to drive the Plan tab.';
        summary.classList.remove('is-active');
        return;
    }
    summary.textContent = data.active_plan.summary;
    summary.classList.add('is-active');
}

function buildTargetedRow(row) {
    const target = Number(row.target || 0);
    const planned = Number(row.planned || 0);
    const status = row.progress_status || 'under_target';
    const progressMax = Math.max(target, planned, 1);
    const item = document.createElement('article');
    item.className = `vp-row status-${status}`;

    const header = document.createElement('div');
    header.className = 'vp-row__header';

    const name = document.createElement('span');
    name.className = 'vp-row__name';
    name.textContent = row.muscle_group;

    const totals = document.createElement('span');
    totals.className = 'vp-row__sets';
    totals.textContent = `${formatSets(planned)} / ${formatSets(target)}`;

    const progress = document.createElement('progress');
    progress.className = 'vp-progress';
    progress.max = progressMax;
    progress.value = Math.min(planned, progressMax);
    progress.setAttribute('aria-label', `${row.muscle_group} planned sets`);
    progress.setAttribute('aria-valuenow', String(planned));
    progress.setAttribute('aria-valuemax', String(progressMax));

    const meta = document.createElement('div');
    meta.className = 'vp-row__meta';
    meta.innerHTML = `<span class="vp-dot" aria-hidden="true"></span><span>${status.replaceAll('_', ' ')}</span>`;

    header.append(name, totals);
    item.append(header, progress, meta);
    return item;
}

function buildBonusRow(row) {
    const planned = Number(row.planned || 0);
    const item = document.createElement('article');
    item.className = 'vp-row vp-row--bonus status-planned_without_target';

    const header = document.createElement('div');
    header.className = 'vp-row__header';

    const name = document.createElement('span');
    name.className = 'vp-row__name';
    name.textContent = row.muscle_group;

    const totals = document.createElement('span');
    totals.className = 'vp-row__sets';
    const setsLabel = `${formatSets(planned)} ${planned === 1 ? 'set' : 'sets'}`;
    totals.textContent = setsLabel;
    totals.setAttribute('aria-label', `${row.muscle_group}: ${setsLabel} from compound exercises (no target)`);

    header.append(name, totals);
    item.append(header);
    return item;
}

function renderRows(body, data) {
    const rows = Array.isArray(data.rows) ? data.rows : [];
    if (!rows.length) {
        renderEmpty(body);
        return;
    }

    const targeted = [];
    const bonus = [];
    rows.forEach(row => {
        if (row.progress_status === 'planned_without_target') {
            bonus.push(row);
        } else {
            targeted.push(row);
        }
    });

    const fragment = document.createDocumentFragment();

    if (targeted.length) {
        const list = document.createElement('div');
        list.className = 'vp-list';
        targeted.forEach(row => list.appendChild(buildTargetedRow(row)));
        fragment.appendChild(list);
    }

    if (bonus.length) {
        const section = document.createElement('section');
        section.className = 'vp-bonus';
        section.setAttribute('aria-labelledby', 'vpBonusHeading');

        const heading = document.createElement('h3');
        heading.id = 'vpBonusHeading';
        heading.className = 'vp-bonus__heading';
        heading.textContent = 'Bonus from compounds';

        const note = document.createElement('p');
        note.className = 'vp-bonus__note';
        note.textContent = 'Sets attributed to muscles you did not target in this plan.';

        const list = document.createElement('div');
        list.className = 'vp-list vp-list--bonus';
        bonus.forEach(row => list.appendChild(buildBonusRow(row)));

        section.append(heading, note, list);
        fragment.appendChild(section);
    }

    body.replaceChildren(fragment);
}

async function fetchAndRender() {
    const body = document.getElementById('vpDrawerBody');
    if (!body) {
        return;
    }

    renderLoading(body);
    try {
        const payload = await api.get('/api/volume_progress', {
            showErrorToast: false,
            showLoading: false
        });
        const data = unwrapPayload(payload);
        updateHeaderSummary(data);
        if (!data?.active_plan_exists) {
            renderEmpty(body);
            return;
        }
        renderRows(body, data);
    } catch (error) {
        console.error('Error loading volume progress:', error);
        renderError(body);
    }
}

export function initializePlanVolumePanel() {
    const root = document.getElementById('vpDrawer');
    if (!root) {
        return;
    }

    moveOverlayNodesToBody();
    wireDrawer();
    fetchAndRender();
    document.addEventListener(
        'workout-plan:volume-affecting-change',
        debounce(fetchAndRender, 150)
    );
}
