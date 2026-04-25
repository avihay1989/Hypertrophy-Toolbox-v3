# Volume Taxonomy Audit

Phase 0 live database audit for Plan <-> Distribute volume integration.

- Database audited: `data/database.db`
- Audit date: 2026-04-25
- Gate: Phase 0 only; no route/template/static feature wiring included.
- Decision source: execution-plan recommended/default decisions confirmed by user instruction to proceed before Phase 1.
- Blank P/S/T strategy recorded in code: `isolated_only`

## Audit queries run

- `SELECT DISTINCT primary_muscle_group FROM exercises ORDER BY 1;`
- `SELECT DISTINCT secondary_muscle_group FROM exercises ORDER BY 1;`
- `SELECT DISTINCT tertiary_muscle_group FROM exercises ORDER BY 1;`
- `SELECT DISTINCT muscle FROM exercise_isolated_muscles ORDER BY 1;`
- `SELECT DISTINCT advanced_isolated_muscles FROM exercises WHERE advanced_isolated_muscles IS NOT NULL;`
- `Row counts per distinct value for each query above.`
- `SELECT COUNT(*) FROM exercises WHERE primary_muscle_group IS NULL OR TRIM(primary_muscle_group)='';`
- `SELECT COUNT(*) FROM exercises WHERE (primary_muscle_group IS NULL OR TRIM(primary_muscle_group)='') AND (secondary_muscle_group IS NULL OR TRIM(secondary_muscle_group)='') AND (tertiary_muscle_group IS NULL OR TRIM(tertiary_muscle_group)='');`
- `SELECT exercise_name, advanced_isolated_muscles FROM exercises WHERE (primary_muscle_group IS NULL OR TRIM(primary_muscle_group)='') AND (secondary_muscle_group IS NULL OR TRIM(secondary_muscle_group)='') AND (tertiary_muscle_group IS NULL OR TRIM(tertiary_muscle_group)='') AND advanced_isolated_muscles IS NOT NULL;`
- `SELECT e.exercise_name, COUNT(eim.muscle) AS iso_count FROM exercises e LEFT JOIN exercise_isolated_muscles eim USING (exercise_name) WHERE (e.primary_muscle_group IS NULL OR TRIM(e.primary_muscle_group)='') AND (e.secondary_muscle_group IS NULL OR TRIM(e.secondary_muscle_group)='') AND (e.tertiary_muscle_group IS NULL OR TRIM(e.tertiary_muscle_group)='') GROUP BY e.exercise_name;`

## Recorded product decisions

| Decision | Recorded answer | Source | Notes |
|---|---|---|---|
| Middle-Shoulder | ADD as Basic bucket; Advanced `lateral-deltoid` | Plan recommended default | Avoids losing many lateral-deltoid exercises into front/rear shoulders. |
| Hip-Adductors / Adductors | ADD as Basic bucket; Advanced `inner-thigh` | Plan recommended default | Keeps adductor work distinct from Glutes. |
| Rotator Cuff | ROLL to `Rear-Shoulder`; Advanced `posterior-deltoid` | Plan recommended default | Diagnostics should still expose these tokens. |
| Upper Back | ROLL to `Middle-Traps`; Advanced `traps-middle` | Plan recommended default | Keeps upper-back rows near the mid-back splitter. |
| Trapezius / Upper Traps | ROLL to `Traps`; Advanced `upper-trapezius` | Plan recommended default | Existing Basic list already has Traps. |
| Shoulders | ROLL to `Front-Shoulder`; Advanced `anterior-deltoid` | Plan recommended default | Underspecified shoulder data uses a deterministic fallback. |
| Back / general back | ROLL to `Latissimus-Dorsi`; Advanced `lats` | Plan recommended default | General fallback for broad back labels. |
| D-blank-pst | `isolated_only` | Plan default proposal | Every blank row remains diagnostic; isolated tokens contribute in Phase 1 when present. |

User confirmation was provided by the instruction to proceed with the execution plan.

## P/S/T token rollups

| Token | Primary count | Secondary count | Tertiary count | Total | Proposed Basic | Proposed Advanced | Decision | Notes |
|---|---:|---:|---:|---:|---|---|---|---|
| `Abs/Core` | 52 | 0 | 0 | 52 | `Abdominals` | `upper-abdominals` | ROLL | Canonical/live label. |
| `Back` | 2 | 1 | 1 | 4 | `Latissimus-Dorsi` | `lats` | ROLL | Open execution-plan decision recorded with recommended default. |
| `Biceps` | 94 | 75 | 81 | 250 | `Biceps` | `long-head-biceps` | ROLL | Canonical/live label. |
| `Calves` | 57 | 0 | 7 | 64 | `Calves` | `gastrocnemius` | ROLL | Canonical/live label. |
| `Chest` | 144 | 6 | 1 | 151 | `Chest` | `mid-lower-pectoralis` | ROLL | Canonical/live label. |
| `Core` | 0 | 0 | 8 | 8 | `Abdominals` | `upper-abdominals` | ROLL | Canonical/live label. |
| `Erectors` | 0 | 0 | 73 | 73 | `Lower Back` | `lowerback` | ROLL | Canonical/live label. |
| `External Obliques` | 23 | 91 | 1 | 115 | `Abdominals` | `obliques` | ROLL | Canonical/live label. |
| `Forearms` | 10 | 182 | 12 | 204 | `Forearms` | `wrist-flexors` | ROLL | Canonical/live label. |
| `Front-Shoulder` | 45 | 25 | 122 | 192 | `Front-Shoulder` | `anterior-deltoid` | ROLL | Canonical/live label. |
| `Gluteus Maximus` | 119 | 265 | 8 | 392 | `Glutes` | `gluteus-maximus` | ROLL | Canonical/live label. |
| `Hamstrings` | 50 | 100 | 219 | 369 | `Hamstrings` | `medial-hamstrings` | ROLL | Canonical/live label. |
| `Hip-Adductors` | 2 | 0 | 0 | 2 | `Hip-Adductors` | `inner-thigh` | ADD | Canonical/live label. |
| `Latissimus Dorsi` | 93 | 38 | 0 | 131 | `Latissimus-Dorsi` | `lats` | ROLL | Canonical/live label. |
| `Lower Back` | 9 | 2 | 62 | 73 | `Lower Back` | `lowerback` | ROLL | Canonical/live label. |
| `Middle-Shoulder` | 66 | 0 | 0 | 66 | `Middle-Shoulder` | `lateral-deltoid` | ADD | Canonical/live label. |
| `Middle-Traps` | 4 | 31 | 16 | 51 | `Middle-Traps` | `traps-middle` | ROLL | Canonical/live label. |
| `Neck` | 12 | 0 | 0 | 12 | `Neck` | `upper-trapezius` | ROLL | No dedicated Advanced neck slider; representative fallback only. |
| `Quadriceps` | 237 | 24 | 4 | 265 | `Quadriceps` | `rectus-femoris` | ROLL | Canonical/live label. |
| `Rear-Shoulder` | 50 | 0 | 0 | 50 | `Rear-Shoulder` | `posterior-deltoid` | ROLL | Canonical/live label. |
| `Rectus Abdominis` | 68 | 7 | 12 | 87 | `Abdominals` | `upper-abdominals` | ROLL | Canonical/live label. |
| `Rotator Cuff` | 0 | 22 | 0 | 22 | `Rear-Shoulder` | `posterior-deltoid` | ROLL | Open execution-plan decision recorded with recommended default. |
| `Shoulders` | 3 | 2 | 3 | 8 | `Front-Shoulder` | `anterior-deltoid` | ROLL | Open execution-plan decision recorded with recommended default. |
| `Trapezius` | 21 | 19 | 1 | 41 | `Traps` | `upper-trapezius` | ROLL | Open execution-plan decision recorded with recommended default. |
| `Triceps` | 65 | 167 | 4 | 236 | `Triceps` | `long-head-triceps` | ROLL | Canonical/live label. |
| `Upper Back` | 29 | 0 | 21 | 50 | `Middle-Traps` | `traps-middle` | ROLL | Open execution-plan decision recorded with recommended default. |
| `Upper Chest` | 0 | 0 | 42 | 42 | `Chest` | `upper-pectoralis` | ROLL | Canonical/live label. |
| `Upper Traps` | 9 | 35 | 0 | 44 | `Traps` | `upper-trapezius` | ROLL | Open execution-plan decision recorded with recommended default. |

## Null and blank P/S/T counts

| Query | Count |
|---|---:|
| Primary blank/null | 633 |
| All P/S/T blank/null | 633 |
| All P/S/T blank/null with CSV isolated data | 252 |
| All P/S/T blank/null with mapping-table isolated data | 252 |

## Isolated token rollups

| Normalized token | Raw variants | Mapping-table count | CSV token count | Total incidence | Proposed Basic | Proposed Advanced | Decision | Notes |
|---|---|---:|---:|---:|---|---|---|---|
| `adductors` | `Adductors`, `adductors` | 199 | 199 | 398 | `Hip-Adductors` | `inner-thigh` | ROLL | Canonicalized to existing Advanced bucket. |
| `anterior-deltoid` | `Anterior Deltoid`, `anterior deltoid`, `anterior-deltoid` | 168 | 168 | 336 | `Front-Shoulder` | `anterior-deltoid` | ROLL | Canonicalized to existing Advanced bucket. |
| `back` | `back` | 1 | 1 | 2 | `Latissimus-Dorsi` | `lats` | ROLL | Canonicalized to existing Advanced bucket. |
| `biceps-brachii` | `biceps brachii`, `biceps-brachii` | 1 | 1 | 2 | `Biceps` | `long-head-biceps` | ROLL | Canonicalized to existing Advanced bucket. |
| `brachialis` | `brachialis` | 6 | 6 | 12 | `Forearms` | `wrist-flexors` | ROLL | Canonicalized to existing Advanced bucket. |
| `brachioradialis` | `brachioradialis` | 10 | 10 | 20 | `Forearms` | `wrist-flexors` | ROLL | Canonicalized to existing Advanced bucket. |
| `chest` | `chest`, `Chest` | 168 | 168 | 336 | `Chest` | `mid-lower-pectoralis` | ROLL | Canonicalized to existing Advanced bucket. |
| `erector-spinae` | `erector spinae`, `erector-spinae` | 8 | 8 | 16 | `Lower Back` | `lowerback` | ROLL | Canonicalized to existing Advanced bucket. |
| `gastrocnemius` | `Gastrocnemius`, `gastrocnemius` | 32 | 32 | 64 | `Calves` | `gastrocnemius` | ROLL | Canonicalized to existing Advanced bucket. |
| `general-back` | `general back`, `general-back` | 12 | 12 | 24 | `Latissimus-Dorsi` | `lats` | ROLL | Canonicalized to existing Advanced bucket. |
| `gluteus-maximus` | `Gluteus Maximus`, `gluteus maximus`, `gluteus-maximus` | 81 | 81 | 162 | `Glutes` | `gluteus-maximus` | ROLL | Canonicalized to existing Advanced bucket. |
| `gluteus-medius` | `Gluteus Medius`, `gluteus-medius` | 26 | 26 | 52 | `Glutes` | `gluteus-medius` | ROLL | Canonicalized to existing Advanced bucket. |
| `hamstrings` | `hamstrings` | 5 | 5 | 10 | `Hamstrings` | `medial-hamstrings` | ROLL | Canonicalized to existing Advanced bucket. |
| `hip-adductors` | `hip-adductors` | 2 | 2 | 4 | `Hip-Adductors` | `inner-thigh` | ROLL | Canonicalized to existing Advanced bucket. |
| `infraspinatus` | `infraspinatus` | 2 | 2 | 4 | `Rear-Shoulder` | `posterior-deltoid` | ROLL | Canonicalized to existing Advanced bucket. |
| `inner-quadriceps` | `Inner Quadriceps`, `inner-quadriceps` | 12 | 12 | 24 | `Quadriceps` | `inner-quadriceps` | ROLL | Canonicalized to existing Advanced bucket. |
| `inner-thigh` | `Inner Thigh`, `inner-thigh` | 11 | 11 | 22 | `Hip-Adductors` | `inner-thigh` | ROLL | Canonicalized to existing Advanced bucket. |
| `lateral-deltoid` | `Lateral Deltoid`, `lateral deltoid`, `lateral-deltoid` | 112 | 112 | 224 | `Middle-Shoulder` | `lateral-deltoid` | ROLL | Canonicalized to existing Advanced bucket. |
| `lateral-hamstrings` | `Lateral Hamstrings`, `lateral-hamstrings` | 34 | 34 | 68 | `Hamstrings` | `lateral-hamstrings` | ROLL | Canonicalized to existing Advanced bucket. |
| `lateral-head-triceps` | `Lateral Head Triceps`, `lateral-head-triceps` | 7 | 7 | 14 | `Triceps` | `lateral-head-triceps` | ROLL | Canonicalized to existing Advanced bucket. |
| `latissimus-dorsi` | `latissimus dorsi`, `latissimus-dorsi` | 50 | 50 | 100 | `Latissimus-Dorsi` | `lats` | ROLL | Canonicalized to existing Advanced bucket. |
| `long-head-bicep` | `Long Head Bicep`, `long-head-bicep` | 18 | 18 | 36 | `Biceps` | `long-head-biceps` | ROLL | Canonicalized to existing Advanced bucket. |
| `long-head-tricep` | `Long Head Tricep`, `long-head-tricep` | 14 | 14 | 28 | `Triceps` | `long-head-triceps` | ROLL | Canonicalized to existing Advanced bucket. |
| `lower-abdominals` | `Lower Abdominals`, `lower-abdominals` | 23 | 23 | 46 | `Abdominals` | `lower-abdominals` | ROLL | Canonicalized to existing Advanced bucket. |
| `lower-traps` | `Lower Traps`, `lower-traps` | 10 | 10 | 20 | `Middle-Traps` | `lower-trapezius` | ROLL | Canonicalized to existing Advanced bucket. |
| `medial-hamstrings` | `Medial Hamstrings`, `medial-hamstrings` | 6 | 6 | 12 | `Hamstrings` | `medial-hamstrings` | ROLL | Canonicalized to existing Advanced bucket. |
| `medial-head-triceps` | `Medial Head Triceps`, `medial-head-triceps` | 6 | 6 | 12 | `Triceps` | `medial-head-triceps` | ROLL | Canonicalized to existing Advanced bucket. |
| `mid-and-lower-chest` | `Mid and Lower Chest`, `mid-and-lower-chest` | 8 | 8 | 16 | `Chest` | `mid-lower-pectoralis` | ROLL | Canonicalized to existing Advanced bucket. |
| `middle-traps` | `middle-traps`, `Middle-Traps` | 1 | 1 | 2 | `Middle-Traps` | `traps-middle` | ROLL | Canonicalized to existing Advanced bucket. |
| `obliques` | `Obliques`, `obliques` | 115 | 115 | 230 | `Abdominals` | `obliques` | ROLL | Canonicalized to existing Advanced bucket. |
| `outer-quadricep` | `Outer Quadricep`, `outer-quadricep` | 9 | 9 | 18 | `Quadriceps` | `outer-quadriceps` | ROLL | Canonicalized to existing Advanced bucket. |
| `pectoralis-major-clavicular` | `pectoralis major clavicular`, `pectoralis-major-clavicular` | 2 | 2 | 4 | `Chest` | `upper-pectoralis` | ROLL | Canonicalized to existing Advanced bucket. |
| `pectoralis-major-sternal-head` | `pectoralis major sternal head`, `pectoralis-major-sternal-head` | 11 | 11 | 22 | `Chest` | `mid-lower-pectoralis` | ROLL | Canonicalized to existing Advanced bucket. |
| `posterior-deltoid` | `Posterior Deltoid`, `posterior deltoid`, `posterior-deltoid` | 65 | 65 | 130 | `Rear-Shoulder` | `posterior-deltoid` | ROLL | Canonicalized to existing Advanced bucket. |
| `pronators` | `pronators` | 1 | 1 | 2 | `Forearms` | `wrist-flexors` | ROLL | Canonicalized to existing Advanced bucket. |
| `quadriceps` | `quadriceps` | 55 | 55 | 110 | `Quadriceps` | `rectus-femoris`, `inner-quadriceps`, `outer-quadriceps` | ROLL | Distributed umbrella token. |
| `rear-delts` | `Rear Delts`, `rear-delts` | 27 | 27 | 54 | `Rear-Shoulder` | `posterior-deltoid` | ROLL | Canonicalized to existing Advanced bucket. |
| `rear-shoulder` | `Rear-Shoulder`, `rear-shoulder` | 1 | 1 | 2 | `Rear-Shoulder` | `posterior-deltoid` | ROLL | Canonicalized to existing Advanced bucket. |
| `rectus-abdominis` | `rectus abdominis`, `rectus-abdominis` | 44 | 44 | 88 | `Abdominals` | `upper-abdominals` | ROLL | Canonicalized to existing Advanced bucket. |
| `rectus-femoris` | `Rectus Femoris`, `rectus-femoris` | 15 | 15 | 30 | `Quadriceps` | `rectus-femoris` | ROLL | Canonicalized to existing Advanced bucket. |
| `serratus-anterior` | `Serratus Anterior`, `serratus-anterior` | 21 | 21 | 42 | `Chest` | `mid-lower-pectoralis` | ROLL | Canonicalized to existing Advanced bucket. |
| `short-head-bicep` | `Short Head Bicep`, `short-head-bicep` | 13 | 13 | 26 | `Biceps` | `short-head-biceps` | ROLL | Canonicalized to existing Advanced bucket. |
| `soleus` | `Soleus`, `soleus` | 3 | 3 | 6 | `Calves` | `soleus` | ROLL | Canonicalized to existing Advanced bucket. |
| `splenius` | `splenius` | 5 | 5 | 10 | `Neck` | (none) | ROLL | Basic-only neck token; no Advanced neck slider exists today. |
| `sternocleidomastoid` | `sternocleidomastoid` | 7 | 7 | 14 | `Neck` | (none) | ROLL | Basic-only neck token; no Advanced neck slider exists today. |
| `subscapularis` | `subscapularis` | 1 | 1 | 2 | `Rear-Shoulder` | `posterior-deltoid` | ROLL | Canonicalized to existing Advanced bucket. |
| `supinator` | `supinator` | 1 | 1 | 2 | `Forearms` | `wrist-extensors` | ROLL | Canonicalized to existing Advanced bucket. |
| `supraspinatus` | `Supraspinatus`, `supraspinatus` | 4 | 4 | 8 | `Rear-Shoulder` | `posterior-deltoid` | ROLL | Canonicalized to existing Advanced bucket. |
| `tfl` | `tfl`, `Tfl` | 1 | 1 | 2 | `Glutes` | `gluteus-medius` | ROLL | Canonicalized to existing Advanced bucket. |
| `tibialis` | `Tibialis`, `tibialis` | 6 | 6 | 12 | `Calves` | `tibialis` | ROLL | Canonicalized to existing Advanced bucket. |
| `traps-(mid-back)` | `Traps (mid-back)`, `traps-(mid-back)` | 70 | 70 | 140 | `Middle-Traps` | `traps-middle` | ROLL | Canonicalized to existing Advanced bucket. |
| `triceps-brachi` | `triceps brachi`, `triceps-brachi` | 1 | 1 | 2 | `Triceps` | `long-head-triceps` | ROLL | Canonicalized to existing Advanced bucket. |
| `triceps-brachii` | `triceps brachii`, `triceps-brachii` | 26 | 26 | 52 | `Triceps` | `long-head-triceps` | ROLL | Canonicalized to existing Advanced bucket. |
| `upper-abdominals` | `Upper Abdominals`, `upper-abdominals` | 20 | 20 | 40 | `Abdominals` | `upper-abdominals` | ROLL | Canonicalized to existing Advanced bucket. |
| `upper-pectoralis` | `Upper Pectoralis`, `upper-pectoralis` | 5 | 5 | 10 | `Chest` | `upper-pectoralis` | ROLL | Canonicalized to existing Advanced bucket. |
| `upper-trapezius` | `upper trapezius`, `upper-trapezius` | 10 | 10 | 20 | `Traps` | `upper-trapezius` | ROLL | Canonicalized to existing Advanced bucket. |
| `upper-traps` | `Upper Traps`, `upper-traps` | 8 | 8 | 16 | `Traps` | `upper-trapezius` | ROLL | Canonicalized to existing Advanced bucket. |
| `wrist-extensors` | `wrist extensors`, `Wrist Extensors`, `wrist-extensors` | 12 | 12 | 24 | `Forearms` | `wrist-extensors` | ROLL | Canonicalized to existing Advanced bucket. |
| `wrist-flexors` | `Wrist Flexors`, `wrist flexors`, `wrist-flexors` | 6 | 6 | 12 | `Forearms` | `wrist-flexors` | ROLL | Canonicalized to existing Advanced bucket. |

## Raw advanced_isolated_muscles values

| Raw CSV value | Row count |
|---|---:|
| `Adductors` | 199 |
| `Anterior Deltoid` | 45 |
| `anterior deltoid` | 13 |
| `Anterior Deltoid; Chest` | 6 |
| `Anterior Deltoid; Lateral Deltoid` | 38 |
| `Anterior Deltoid; Lateral Deltoid; Obliques` | 1 |
| `Anterior Deltoid; Obliques` | 1 |
| `Anterior Deltoid; Posterior Deltoid` | 4 |
| `Anterior Deltoid; Posterior Deltoid; Chest` | 1 |
| `back` | 1 |
| `biceps brachii` | 1 |
| `brachialis` | 6 |
| `brachioradialis` | 10 |
| `Chest` | 127 |
| `Chest; Anterior Deltoid` | 14 |
| `Chest; Lateral Head Triceps; Medial Head Triceps` | 5 |
| `Chest; Mid and Lower Chest` | 5 |
| `Chest; Mid and Lower Chest; Anterior Deltoid` | 1 |
| `Chest; Mid and Lower Chest; Long Head Tricep; Lateral Head Triceps; Anterior Deltoid` | 1 |
| `Chest; Mid and Lower Chest; Long Head Tricep; Lateral Head Triceps; Medial Head Triceps; Anterior Deltoid` | 1 |
| `Chest; Traps (mid-back)` | 1 |
| `Chest; Upper Pectoralis` | 3 |
| `Chest; Upper Pectoralis; Anterior Deltoid` | 2 |
| `erector spinae` | 8 |
| `Gastrocnemius` | 17 |
| `gastrocnemius` | 15 |
| `general back` | 12 |
| `Gluteus Maximus` | 5 |
| `gluteus maximus` | 41 |
| `Gluteus Maximus; Inner Quadriceps; Outer Quadricep` | 1 |
| `Gluteus Maximus; Lateral Hamstrings` | 29 |
| `Gluteus Medius` | 17 |
| `Gluteus Medius; Chest` | 1 |
| `Gluteus Medius; Gluteus Maximus; Inner Quadriceps` | 1 |
| `Gluteus Medius; Inner Quadriceps` | 1 |
| `Gluteus Medius; Inner Quadriceps; Outer Quadricep` | 1 |
| `Gluteus Medius; Lateral Deltoid; Anterior Deltoid` | 3 |
| `Gluteus Medius; Posterior Deltoid` | 1 |
| `hamstrings` | 5 |
| `hip-adductors` | 2 |
| `infraspinatus` | 2 |
| `Inner Quadriceps` | 1 |
| `Inner Quadriceps; Outer Quadricep` | 1 |
| `Inner Quadriceps; Outer Quadricep; Anterior Deltoid` | 1 |
| `Inner Quadriceps; Outer Quadricep; Gluteus Maximus` | 1 |
| `Inner Quadriceps; Outer Quadricep; Gluteus Maximus; Lateral Deltoid; Anterior Deltoid` | 3 |
| `Inner Quadriceps; Outer Quadricep; Obliques` | 1 |
| `Inner Thigh` | 11 |
| `Lateral Deltoid` | 31 |
| `lateral deltoid` | 4 |
| `Lateral Deltoid; Anterior Deltoid` | 23 |
| `Lateral Deltoid; Anterior Deltoid; Posterior Deltoid` | 7 |
| `Lateral Deltoid; Anterior Deltoid; Traps (mid-back)` | 1 |
| `Lateral Hamstrings` | 5 |
| `latissimus dorsi` | 11 |
| `latissimus-dorsi` | 39 |
| `Long Head Bicep` | 12 |
| `Long Head Bicep; Short Head Bicep` | 6 |
| `Long Head Tricep` | 12 |
| `Lower Abdominals` | 15 |
| `Lower Abdominals; Lower Traps` | 2 |
| `Lower Abdominals; Rectus Femoris` | 2 |
| `Lower Abdominals; Upper Abdominals` | 4 |
| `Lower Traps` | 8 |
| `Medial Hamstrings` | 6 |
| `Obliques` | 102 |
| `obliques` | 6 |
| `Obliques; Gluteus Medius` | 1 |
| `pectoralis major clavicular` | 2 |
| `pectoralis major sternal head` | 11 |
| `Posterior Deltoid` | 27 |
| `posterior deltoid` | 8 |
| `Posterior Deltoid; Traps (mid-back)` | 16 |
| `pronators` | 1 |
| `quadriceps` | 55 |
| `Rear Delts` | 27 |
| `Rear-Shoulder, Middle-Traps, Tfl` | 1 |
| `rectus abdominis` | 44 |
| `Rectus Femoris` | 13 |
| `Serratus Anterior` | 21 |
| `Short Head Bicep` | 6 |
| `Short Head Bicep; Wrist Extensors` | 1 |
| `Soleus` | 3 |
| `splenius` | 5 |
| `sternocleidomastoid` | 7 |
| `subscapularis` | 1 |
| `supinator` | 1 |
| `Supraspinatus` | 2 |
| `supraspinatus` | 2 |
| `Tibialis` | 6 |
| `Traps (mid-back)` | 45 |
| `Traps (mid-back); Anterior Deltoid` | 1 |
| `Traps (mid-back); Lateral Deltoid; Anterior Deltoid; Upper Traps` | 1 |
| `Traps (mid-back); Obliques` | 3 |
| `Traps (mid-back); Posterior Deltoid` | 1 |
| `Traps (mid-back); Upper Traps` | 1 |
| `triceps brachi` | 1 |
| `triceps brachii` | 26 |
| `Upper Abdominals` | 16 |
| `upper trapezius` | 10 |
| `Upper Traps` | 6 |
| `Wrist Extensors` | 8 |
| `wrist extensors` | 2 |
| `Wrist Extensors; Wrist Flexors` | 1 |
| `Wrist Flexors` | 3 |
| `wrist flexors` | 2 |

## Blank P/S/T exercises

| Exercise | advanced_isolated_muscles | isolated tokens | iso_count | Proposed strategy |
|---|---|---|---:|---|
| `Abdominals Stretch Variation Four` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Abdominals Stretch Variation One` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Abdominals Stretch Variation Three` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Abdominals Stretch Variation Two` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Adductor Raise Side Lying Long Lever` | `Inner Thigh` | `inner-thigh` | 1 | ISOLATED_ONLY |
| `Adductor Raise Side Lying Short Lever` | `Inner Thigh` | `inner-thigh` | 1 | ISOLATED_ONLY |
| `Adductor Stretch Dynamic Standing Alternate` | `Inner Thigh` | `inner-thigh` | 1 | ISOLATED_ONLY |
| `Adductor Stretch Dynamic Unilateral 4 Point Position` | `Inner Thigh` | `inner-thigh` | 1 | ISOLATED_ONLY |
| `Adductor Stretch Seated Bilateral Dynamic` | `Inner Thigh` | `inner-thigh` | 1 | ISOLATED_ONLY |
| `Adductor Stretch Seated Bilateral Static` | `Inner Thigh` | `inner-thigh` | 1 | ISOLATED_ONLY |
| `Alphabet` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Alternating Pole Rotation` | `Lateral Deltoid; Anterior Deltoid; Posterior Deltoid` | `anterior-deltoid, lateral-deltoid, posterior-deltoid` | 3 | ISOLATED_ONLY |
| `Alternating Swipe Around` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Ankle Circle` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Backward Arm Circle` | `Lateral Deltoid; Anterior Deltoid; Posterior Deltoid` | `anterior-deltoid, lateral-deltoid, posterior-deltoid` | 3 | ISOLATED_ONLY |
| `Band Floor Quad Stretch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Glute Kickback` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Glute Kickback Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Hip Abduction` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Hip Adduction` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Knee Extension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Press Around` | `Chest; Mid and Lower Chest` | `chest, mid-and-lower-chest` | 2 | ISOLATED_ONLY |
| `Band Pull Around` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Band Seated Cervical Side Flexion` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Seated Cervical Side Flexion Eccentric` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Seated Cervical Side Flexion Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Seated Inversions` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Shoulder Y Raise` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Side Bend` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Band Straight Leg Hip Flexions` | `Rectus Femoris` | `rectus-femoris` | 1 | ISOLATED_ONLY |
| `Band Tricep Kickback` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Band Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Banded Side Walks` | `Gluteus Medius` | `gluteus-medius` | 1 | ISOLATED_ONLY |
| `Barbell Behind The Neck Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Clean And Jerk` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Clean And Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Feet Elevated Figure Four Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Feet Elevated Single Leg Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Feet Elevated Staggered Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Front Rack Step Up` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Hang Clean And Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell High Pull` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Barbell J M Press` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Barbell Landmine Side Bend` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Barbell Muscle Snatch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Power Snatch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Pullover` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Quad Stomp` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Rack Pull` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Barbell Shoulder Extension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Side Step Up` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Snatch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Snatch Grip High Pull` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Barbell Split Jerk` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Step Up` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Step Up Balance` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Thruster` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Barbell Tricep Guillotine Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Barbell Wrist Extension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Biceps Stretch Variation Five` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Biceps Stretch Variation Four` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Biceps Stretch Variation One` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Biceps Stretch Variation Three` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Biceps Stretch Variation Two` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Big Toe Abduction` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Big Toe Dorsiflexion` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bird Dog` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Box Assisted Dips` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Bodyweight Clapping Push Up` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Bodyweight Diamond Knee Push Ups` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Bodyweight Elevated Push Up` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Bodyweight Explosive Push Up` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Bodyweight Feet Elevated Figure Four Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Feet Elevated Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Feet Elevated Single Leg Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Feet Elevated Staggered Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Hands Up Push Ups` | `Chest; Anterior Deltoid` | `anterior-deltoid, chest` | 2 | ISOLATED_ONLY |
| `Bodyweight Hip Abduction` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Knee Push Ups` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Bodyweight Ninety Ninety Hip Stretch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Pike Press` | `Traps (mid-back); Anterior Deltoid` | `anterior-deltoid, traps-(mid-back)` | 2 | ISOLATED_ONLY |
| `Bodyweight Quad Stomp` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Reverse Step Up` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Single Leg Balance Stable` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Stability Ball Hyperextension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Staggered Waiters Bow` | `Gluteus Maximus; Lateral Hamstrings` | `gluteus-maximus, lateral-hamstrings` | 2 | ISOLATED_ONLY |
| `Bodyweight Step Up Knee Drive` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Superman Pull` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bodyweight Thoracic Spine Rotation` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Bodyweight Waiters Bow` | `Gluteus Maximus; Lateral Hamstrings` | `gluteus-maximus, lateral-hamstrings` | 2 | ISOLATED_ONLY |
| `Bosu Ball Burpee` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Bosu Ball Feet Elevated Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bosu Ball Half Burpee` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Bosu Ball Offset Pushup` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Bosu Ball Pike Pushup` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Bosu Ball Pullover` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bosu Ball Pushup` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Bosu Ball Single Leg Balance` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bosu Ball Single Leg Elevated Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bosu Ball Situp` | `Upper Abdominals` | `upper-abdominals` | 1 | ISOLATED_ONLY |
| `Bosu Ball Superman` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Bosu Ball Toe Tap` | `Lower Abdominals` | `lower-abdominals` | 1 | ISOLATED_ONLY |
| `Bosu Ball Up And Over` | `Lower Abdominals` | `lower-abdominals` | 1 | ISOLATED_ONLY |
| `Bosu Ball Walkover Pushup` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Bosu Ball Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Bow Pose` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Box Jump` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Butt Kick` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cable Braced Single Arm Chest Press` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Cable Braced Wrist Extension` | `Wrist Extensors` | `wrist-extensors` | 1 | ISOLATED_ONLY |
| `Cable External Rotation` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cable Half Kneeling High To Low Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Cable Half Kneeling Low To High Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Cable Half Kneeling Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Cable Internal Rotation` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cable Kneeling High To Low Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Cable Kneeling Low To High Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Cable Kneeling Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Cable Leaning Single Arm Skullover` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cable Overhead Tricep Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cable Pull Around` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Cable Quadruped Hip Abduction` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cable Rope Lat Prayer` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cable Single Arm Lat Prayer` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cable Standing Glute Kickback` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cable Standing High To Low Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Cable Standing Hip Adduction` | `Inner Thigh` | `inner-thigh` | 1 | ISOLATED_ONLY |
| `Cable Standing Low To High Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Cable Standing Mid Kickback` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cable Standing Single Arm Chest Press` | `Chest; Anterior Deltoid` | `anterior-deltoid, chest` | 2 | ISOLATED_ONLY |
| `Cable Standing Straight Leg Mid Kickback` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cable Wrist Extension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Assault Bike` | `Chest; Anterior Deltoid` | `anterior-deltoid, chest` | 2 | ISOLATED_ONLY |
| `Cardio Assault Bike Arms Only` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Band Press Jacks` | `Gluteus Medius; Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, gluteus-medius, lateral-deltoid` | 3 | ISOLATED_ONLY |
| `Cardio Band Seal Jacks` | `Gluteus Medius; Chest` | `chest, gluteus-medius` | 2 | ISOLATED_ONLY |
| `Cardio Box Quick Feet` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Criss Cross Jacks` | `Gluteus Medius; Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, gluteus-medius, lateral-deltoid` | 3 | ISOLATED_ONLY |
| `Cardio Diamond Hop` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Figure Eight Sprint` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Forward Scissor` | `Lower Abdominals; Rectus Femoris` | `lower-abdominals, rectus-femoris` | 2 | ISOLATED_ONLY |
| `Cardio In And Out Forward` | `Lower Abdominals; Rectus Femoris` | `lower-abdominals, rectus-femoris` | 2 | ISOLATED_ONLY |
| `Cardio In And Outs` | `Gluteus Medius` | `gluteus-medius` | 1 | ISOLATED_ONLY |
| `Cardio In In Out Out Shuffle` | `Gluteus Medius` | `gluteus-medius` | 1 | ISOLATED_ONLY |
| `Cardio Jumping Jacks` | `Gluteus Medius; Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, gluteus-medius, lateral-deltoid` | 3 | ISOLATED_ONLY |
| `Cardio Karaoke` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Knee Taps` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Lateral Quick Feet` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Lateral Shuffle` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Long Jump` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Long Jump Shuffle Back` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Quick Feet` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Seal Jacks` | `Gluteus Medius` | `gluteus-medius` | 1 | ISOLATED_ONLY |
| `Cardio Shuttle Sprint` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Single Leg Forward Hop` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Single Leg Lateral Hop` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Skater` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Skater To Single Leg Burpee` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Cardio Ski Erg` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Sprint In Place` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Step Out Jacks` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cardio Three Step Heismans` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cat Pose` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Cervical Extension Band` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cervical Extension Banded Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cervical Extension Eccentric Band` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cervical Extension Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Chair Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Chest Stretch Variation Four` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Chest Stretch Variation One` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Chest Stretch Variation Three` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Chest Stretch Variation Two` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Child Pose Arms Extended` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Child Pose Arms Extended Left Right` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Child Pose Arms On Side` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Child Pose Elbows On Block` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Clamshells 1 Side Lying` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Clamshells 2 Side Lying` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Clamshells 3 Internal External Rotations Side Lying` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Clamshells 4 Side Lying Resisted` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Clock Taps` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cobra Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cobra Stretch 1` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Cobra Stretch 2` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Core Stability 1 Crosslateral Limb Raise 4Pt Position` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Core Stability 2 Opposite Shoulder Tap 4Pt Position` | `Anterior Deltoid; Obliques` | `anterior-deltoid, obliques` | 2 | ISOLATED_ONLY |
| `Core Stability 4 Crosslateral Limb Raise Push Up Position` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Core Stability 5 Crosslateral Limb Raise Into Knee Elbow Tuck Push Up Position` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Core Stability Regression Crosslateral Limb Raise Push Up Position` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Corpse Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Crescent Moon Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Crescent Moon Pose Quad Stretch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Crescent Moon Pose Quad Stretch With Block` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Criss Cross Bow Tie Pose` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Crosslateral Core Stabilisation Unilateral Load Kettlebell` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Dead Bug` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dead Bugs Cross Lateral` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Dead Bugs Same Side` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Dead Hang` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Depth Jump` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Diamond Push Ups` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dorsal Flexion Hold` | `Tibialis` | `tibialis` | 1 | ISOLATED_ONLY |
| `Double Pigeon Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Downward Dog` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Downward Dog Toe To Heel` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Downward Dog With Fingers Facing Feet` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Alternating Arnold Press` | `Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Dumbbell Alternating Single Arm Press` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Dumbbell Alternating Single Arm Thruster` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Dumbbell Clean And Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Cuban Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Elevated Pushup` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Dumbbell Feet Elevated Figure Four Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Feet Elevated Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Feet Elevated Single Leg Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Feet Elevated Staggered Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Figure Four Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Front Rack Step Up` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Goblet Side Step Up` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Goblet Step Up` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Hang Clean And Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Internal Rotation` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Long Lever Russian Twist` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Dumbbell Overhead Side Bend` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Dumbbell Pullover` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Pullover Eccentrics` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Quad Stomp` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Seated Single Arm Arnold Press` | `Anterior Deltoid; Lateral Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Dumbbell Seated Tibialis Raise` | `Tibialis` | `tibialis` | 1 | ISOLATED_ONLY |
| `Dumbbell Seated Y Press` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Dumbbell Service Exercise` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Side Step Up` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Single Arm Arnold Press` | `Anterior Deltoid; Lateral Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Dumbbell Single Arm Clean And Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Single Arm Front Rack Step Up` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Single Arm Hang Clean And Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Single Arm Press` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Dumbbell Single Arm Push Press` | `Anterior Deltoid; Lateral Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Dumbbell Single Arm Shoulder Extension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Single Arm Step Up` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Single Arm Thruster` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Dumbbell Single Leg Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Staggered Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Staggered Waiters Bow` | `Gluteus Maximus; Lateral Hamstrings` | `gluteus-maximus, lateral-hamstrings` | 2 | ISOLATED_ONLY |
| `Dumbbell Standing Hip Abduction` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Standing Tibialis Raise` | `Tibialis` | `tibialis` | 1 | ISOLATED_ONLY |
| `Dumbbell Step Up` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Superman` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Superman Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Tricep Guillotine Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Waiters Bow` | `Gluteus Maximus; Lateral Hamstrings` | `gluteus-maximus, lateral-hamstrings` | 2 | ISOLATED_ONLY |
| `Dumbbell Weighted Dip` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Dumbbell Wrist Supinations Pronations` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Dumbbell Y Press` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Eagle Arm Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Eagle Arms Chin Into Chest` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Easy Pose Neck Stretch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Easy Seated Twist Pose` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Elbow Extensor Isometric Seated Overhead Dumbbell` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Elbow Extensor Mobilisation Kneeling Lacrosse Ball` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Elevated Pike Press` | `Traps (mid-back); Lateral Deltoid; Anterior Deltoid; Upper Traps` | `anterior-deltoid, lateral-deltoid, traps-(mid-back), upper-traps` | 4 | ISOLATED_ONLY |
| `Elliptical` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Eversions` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Extended side Angle Pose With Block` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `extended-side-angle-pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Femoral Nerve Mobilisation` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Floor Knee Pull Bilateral` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Foam Roller Angel` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Foam Roller Quad Mobilisation` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Forearms Stretch Variation Four` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Forearms Stretch Variation One` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Forearms Stretch Variation Three` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Forearms Stretch Variation Two` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Forward Arm Circle` | `Lateral Deltoid; Anterior Deltoid; Posterior Deltoid` | `anterior-deltoid, lateral-deltoid, posterior-deltoid` | 3 | ISOLATED_ONLY |
| `Gastrocnemius Stretch Bilateral On Box` | `Gastrocnemius` | `gastrocnemius` | 1 | ISOLATED_ONLY |
| `Gastrocnemius Stretch Push Up Position` | `Gastrocnemius` | `gastrocnemius` | 1 | ISOLATED_ONLY |
| `Gastrocnemius Stretch Unilateral On Box` | `Gastrocnemius` | `gastrocnemius` | 1 | ISOLATED_ONLY |
| `Gastrocnemius Stretch Unilateral On Wall` | `Gastrocnemius` | `gastrocnemius` | 1 | ISOLATED_ONLY |
| `Gate Pose Rounding Spine Looking Up` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Gate Pose Variation Arm Extended on Side` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glute Bridge Eccentric Unilateral` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glute Bridge Isometric Hold Single Alternate` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glute Hip Rotator Stretch 1 Seated` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glute Hip Rotator Stretch 2 Seated` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glute Hip Rotator Stretch 3 Seated` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glute Hip Rotator Stretch Supine` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glute Piriformis Mobilisation 1 Floor Seated Lacrosse Ball` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glute Stretch Knee Pull Dynamic Standing` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glute Stretch Static Unilateral` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Gluteator` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glutes Stretch Variation One` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glutes Stretch Variation Three` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Glutes Stretch Variation Two` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Half Lotus` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Half Monkey Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Half Neck Rolls` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Bridge Isometric Open Angle` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Bridge With Elevated Legs Box Bilateral` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Bridge With Elevated Legs Box Unilateral` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Mobilisation Seated Lacrosse Ball` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Stretch Dynamic Standing Bilateral` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Stretch Dynamic Supine Alternating` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Stretch Seated Single Leg` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Stretch Seated Single Leg Isometric` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Stretch Static Standing Single Leg` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Stretch Supine Dynamic Band` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Stretch Supine Glide` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstring Stretch Supine Static` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstrings Stretch Variation Four` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstrings Stretch Variation One` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstrings Stretch Variation Three` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hamstrings Stretch Variation Two` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Happy Baby` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Headstand` | `Anterior Deltoid; Lateral Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Hip Extension 4Pt Position Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hip Extension External Rotation 4Pt Position` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hip Extension External Rotation Pulses 4Pt Position` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hip Extension Into Side Flexion` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Hip Openers` | `Anterior Deltoid; Posterior Deltoid; Chest` | `anterior-deltoid, chest, posterior-deltoid` | 3 | ISOLATED_ONLY |
| `I Into W` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `I's Prone` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Inchworm` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Infinity Loop Standing Hip Mobility` | `Rectus Femoris` | `rectus-femoris` | 1 | ISOLATED_ONLY |
| `Intrascapular Muscle Contraction` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Jump Into Single Leg Landing` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Jump Off Box Single Leg Landing` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Jump On And Off Box` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Jump Rope` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Alternating Single Arm Thruster` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Kettlebell Alternating Swing` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Chest Press (Single)` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Kettlebell Clean And Jerk` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Clean And Press` | `Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Kettlebell Hang Clean And Jerk` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Hang Clean And Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Hollow Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Kneel To Stand Shoulder Flexion Bent Elbow Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Push Press` | `Anterior Deltoid; Lateral Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Kettlebell Quad Stomp` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Shoulder Flexion Bent Elbow Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Single Arm Clean And Jerk` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Single Arm Clean And Press` | `Anterior Deltoid; Lateral Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Kettlebell Single Arm Hang Clean And Jerk` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Single Arm Press` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Kettlebell Single Arm Push Press` | `Anterior Deltoid; Lateral Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Kettlebell Single Arm Shoulder Extension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Single Arm Snatch` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Kettlebell Single Arm Step Up Balance` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Single Arm Thruster` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Kettlebell Single Leg Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Snatch (Double)` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Kettlebell Staggered Waiters Bow` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Step Up Double` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Superman` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Superman Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Tate Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Thruster` | `Anterior Deltoid; Lateral Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Kettlebell Waiters Bow` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Walking Shoulder Flexion Bent Elbow Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kettlebell Walkover Pushup` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Kettlebell Wrist Extension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Kickbacks` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Knee Extension Seated Partial` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Knee Pull And Lumbar Rotation` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Kneeling Quad Stretch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Landmine Alternating Single Arm Press` | `Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Landmine Glute Kick Back` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Landmine Hollow Hold` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Landmine Kneeling Twist` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Landmine Oblique Twist` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Landmine Rotational Lift To Press` | `Anterior Deltoid; Lateral Deltoid; Obliques` | `anterior-deltoid, lateral-deltoid, obliques` | 3 | ISOLATED_ONLY |
| `Landmine Russian Twist` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Landmine Single Arm Chest Press` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Landmine Single Arm Push Press` | `Anterior Deltoid; Lateral Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Landmine Single Leg Glute Bridge` | `Gluteus Maximus` | `gluteus-maximus` | 1 | ISOLATED_ONLY |
| `Landmine Snatch` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Landmine Split Jerk` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Landmine Stationary Twist` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Landmine Thruster` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Lat And Lateral Line Stretch` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Lat And Shoulder External Rotation Stretch 1 Kneeling Dowel` | `Anterior Deltoid; Posterior Deltoid` | `anterior-deltoid, posterior-deltoid` | 2 | ISOLATED_ONLY |
| `Lat And Shoulder External Rotation Stretch 2 Kneeling Dowel` | `Anterior Deltoid; Posterior Deltoid` | `anterior-deltoid, posterior-deltoid` | 2 | ISOLATED_ONLY |
| `Lat And Shoulder External Rotation Stretch 3 Kneeling Dowel` | `Anterior Deltoid; Posterior Deltoid` | `anterior-deltoid, posterior-deltoid` | 2 | ISOLATED_ONLY |
| `Lat Mobilisation Floor Foam Roller` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lats Stretch Variation One` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lats Stretch Variation Three` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lats Stretch Variation Two` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Laying Cervical Extensor Mobilisation Peanut Tool` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Laying Cervical Flexion 2` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Laying Cervical Flexion Isometric` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Laying Chin Tucks` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Laying Levator Scapulae Mobilisation Massage Ball` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Laying Ts` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Leg Lowers` | `Lower Abdominals` | `lower-abdominals` | 1 | ISOLATED_ONLY |
| `Lord Of The Dance` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lower Back Extensions 2` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lower Back Extensions 3` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lower Back Extensions 4` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lower back Stretch Variation Four` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lower back Stretch Variation One` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lower back Stretch Variation Three` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lower back Stretch Variation Two` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lumbar Extensor Mobilisation Supine Bent Knees Peanut Tool` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lumbar Rotation 1` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lumbar Rotation 2` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lumbar Rotation 3` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lumbar Rotation 4` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Lumbar Rotation 5` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Machine 45 Degree Back Extension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Machine Assisted Parallel Bar Dips` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Machine Back Extension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Machine Dips` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Machine Glute Kickback` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Machine Hip Abduction` | `Gluteus Medius` | `gluteus-medius` | 1 | ISOLATED_ONLY |
| `Machine Hip Adduction` | `Inner Thigh` | `inner-thigh` | 1 | ISOLATED_ONLY |
| `Machine Hip And Glute Abduction` | `Gluteus Medius` | `gluteus-medius` | 1 | ISOLATED_ONLY |
| `Machine Hip And Glute Adduction` | `Inner Thigh` | `inner-thigh` | 1 | ISOLATED_ONLY |
| `Machine Hip And Glute Kickback` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Machine Pullover` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Machine Reverse Hyperextension` | `Gluteus Maximus; Lateral Hamstrings` | `gluteus-maximus, lateral-hamstrings` | 2 | ISOLATED_ONLY |
| `Medicine Ball Chest Press Partner Toss` | `Chest; Mid and Lower Chest; Long Head Tricep; Lateral Head Triceps; Anterior Deltoid` | `anterior-deltoid, chest, lateral-head-triceps, long-head-tricep, mid-and-lower-chest` | 5 | ISOLATED_ONLY |
| `Medicine Ball Chest Press Slam` | `Chest; Mid and Lower Chest; Long Head Tricep; Lateral Head Triceps; Medial Head Triceps; Anterior Deltoid` | `anterior-deltoid, chest, lateral-head-triceps, long-head-tricep, medial-head-triceps, mid-and-lower-chest` | 6 | ISOLATED_ONLY |
| `Medicine Ball Chest Press Toss` | `Chest; Anterior Deltoid` | `anterior-deltoid, chest` | 2 | ISOLATED_ONLY |
| `Medicine Ball Clean And Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Medicine Ball Clean And Press Slam` | `Inner Quadriceps; Outer Quadricep; Anterior Deltoid` | `anterior-deltoid, inner-quadriceps, outer-quadricep` | 3 | ISOLATED_ONLY |
| `Medicine Ball Dead Bug` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Medicine Ball Half Kneeling Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Medicine Ball Halo` | `Lateral Deltoid; Anterior Deltoid; Posterior Deltoid` | `anterior-deltoid, lateral-deltoid, posterior-deltoid` | 3 | ISOLATED_ONLY |
| `Medicine Ball Hang Clean And Press` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Medicine Ball Hip Abduction` | `Gluteus Medius` | `gluteus-medius` | 1 | ISOLATED_ONLY |
| `Medicine Ball Hollow Hold` | `Lower Abdominals; Upper Abdominals` | `lower-abdominals, upper-abdominals` | 2 | ISOLATED_ONLY |
| `Medicine Ball Kneeling Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Medicine Ball Partner Side Toss` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Medicine Ball Partner Situp Toss` | `Upper Abdominals` | `upper-abdominals` | 1 | ISOLATED_ONLY |
| `Medicine Ball Press Jack` | `Gluteus Medius` | `gluteus-medius` | 1 | ISOLATED_ONLY |
| `Medicine Ball Pushup` | `Chest; Mid and Lower Chest` | `chest, mid-and-lower-chest` | 2 | ISOLATED_ONLY |
| `Medicine Ball Rainbow Slam` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Medicine Ball Russian Twist` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Medicine Ball Self Toss` | `Inner Quadriceps; Outer Quadricep; Gluteus Maximus; Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, gluteus-maximus, inner-quadriceps, lateral-deltoid, outer-quadricep` | 5 | ISOLATED_ONLY |
| `Medicine Ball Slam` | `Upper Abdominals` | `upper-abdominals` | 1 | ISOLATED_ONLY |
| `Medicine Ball Thruster` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Medicine Ball Walkover Pushup` | `Chest; Mid and Lower Chest; Anterior Deltoid` | `anterior-deltoid, chest, mid-and-lower-chest` | 3 | ISOLATED_ONLY |
| `Medicine Ball Wall Ball` | `Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Medicine Ball Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Medicine Ball Wood Chopper Toss` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Monkey Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Mountain` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Neutral Chest Press` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Oblique Jackknife` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `One Arm Cow Face Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Parallel Bar Dips` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Partner Lower Back Extensions` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Pigeon Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Plate Car Driver` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Plate Clean` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Plate Clean And Press` | `Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Plate Deficit Pushup` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Plate Glute Bridge to Chest Press` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Plate Halo` | `Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Plate Pinch Grip Side Bend` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Plate Reach` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Plate Staggered Waiters Bow` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Plate Standing Twist` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Plate Superman` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Plate Superman Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Plate Thruster` | `Anterior Deltoid; Lateral Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Plate Waiters Bow` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Plate Weighted Dead Hang` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Plate Weighted Dip` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Plate Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Pole Rotation` | `Lateral Deltoid; Anterior Deltoid; Posterior Deltoid` | `anterior-deltoid, lateral-deltoid, posterior-deltoid` | 3 | ISOLATED_ONLY |
| `Prayer Stretch 1` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Prayer Stretch 2 Roller` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Prayer Stretch Side Bend` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Puppy Pose` | `Posterior Deltoid` | `posterior-deltoid` | 1 | ISOLATED_ONLY |
| `Pushup Position Shoulder Clock` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Pyramid Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Pyramid Pose Blocks` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Pyramid Prayer` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `QL Mobilisation Floor Foam Roller` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Quads Stretch Variation Four` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Quads Stretch Variation One` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Quads Stretch Variation Three` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Quads Stretch Variation Two` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Reach And Catch` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Reclining Pigeon Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Resisted Radial Deviation` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Restful Cow Face Pose Legs` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Reverse Prayer` | `Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Revolved Head To Knee` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Revolved Side Angle Pose With Prayer Hands` | `Traps (mid-back); Obliques` | `obliques, traps-(mid-back)` | 2 | ISOLATED_ONLY |
| `Revolved Side Angle Pose With Prayer Hands Beginner` | `Traps (mid-back); Obliques` | `obliques, traps-(mid-back)` | 2 | ISOLATED_ONLY |
| `Ring Standing Archer Pushup` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Ring Standing Pushup` | `Anterior Deltoid; Chest` | `anterior-deltoid, chest` | 2 | ISOLATED_ONLY |
| `Ring Standing Roll Out` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Rotator Cuff External Rotations 1` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Rotator Cuff External Rotations 2` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Rotator Cuff External Rotations 3` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Rotator Cuff Mobilisation Lacrosse Ball` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Scapular Depression` | `Lower Traps` | `lower-traps` | 1 | ISOLATED_ONLY |
| `Scapular Elevation` | `Upper Traps` | `upper-traps` | 1 | ISOLATED_ONLY |
| `Scapular Protraction` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Scapular Retraction` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Scorpion Twist Pose` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Seated Arm Stretch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Box Jump` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Cervical Flexion Isometric` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Cervical Rotation Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Cervical Side Flexion Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Doming` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Forward Bend` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Hip Flexion Hold` | `Rectus Femoris` | `rectus-femoris` | 1 | ISOLATED_ONLY |
| `Seated Lateral Line Stretch` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Seated Manual Cervical Extensor Mobilisation` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Median Nerve Slider` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Median Nerve Tensioner` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Plantar Flexions` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Quad Stretch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Radial Nerve Slider` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Radial Nerve Tensioner` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Shoulder Abduction` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Side Bend Pose` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Seated Tibialis Raise` | `Tibialis` | `tibialis` | 1 | ISOLATED_ONLY |
| `Seated Twist` | `Traps (mid-back); Obliques` | `obliques, traps-(mid-back)` | 2 | ISOLATED_ONLY |
| `Seated Ulnar Nerve Slider` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Ulnar Nerve Tensioner` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Upper Trap And Suprispinatus Stretch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Seated Wrist Extensor Stretch` | `Wrist Extensors` | `wrist-extensors` | 1 | ISOLATED_ONLY |
| `Seated Wrist Flexor Stretch` | `Wrist Flexors` | `wrist-flexors` | 1 | ISOLATED_ONLY |
| `Serratus Activation Cross Punch` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Shoulder Abduction Stretch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Shoulder External Internal Rotation` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Shoulder External Rotation Deceleration` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Shoulder Flexion Thoracic Extensions` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Shoulder Flexion Wall Stretch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Shoulders Stretch Variation Four` | `Posterior Deltoid` | `posterior-deltoid` | 1 | ISOLATED_ONLY |
| `Shoulders Stretch Variation One` | `Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Shoulders Stretch Variation Three` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Shoulders Stretch Variation Two` | `Anterior Deltoid; Posterior Deltoid` | `anterior-deltoid, posterior-deltoid` | 2 | ISOLATED_ONLY |
| `Side Lying External Rotator Cuff Stretch` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Side Step On And Off Box` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Single Leg Balance 2` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Single Leg Bosu Ball Balance 2` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Single Leg Box Jump` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Single Leg Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Skydiver` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Slow Tempo Mountain Climber` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Smith Machine Glute Kickback` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Smith Machine Side Bend` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Soleus Stretch` | `Soleus` | `soleus` | 1 | ISOLATED_ONLY |
| `Sphinx Pose` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Stability Ball Atomic Push Up` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Stability Ball Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Stability Ball Knee Tuck` | `Lower Abdominals` | `lower-abdominals` | 1 | ISOLATED_ONLY |
| `Stability Ball Pike` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Stability Ball Push Up` | `Chest; Anterior Deltoid` | `anterior-deltoid, chest` | 2 | ISOLATED_ONLY |
| `Stability Ball Reverse Hyperextension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Stability Ball Stir The Pot` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Stability Ball Straight Leg Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Stability Ball V Up Pass` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Stability Ball Windshield Wiper` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Doming` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Forward Bend` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Forward Bend Blocks` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Inversions Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Mini-Band Hip Flexion` | `Rectus Femoris` | `rectus-femoris` | 1 | ISOLATED_ONLY |
| `Standing Neck Extensions` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Neck Flexions` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Neck Mobility Circumductions` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Neck Rotations` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Neck Side Flexions` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Shoulder Abduction` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Shoulder Flexion Mobility` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Standing Tibialis Raise` | `Tibialis` | `tibialis` | 1 | ISOLATED_ONLY |
| `Stationary Bike` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Supermans` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Supine Twist Lying` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Supported Matsyasana Pose` | `Chest; Traps (mid-back)` | `chest, traps-(mid-back)` | 2 | ISOLATED_ONLY |
| `Swipe Around` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Table Top Pose Variation 1` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Table Top Pose Variation 2` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Table Top Pose Variation 3` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Thoracic Extensions Foam Roller` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Thoracic Flexion And Extensions` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Thread The Needle Hip Over Knees` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Tip Toe Walking` | `Gastrocnemius` | `gastrocnemius` | 1 | ISOLATED_ONLY |
| `Toe Tap` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Towel Knee Extension` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Towel Knee Extension Hold` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Traps mid back Stretch Variation One` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Traps mid back Stretch Variation Two` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Traps Stretch Variation One` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Traps Stretch Variation Three` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Traps Stretch Variation Two` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Treadmill Backwards Walk` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Treadmill Jog` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Treadmill Side Shuffle` | `Gluteus Medius` | `gluteus-medius` | 1 | ISOLATED_ONLY |
| `Treadmill Sprint` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Treadmill Walk` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Tree Pose` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Triceps Stretch Variation One` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Triceps Stretch Variation Three` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Triceps Stretch Variation Two` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `TRX Glute Bridge` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Two Arms Cow Face Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Ulnar Deviations` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Urdhva Dhanurasana Wheel Pose` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Vajrasana Variation 1` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Vajrasana Variation 2` | `Traps (mid-back)` | `traps-(mid-back)` | 1 | ISOLATED_ONLY |
| `Vitruvian Arnold Press` | `Lateral Deltoid; Anterior Deltoid` | `anterior-deltoid, lateral-deltoid` | 2 | ISOLATED_ONLY |
| `Vitruvian Kneeling Wood Chopper` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Vitruvian Push Up` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Vitruvian Side Bend` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Vitruvian Windmill` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Walk Your Downward Dog` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Wall Angels` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Wall Sit` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Wall Supported Dorsal Flexion` | `Tibialis` | `tibialis` | 1 | ISOLATED_ONLY |
| `Warrior One` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Warrior Three` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Warrior Two` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Weighted Diamond Push Ups` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Weighted Knee Push Ups` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Weighted Push Ups` | `Chest; Anterior Deltoid` | `anterior-deltoid, chest` | 2 | ISOLATED_ONLY |
| `Weighted Wall Sit` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Wide Legged Forward Fall` | `Anterior Deltoid` | `anterior-deltoid` | 1 | ISOLATED_ONLY |
| `Wide Legged Standing Forward Bend Holding Heels` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |
| `Wild Thing Pose` | `Obliques` | `obliques` | 1 | ISOLATED_ONLY |
| `Wrist Extensor Kneeling Hold` | `Wrist Extensors` | `wrist-extensors` | 1 | ISOLATED_ONLY |
| `Wrist Extensor Mobilisation` | `Wrist Extensors` | `wrist-extensors` | 1 | ISOLATED_ONLY |
| `Yogi Arm Clock` | `Chest` | `chest` | 1 | ISOLATED_ONLY |
| `Ys` | `(blank/null)` | `(blank/null)` | 0 | EXCLUDE_EMPTY |

## Phase 0 notes

- The live DB contains blank P/S/T rows with no isolated data; those remain diagnostic-only even under `isolated_only` because there is no source attribution to distribute.
- `exercise_isolated_muscles` and the legacy CSV column currently agree on the normalized isolated-token universe; Phase 1 should still prefer the mapping table and use CSV only as fallback.
- `splenius` and `sternocleidomastoid` are recorded as Basic Neck decisions, but Advanced has no neck slider today; Phase 1 should keep these diagnostic in Advanced mode unless the product adds a neck splitter.
