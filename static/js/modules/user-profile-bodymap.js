import {
    annotateBodymapPolygons,
    COVERAGE_LIFT_LABELS,
    COVERAGE_MUSCLE_CHAIN,
    loadBodymapSvg,
} from './bodymap-svg.js';
import {
    epley1rm,
    isLiftFilled,
    liftRowsFromForm,
} from './user-profile-data.js';

// =============================================================================
// Issue #19 — Bodymap coverage view
// =============================================================================

const BODYMAP_STATE = {
    side: 'front',
    svgMounted: { front: false, back: false },
};

const STATE_LABELS = {
    measured: 'Measured',
    cross_muscle: 'Cross-muscle fallback',
    cold_start_only: 'Population estimate',
    not_assessed: 'Not assessed',
};

function computeMuscleCoverage(filledByKey) {
    // Mirror of `muscle_coverage_state` in `utils/profile_estimator.py`.
    // Enforced in lockstep — see the comment on COVERAGE_MUSCLE_CHAIN in
    // bodymap-svg.js.
    const out = {};
    for (const [muscle, chain] of Object.entries(COVERAGE_MUSCLE_CHAIN)) {
        const chainEntries = [];
        const filledEntries = [];
        let firstFilledIdx = null;
        chain.forEach((slug, idx) => {
            const lift = filledByKey.get(slug);
            const filled = isLiftFilled(lift);
            const entry = {
                lift_key: slug,
                label: COVERAGE_LIFT_LABELS[slug] || slug,
                filled,
            };
            if (filled && lift) {
                const weight = Number(lift.weight_kg);
                const reps = Number(lift.reps);
                entry.weight_kg = weight;
                entry.reps = reps;
                if (!slug.startsWith('bodyweight_') && weight > 0 && reps > 0) {
                    entry.estimated_1rm = Math.round(epley1rm(weight, reps) * 10) / 10;
                }
                if (firstFilledIdx === null) firstFilledIdx = idx;
                filledEntries.push(entry);
            }
            chainEntries.push(entry);
        });

        let state;
        if (chain.length === 0) {
            state = 'not_assessed';
        } else if (firstFilledIdx === 0) {
            state = 'measured';
        } else if (firstFilledIdx !== null) {
            state = 'cross_muscle';
        } else {
            state = 'cold_start_only';
        }

        let improvementSlug = null;
        if (state === 'cross_muscle' || state === 'cold_start_only') {
            const next = chainEntries.find(e => !e.filled);
            improvementSlug = next ? next.lift_key : null;
        }

        out[muscle] = {
            muscle,
            state,
            chain: chainEntries,
            filled: filledEntries,
            primary_lift_key: chain[0] || null,
            primary_lift_label: chain[0] ? (COVERAGE_LIFT_LABELS[chain[0]] || chain[0]) : null,
            improvement_lift_key: improvementSlug,
            improvement_lift_label: improvementSlug ? (COVERAGE_LIFT_LABELS[improvementSlug] || improvementSlug) : null,
        };
    }
    return out;
}

async function mountBodymapForSide(stage, side) {
    if (BODYMAP_STATE.svgMounted[side]) return;
    try {
        const svgText = await loadBodymapSvg(side);
        const wrap = document.createElement('div');
        wrap.className = 'profile-bodymap-svg-pane';
        wrap.dataset.bodymapPane = side;
        wrap.hidden = side !== BODYMAP_STATE.side;
        wrap.innerHTML = svgText;
        const svgEl = wrap.querySelector('svg');
        if (svgEl) {
            annotateBodymapPolygons(svgEl, side);
        }
        const loading = stage.querySelector('[data-bodymap-loading]');
        if (loading) loading.remove();
        stage.appendChild(wrap);
        BODYMAP_STATE.svgMounted[side] = true;
    } catch (error) {
        const stageMsg = stage.querySelector('[data-bodymap-loading]');
        if (stageMsg) {
            stageMsg.textContent = 'Could not load body diagram. Refresh to retry.';
        }
    }
}

// Workout-cool back regions can map to multiple backend muscles (BACK →
// Upper Back + Lower Back). The worst state wins so the polygon's fill
// reflects the least-confident muscle in the set — selecting one filled
// lift in a multi-muscle region shouldn't visually claim full coverage of
// the others.
const COVERAGE_STATE_RANK = {
    measured: 3,
    cross_muscle: 2,
    cold_start_only: 1,
    not_assessed: 0,
};

function regionMuscles(region) {
    const plural = region.dataset.bodymapMuscles;
    if (plural) {
        return plural.split(',').map(m => m.trim()).filter(Boolean);
    }
    if (region.dataset.bodymapMuscle) {
        return [region.dataset.bodymapMuscle];
    }
    return [];
}

function aggregateCoverageForRegion(region, coverage) {
    const muscles = regionMuscles(region);
    if (muscles.length === 0) return null;
    let worst = null;
    for (const muscle of muscles) {
        const entry = coverage[muscle];
        if (!entry) continue;
        if (worst === null || COVERAGE_STATE_RANK[entry.state] < COVERAGE_STATE_RANK[worst.state]) {
            worst = entry;
        }
    }
    return worst;
}

function applyCoverageStateToPolygons(stage, coverage) {
    const panes = stage.querySelectorAll('[data-bodymap-pane]');
    panes.forEach(pane => {
        const regions = pane.querySelectorAll('.muscle-region');
        regions.forEach(region => {
            for (const cls of ['state-measured', 'state-cross_muscle', 'state-cold_start_only', 'state-not_assessed']) {
                region.classList.remove(cls);
            }
            const entry = aggregateCoverageForRegion(region, coverage);
            if (!entry) {
                region.classList.add('state-not_assessed');
                region.dataset.coverageState = 'not_assessed';
                region.setAttribute('role', 'img');
                region.setAttribute('aria-label', `${region.dataset.bodymapLabel || 'Region'} — Not assessed`);
                return;
            }
            region.classList.add(`state-${entry.state}`);
            region.dataset.coverageState = entry.state;
            region.setAttribute('role', 'img');
            region.setAttribute('aria-label', `${region.dataset.bodymapLabel || entry.muscle} — ${STATE_LABELS[entry.state]}`);
            region.dataset.bodymapImprovement = entry.improvement_lift_key || '';
        });
    });
}

function popoverBodyForState(entry) {
    const fragments = [];
    if (entry.state === 'measured' && entry.filled.length > 0) {
        const list = entry.filled.map(lift => {
            if (lift.weight_kg !== undefined && lift.reps !== undefined) {
                if (lift.lift_key.startsWith('bodyweight_')) {
                    return `<li><strong>${lift.label}</strong> &mdash; ${lift.reps} reps (bodyweight)</li>`;
                }
                const oneRm = lift.estimated_1rm !== undefined ? ` &middot; 1RM &asymp; ${lift.estimated_1rm} kg` : '';
                return `<li><strong>${lift.label}</strong> &mdash; ${lift.weight_kg} kg &times; ${lift.reps}${oneRm}</li>`;
            }
            return `<li><strong>${lift.label}</strong></li>`;
        }).join('');
        fragments.push(`<ul class="profile-bodymap-popover-list">${list}</ul>`);
    } else if (entry.state === 'cross_muscle' && entry.filled.length > 0) {
        const fallback = entry.filled[0];
        fragments.push(`<p>Borrowing from <strong>${fallback.label}</strong> with the cross-muscle factor (0.6).</p>`);
    } else if (entry.state === 'cold_start_only') {
        fragments.push(`<p>No reference lift saved. Suggestions for this muscle use the population estimate from your demographics.</p>`);
    } else if (entry.state === 'not_assessed') {
        fragments.push(`<p>The estimator does not seed suggestions for this muscle.</p>`);
    }

    if (entry.improvement_lift_key) {
        fragments.push(
            `<p class="profile-bodymap-popover-action"><a href="#lift-${entry.improvement_lift_key}-weight" data-bodymap-jump="${entry.improvement_lift_key}">How to improve</a> &mdash; enter ${entry.improvement_lift_label}.</p>`
        );
    }
    return fragments.join('');
}

function showPopover(card, region, coverage) {
    const popover = card.querySelector('[data-bodymap-popover]');
    if (!popover) return;
    const label = region.dataset.bodymapLabel || region.dataset.bodymapMuscle || 'Region';
    const entry = aggregateCoverageForRegion(region, coverage);
    if (!entry) {
        popover.querySelector('[data-popover-title]').textContent = label;
        popover.querySelector('[data-popover-state]').textContent = 'Not assessed';
        popover.querySelector('[data-popover-state]').dataset.state = 'not_assessed';
        popover.querySelector('[data-popover-body]').innerHTML = '<p>The estimator does not seed suggestions for this muscle.</p>';
        popover.hidden = false;
        return;
    }
    popover.querySelector('[data-popover-title]').textContent = label;
    const stateNode = popover.querySelector('[data-popover-state]');
    stateNode.textContent = STATE_LABELS[entry.state];
    stateNode.dataset.state = entry.state;
    popover.querySelector('[data-popover-body]').innerHTML = popoverBodyForState(entry);
    popover.hidden = false;
}

function hidePopover(card) {
    const popover = card.querySelector('[data-bodymap-popover]');
    if (popover) popover.hidden = true;
}

function attachPolygonInteractivity(card, stage, getCoverage) {
    const panes = stage.querySelectorAll('[data-bodymap-pane]');
    panes.forEach(pane => {
        const regions = pane.querySelectorAll('.muscle-region');
        regions.forEach(region => {
            if (region.dataset.bodymapBound === '1') return;
            region.dataset.bodymapBound = '1';
            if (regionMuscles(region).length === 0) return;

            region.addEventListener('mouseenter', () => showPopover(card, region, getCoverage()));
            region.addEventListener('mouseleave', () => hidePopover(card));
            region.addEventListener('focus', () => showPopover(card, region, getCoverage()));
            region.addEventListener('blur', () => hidePopover(card));

            // Click → scroll to the matching reference-lift row. For
            // multi-muscle regions (e.g. workout-cool's BACK), the
            // worst-state aggregator picks which muscle's improvement
            // lift gets focused — same rule the polygon's fill follows.
            region.addEventListener('click', event => {
                event.preventDefault();
                const entry = aggregateCoverageForRegion(region, getCoverage());
                if (!entry) return;
                const target = entry.improvement_lift_key || entry.primary_lift_key;
                if (!target) return;
                const input = document.getElementById(`lift-${target}-weight`);
                if (input) {
                    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    try {
                        input.focus({ preventScroll: true });
                    } catch (_) {
                        input.focus();
                    }
                }
            });

            region.setAttribute('tabindex', '0');
        });
    });
}

function bodymapCoverageSnapshot() {
    const liftRows = liftRowsFromForm();
    const filledByKey = new Map(liftRows.map(r => [r.lift_key, r]));
    return computeMuscleCoverage(filledByKey);
}

function applyBodymapState(card, stage, coverage) {
    applyCoverageStateToPolygons(stage, coverage);
    // Mirror the state into the screen-reader summary list so AT users
    // see the same updates after live form changes.
    const srItems = card.querySelectorAll('[data-bodymap-sr-list] [data-sr-muscle]');
    srItems.forEach(node => {
        const muscle = node.dataset.srMuscle;
        const entry = coverage[muscle];
        if (!entry) return;
        node.dataset.srState = entry.state;
        const dd = node.querySelector('dd');
        if (!dd) return;
        if (entry.state === 'measured') {
            const count = entry.filled.length;
            dd.textContent = `Measured (${count} reference lift${count === 1 ? '' : 's'} saved)`;
        } else if (entry.state === 'cross_muscle') {
            const fallback = entry.filled[0];
            dd.textContent = `Inferred from ${fallback ? fallback.label : 'a related lift'} (cross-muscle fallback)`;
        } else if (entry.state === 'cold_start_only') {
            dd.textContent = 'Population estimate (no reference lift saved)';
        } else {
            dd.textContent = 'Not assessed';
        }
    });
}

let bodymapInitialized = false;

function renderBodymapCoverage() {
    const card = document.querySelector('[data-section="muscle coverage"]');
    if (!card) return;
    const stage = card.querySelector('[data-bodymap-svg]');
    if (!stage) return;
    const coverage = bodymapCoverageSnapshot();
    applyBodymapState(card, stage, coverage);
}

async function initializeBodymap() {
    if (bodymapInitialized) return;
    const card = document.querySelector('[data-section="muscle coverage"]');
    if (!card) return;
    const stage = card.querySelector('[data-bodymap-svg]');
    if (!stage) return;

    bodymapInitialized = true;

    let coverage = bodymapCoverageSnapshot();
    const getCoverage = () => coverage;

    await mountBodymapForSide(stage, 'front');
    await mountBodymapForSide(stage, 'back');
    applyCoverageStateToPolygons(stage, coverage);
    attachPolygonInteractivity(card, stage, getCoverage);

    // Side toggle.
    card.querySelectorAll('[data-bodymap-side]').forEach(button => {
        button.addEventListener('click', () => {
            const side = button.dataset.bodymapSide;
            BODYMAP_STATE.side = side;
            card.querySelectorAll('[data-bodymap-side]').forEach(other => {
                const isActive = other === button;
                other.classList.toggle('is-active', isActive);
                other.setAttribute('aria-pressed', String(isActive));
            });
            stage.querySelectorAll('[data-bodymap-pane]').forEach(pane => {
                pane.hidden = pane.dataset.bodymapPane !== side;
            });
            hidePopover(card);
        });
    });

    // Refresh polygon state whenever live coverage recomputes.
    const refresh = () => {
        coverage = bodymapCoverageSnapshot();
        applyBodymapState(card, stage, coverage);
    };
    document.getElementById('profile-lifts-form')?.addEventListener('input', refresh);
    document.getElementById('profile-lifts-form')?.addEventListener('change', refresh);

    // Hide popover when clicking outside.
    document.addEventListener('click', event => {
        if (!card.contains(event.target)) hidePopover(card);
    });
}

// Learned Calibration mode toggle (off/suggest). Not autosave-form-shaped
// (single {mode} payload to a dedicated endpoint), so it's wired directly.

export {
    initializeBodymap,
    renderBodymapCoverage,
};
