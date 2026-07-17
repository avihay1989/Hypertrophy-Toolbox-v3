import {
    COHORT_AGE_YEARS,
    COHORT_BODYWEIGHT_KG,
    COHORT_HEIGHT_CM,
    COLD_START_CANONICAL_COMPOUND,
    HIGH_IMPACT_LIFT_PRIORITY,
    bandPillLabel,
    classificationFromForm,
    classifyExperienceTier,
    coldStart1rm,
    computeAccuracyBand,
    epley1rm,
    experienceMultiplier,
    formatYears,
    isLiftFilled,
    liftRowsFromForm,
    nextTierMultiplier,
    tierLabel,
} from './user-profile-data.js';

function renderTiles(card, classification) {
    const setTile = (key, { value, cohort, empty }) => {
        const tile = card.querySelector(`[data-insights-tile="${key}"]`);
        if (!tile) return;
        if (empty) {
            tile.dataset.empty = 'true';
        } else {
            delete tile.dataset.empty;
        }
        const valueNode = tile.querySelector('[data-tile-value]');
        const cohortNode = tile.querySelector('[data-tile-cohort]');
        if (valueNode) valueNode.textContent = value;
        if (cohortNode) cohortNode.textContent = cohort;
    };

    // Bodyweight (used).
    if (classification.bodyweight) {
        const range = classification.rawGender ? COHORT_BODYWEIGHT_KG[classification.rawGender] : null;
        const tier = classification.experienceTier;
        const cohortText = range
            ? (classification.rawGender && tier
                ? `Cohort: ${range[0]}–${range[1]} kg (${classification.gender.toLowerCase()} ${tier})`
                : `Cohort: ${range[0]}–${range[1]} kg (${classification.gender.toLowerCase()})`)
            : 'Cohort range needs gender';
        setTile('bodyweight', {
            value: `${classification.bodyweight} kg`,
            cohort: cohortText,
            empty: false,
        });
    } else {
        setTile('bodyweight', { value: '—', cohort: 'Add bodyweight to enable', empty: true });
    }

    // Height (unused).
    if (classification.height) {
        const range = classification.rawGender ? COHORT_HEIGHT_CM[classification.rawGender] : null;
        setTile('height', {
            value: `${classification.height} cm`,
            cohort: range
                ? `Cohort: ${range[0]}–${range[1]} cm (${classification.gender.toLowerCase()})`
                : 'Cohort range needs gender',
            empty: false,
        });
    } else {
        setTile('height', {
            value: '—',
            cohort: 'Add height (currently unused — flagged for future use)',
            empty: true,
        });
    }

    // Age (unused).
    if (classification.age !== null) {
        setTile('age', {
            value: `${classification.age} yrs`,
            cohort: `Cohort: ${COHORT_AGE_YEARS[0]}–${COHORT_AGE_YEARS[1]} yrs`,
            empty: false,
        });
    } else {
        setTile('age', {
            value: '—',
            cohort: 'Add age (currently unused)',
            empty: true,
        });
    }

    // Experience (used).
    const tier = classification.experienceTier;
    if (tier) {
        const mult = experienceMultiplier(tier);
        const yearsText = formatYears(classification.experienceYears);
        const tile = card.querySelector('[data-insights-tile="experience"]');
        if (tile) {
            delete tile.dataset.empty;
            const valueNode = tile.querySelector('[data-tile-value]');
            const cohortNode = tile.querySelector('[data-tile-cohort]');
            if (valueNode) {
                valueNode.innerHTML = '';
                valueNode.appendChild(document.createTextNode(tierLabel(tier)));
                if (yearsText) {
                    const small = document.createElement('small');
                    small.textContent = ` · ${yearsText}`;
                    valueNode.appendChild(small);
                }
            }
            if (cohortNode) cohortNode.textContent = `Tier multiplier: ×${mult.toFixed(2)} of trained max`;
        }
    } else {
        setTile('experience', {
            value: '—',
            cohort: 'Pick a level to enable cold-start estimates',
            empty: true,
        });
    }
}

function renderCohortSummary(card, classification) {
    const node = card.querySelector('[data-cohort-summary]');
    if (!node) return;
    const genderText = classification.gender ? classification.gender.toLowerCase() : 'unknown gender';
    const ageText = `age ${COHORT_AGE_YEARS[0]}–${COHORT_AGE_YEARS[1]}`;
    const range = classification.rawGender ? COHORT_BODYWEIGHT_KG[classification.rawGender] : null;
    const bodyweightText = range
        ? `bodyweight ${range[0]}–${range[1]} kg`
        : 'bodyweight unknown';
    const tier = classification.experienceTier;
    const yearsText = formatYears(classification.experienceYears);
    const experienceText = tier && yearsText
        ? `${tier} (${yearsText} trained)`
        : 'experience level unknown';
    const missing = !classification.gender || experienceText === 'experience level unknown';
    const body = `${genderText}, ${ageText}, ${bodyweightText}, ${experienceText}`;
    node.textContent = missing
        ? `Estimator cohort: ${body} — fill these to calibrate.`
        : `Estimator cohort: ${body}. Suggestions are calibrated to lifters in this bucket.`;
}

function renderCohortBars(card, classification, liftRows) {
    const section = card.querySelector('[data-insights-bars]');
    const list = card.querySelector('[data-bar-list]');
    if (!section || !list) return;

    if (!classification.rawGender || !classification.bodyweight) {
        list.innerHTML = '';
        section.hidden = true;
        return;
    }

    const tier = classifyExperienceTier(classification.experienceYears);
    const currentMult = experienceMultiplier(tier);
    const nextMult = nextTierMultiplier(tier);

    const filledByKey = new Map(liftRows.map(r => [r.lift_key, r]));
    const newRows = [];
    for (const anchor of COLD_START_CANONICAL_COMPOUND) {
        if (anchor.slug.startsWith('bodyweight_')) continue;
        const row = filledByKey.get(anchor.slug);
        if (!isLiftFilled(row)) continue;
        const weight = Number(row.weight_kg);
        const reps = Number(row.reps);
        if (!(weight > 0) || !(reps > 0)) continue;
        const coldStart = coldStart1rm(anchor.muscle, classification);
        if (coldStart === null || coldStart <= 0) continue;
        const userOneRm = epley1rm(weight, reps);
        const cohortUpper = coldStart * (nextMult / currentMult);
        const maxKg = Math.max(coldStart, userOneRm, cohortUpper) * 1.05;
        const range = (maxKg - 0) || 1;
        const csPct = (coldStart / range) * 100;
        const userPct = (userOneRm / range) * 100;
        const cuPct = (cohortUpper / range) * 100;
        newRows.push({ anchor, coldStart, userOneRm, cohortUpper, csPct, userPct, cuPct });
    }

    if (newRows.length === 0) {
        list.innerHTML = '';
        section.hidden = true;
        return;
    }

    section.hidden = false;
    list.innerHTML = '';
    for (const row of newRows) {
        const li = document.createElement('li');
        li.className = 'profile-insights-bar-row';
        li.dataset.barSlug = row.anchor.slug;

        const head = document.createElement('div');
        head.className = 'profile-insights-bar-head';
        const strong = document.createElement('strong');
        strong.textContent = row.anchor.label;
        const userSpan = document.createElement('span');
        userSpan.className = 'profile-insights-bar-user';
        userSpan.textContent = `≈ ${row.userOneRm.toFixed(1)} kg 1RM`;
        head.appendChild(strong);
        head.appendChild(userSpan);

        const track = document.createElement('div');
        track.className = 'profile-insights-bar-track';
        track.setAttribute('role', 'img');
        track.setAttribute(
            'aria-label',
            `${row.anchor.label}: cold-start ${row.coldStart.toFixed(1)} kg, you ${row.userOneRm.toFixed(1)} kg, cohort upper ${row.cohortUpper.toFixed(1)} kg`,
        );
        const fill = document.createElement('span');
        fill.className = 'profile-insights-bar-fill';
        fill.style.setProperty('--cs-pct', `${row.csPct.toFixed(2)}%`);
        fill.style.setProperty('--cu-pct', `${row.cuPct.toFixed(2)}%`);
        track.appendChild(fill);
        for (const [cls, pct] of [
            ['is-cold-start', row.csPct],
            ['is-user', row.userPct],
            ['is-cohort-upper', row.cuPct],
        ]) {
            const marker = document.createElement('span');
            marker.className = `profile-insights-bar-marker ${cls}`;
            marker.style.setProperty('--mark-pct', `${pct.toFixed(2)}%`);
            track.appendChild(marker);
        }

        const foot = document.createElement('div');
        foot.className = 'profile-insights-bar-foot';
        const csSpan = document.createElement('span');
        csSpan.textContent = `cold-start ≈ ${row.coldStart.toFixed(1)} kg`;
        const cuSpan = document.createElement('span');
        cuSpan.textContent = `cohort upper ≈ ${row.cohortUpper.toFixed(1)} kg`;
        foot.appendChild(csSpan);
        foot.appendChild(cuSpan);

        li.appendChild(head);
        li.appendChild(track);
        li.appendChild(foot);
        list.appendChild(li);
    }
}

function renderProfileInsights() {
    const card = document.querySelector('[data-profile-insights="true"]');
    if (!card) return;

    const classification = classificationFromForm();
    const liftRows = liftRowsFromForm();
    const filledKeys = new Set(liftRows.filter(isLiftFilled).map(r => r.lift_key));
    const hasDemographics = Boolean(classification.gender || classification.bodyweight || classification.experienceYears !== null);

    // Issue #18 — stats tiles + cohort summary + bars.
    renderTiles(card, classification);
    renderCohortSummary(card, classification);
    renderCohortBars(card, classification, liftRows);

    // Cold-start anchors.
    const anchorsSection = card.querySelector('[data-insights-anchors]');
    const anchorList = card.querySelector('[data-anchor-list]');
    const anchorsReady = Boolean(classification.rawGender && classification.bodyweight);
    if (anchorsSection) {
        anchorsSection.hidden = !anchorsReady;
    }
    if (anchorList) {
        anchorList.innerHTML = '';
        for (const anchor of COLD_START_CANONICAL_COMPOUND) {
            const seed = coldStart1rm(anchor.muscle, classification);
            const li = document.createElement('li');
            li.dataset.anchorSlug = anchor.slug;
            const label = document.createElement('strong');
            label.textContent = anchor.label;
            const value = document.createElement('span');
            value.dataset.anchorValue = '';
            value.textContent = seed && seed > 0 ? `≈ ${seed.toFixed(1)} kg 1RM` : '—';
            li.appendChild(label);
            li.appendChild(document.createTextNode(' '));
            li.appendChild(value);
            anchorList.appendChild(li);
        }
    }

    // Replaced-by-your-data list.
    const replacedSection = card.querySelector('[data-insights-replaced]');
    const replacedList = card.querySelector('[data-replaced-list]');
    if (replacedList) {
        replacedList.innerHTML = '';
        const filledByKey = new Map(liftRows.map(r => [r.lift_key, r]));
        for (const anchor of COLD_START_CANONICAL_COMPOUND) {
            if (anchor.slug.startsWith('bodyweight_')) continue;
            const row = filledByKey.get(anchor.slug);
            if (!isLiftFilled(row)) continue;
            const weight = Number(row.weight_kg);
            const reps = Number(row.reps);
            if (!(weight > 0) || !(reps > 0)) continue;
            const oneRm = epley1rm(weight, reps);
            const li = document.createElement('li');
            li.dataset.replacedSlug = anchor.slug;
            const strong = document.createElement('strong');
            strong.textContent = anchor.label;
            const span = document.createElement('span');
            span.textContent = ` (saved ${weight} kg × ${reps} → 1RM ≈ ${oneRm.toFixed(1)} kg)`;
            li.appendChild(strong);
            li.appendChild(span);
            replacedList.appendChild(li);
        }
        if (replacedSection) {
            replacedSection.hidden = replacedList.children.length === 0;
        }
    }

    // Next-high-impact missing list.
    const missingSection = card.querySelector('[data-insights-missing]');
    const missingList = card.querySelector('[data-missing-list]');
    if (missingList) {
        missingList.innerHTML = '';
        const collected = [];
        for (const entry of HIGH_IMPACT_LIFT_PRIORITY) {
            if (filledKeys.has(entry.slug)) continue;
            collected.push(entry);
            if (collected.length >= 3) break;
        }
        for (const entry of collected) {
            const li = document.createElement('li');
            li.dataset.missingSlug = entry.slug;
            li.textContent = entry.label;
            missingList.appendChild(li);
        }
        if (missingSection) {
            missingSection.hidden = collected.length === 0;
        }
    }

    // Accuracy band pill, copy, count, fill bar + Issue #18 donut.
    const summary = computeAccuracyBand(filledKeys, hasDemographics);
    card.dataset.band = summary.band;
    const bandRoot = card.querySelector('[data-insights-band]');
    if (bandRoot) {
        bandRoot.dataset.bandKey = summary.band;
    }
    const pill = card.querySelector('[data-band-pill]');
    if (pill) pill.textContent = bandPillLabel(summary.band);
    const count = card.querySelector('[data-band-count]');
    if (count) count.textContent = `${summary.filledCount} / ${summary.totalSlugs} reference lifts`;
    const copy = card.querySelector('[data-band-copy]');
    if (copy) copy.textContent = summary.copy;
    const fill = card.querySelector('[data-band-fill]');
    if (fill) {
        fill.style.setProperty('--band-progress', String(summary.filledCount));
        fill.style.setProperty('--band-total', String(summary.totalSlugs || 1));
    }
    const donutCount = card.querySelector('[data-donut-count]');
    if (donutCount) {
        donutCount.innerHTML = '';
        donutCount.appendChild(document.createTextNode(String(summary.filledCount)));
        const ofSpan = document.createElement('span');
        ofSpan.className = 'profile-insights-donut-of';
        ofSpan.textContent = `/${summary.totalSlugs}`;
        donutCount.appendChild(ofSpan);
    }
    const donutFill = card.querySelector('[data-donut-fill]');
    if (donutFill) {
        const totalSlugs = summary.totalSlugs || 1;
        const pct = (summary.filledCount / totalSlugs) * 100;
        donutFill.style.strokeDasharray = `${pct.toFixed(2)} ${(100 - pct).toFixed(2)}`;
    }
}

export function bindInsightsAutoUpdate(renderCoverage = () => {}) {
    const refresh = () => {
        renderProfileInsights();
        renderCoverage();
    };
    document.getElementById('profile-demographics-form')?.addEventListener('input', refresh);
    document.getElementById('profile-demographics-form')?.addEventListener('change', refresh);
    document.getElementById('profile-lifts-form')?.addEventListener('input', refresh);
    document.getElementById('profile-lifts-form')?.addEventListener('change', refresh);
}
