# Muscle Selector Documentation v2.0

Interactive SVG body diagram component for selecting target muscle groups in the Generate Starter Plan modal.

## Features

- **External SVG files** with anatomically-shaped muscle regions
- **Simple/Advanced view modes** with parent-child muscle group mappings
- **Front/Back tab navigation** to view anterior and posterior body regions
- **Left/right side synchronization** - clicking either side selects both
- **Multi-select support** with visual feedback (hover, selected, partial)
- **Tooltip on hover** showing muscle name (and key in debug mode)
- **Debug mode** for development/testing
- **"None selected" = target all muscles** for plan generation

## File Locations

| File | Purpose |
|------|---------|
| [static/js/modules/muscle-selector.js](../static/js/modules/muscle-selector.js) | Main JavaScript module |
| [static/css/pages-workout-plan.css](../static/css/pages-workout-plan.css) | Bundled styling for the component |
| [static/vendor/workout-cool/body_anterior.svg](../static/vendor/workout-cool/body_anterior.svg) | Front view, **Simple** mode (workout-cool art) |
| [static/vendor/workout-cool/body_posterior.svg](../static/vendor/workout-cool/body_posterior.svg) | Back view, **Simple** mode (workout-cool art) |
| [static/vendor/react-body-highlighter/body_anterior.svg](../static/vendor/react-body-highlighter/body_anterior.svg) | Front view, **Advanced** mode |
| [static/vendor/react-body-highlighter/body_posterior.svg](../static/vendor/react-body-highlighter/body_posterior.svg) | Back view, **Advanced** mode |
| [scripts/build_workout_cool_svgs.py](../scripts/build_workout_cool_svgs.py) | Builds the workout-cool SVGs from upstream TSX at the pinned SHA |
| [templates/workout_plan.html](../templates/workout_plan.html) | Integration in Generate Plan modal |
| [static/js/app.js](../static/js/app.js) | API integration (generateStarterPlan function) |

See [muscle_selector_vendor.md](muscle_selector_vendor.md) for vendor SVG attribution and mapping details.

### View-mode SVG variants

Simple mode and Advanced mode load different SVG art:

- **Simple mode** uses workout-cool's anatomically-styled silhouette
  ([NOTICE](../static/vendor/workout-cool/NOTICE.md)). It is shipped
  pre-canonicalized — every `.muscle-region` carries
  `data-canonical-muscles="<key>[,<key2>,...]"` directly, so no runtime
  vendor-slug translation is needed for this variant. The posterior
  `BACK` region is intentionally multi-key
  (`lats,upper-back,lowerback`) because workout-cool's art does not
  separate those three.
- **Advanced mode** stays on react-body-highlighter, whose regions
  carry vendor `data-muscle="<slug>"` attributes that
  `mapVendorSlugsToCanonical()` translates at SVG-load time into
  `data-canonical-muscle` (singular).

`SVG_PATHS[mode][side]` and `getSvgPathForMode(mode, side)` resolve the
right URL; `switchViewMode()` triggers a full SVG reload (not just a
legend re-render) when the user toggles modes. Selection state in
`MuscleSelector.selectedMuscles` is preserved verbatim across the
swap, and `updateAllRegionStates()` re-derives the visual state from it.

### Multi-key region click semantics

`selectedMuscles` always stores **advanced** keys. A region whose
`data-canonical-muscles` lists multiple simple keys (only `BACK` in the
workout-cool variant today) must flatten through `SIMPLE_TO_ADVANCED_MAP`
before any `.has` / `.add` / `.delete`. The helpers that enforce this:

- `getCanonicalKeys(region)` — returns the array of simple keys.
- `flattenToAdvancedChildren(simpleKeys)` — expands every simple key,
  falling through to `[key]` for keys that have no children.
- `regionVisualState(region)` — counts how many of the flattened
  advanced keys are currently selected and returns `'selected'` /
  `'partial'` / `'unselected'`.
- `toggleRegion(region)` — mass-add / mass-remove.

For the workout-cool BACK region, the flattened set is
`['lats', 'rhomboids', 'teres-major', 'teres-minor', 'erector-spinae']`
(5 advanced keys). Selecting only one of them in Advanced mode and
returning to Simple mode renders BACK as `partial`. This case is
guarded by `tests/test_muscle_selector_mapping.py::TestRegionVisualState`
plus the `e2e/workout-plan.spec.ts` "Muscle selector body-map variants"
block.

## Architecture

### SVG File Structure

Each SVG file contains:
- A `<defs>` section with embedded styles
- A `.body-outline` group with the body silhouette
- A `.muscle-regions` group containing individual `<path>` elements

Each muscle path has:
- `class="muscle-region"` for CSS styling
- `id` attribute (e.g., `chest`, `biceps-L`, `biceps-R`)
- `data-muscle` attribute with the muscle key (e.g., `data-muscle="biceps"`)

For bilateral muscles (arms, legs), there are separate left/right paths with the same `data-muscle` value, ensuring both sides highlight/select together.

### Central Configuration (in muscle-selector.js)

```javascript
// Simple → Advanced mapping
SIMPLE_TO_ADVANCED_MAP = {
    'chest': ['upper-pectoralis', 'mid-lower-pectoralis'],
    // ...
}

// Display labels
MUSCLE_LABELS = {
    'chest': 'Chest',
    'upper-pectoralis': 'Upper Chest',
    // ...
}

// Backend API mapping
MUSCLE_TO_BACKEND = {
    'chest': 'Chest',
    'upper-pectoralis': 'Upper Chest',
    // ...
}
```

### Muscle Key Reference

#### Simple View - Front Body
| Key | Display Name |
|-----|--------------|
| `front-shoulders` | Front Shoulders |
| `chest` | Chest |
| `biceps` | Biceps |
| `forearms` | Forearms |
| `abdominals` | Abdominals |
| `obliques` | Obliques |
| `quads` | Quadriceps |
| `calves` | Calves |

#### Simple View - Back Body
| Key | Display Name |
|-----|--------------|
| `traps` | Traps |
| `rear-shoulders` | Rear Shoulders |
| `triceps` | Triceps |
| `traps-middle` | Mid Traps |
| `lats` | Lats |
| `lowerback` | Lower Back |
| `glutes` | Glutes |
| `hamstrings` | Hamstrings |

#### Advanced View - Front Body
| Key | Display Name | Parent (Simple) |
|-----|--------------|-----------------|
| `anterior-deltoid` | Anterior Deltoid | front-shoulders |
| `lateral-deltoid` | Lateral Deltoid | front-shoulders |
| `upper-pectoralis` | Upper Chest | chest |
| `mid-lower-pectoralis` | Mid/Lower Chest | chest |
| `long-head-bicep` | Long Head Bicep | biceps |
| `short-head-bicep` | Short Head Bicep | biceps |
| `wrist-flexors` | Wrist Flexors | forearms |
| `wrist-extensors` | Wrist Extensors | forearms |
| `upper-abdominals` | Upper Abs | abdominals |
| `lower-abdominals` | Lower Abs | abdominals |
| `obliques` | Obliques | obliques |
| `groin` | Groin | - |
| `inner-thigh` | Inner Thigh | - |
| `rectus-femoris` | Rectus Femoris | quads |
| `outer-quadricep` | Outer Quad | quads |
| `inner-quadricep` | Inner Quad | quads |
| `tibialis` | Tibialis | - |
| `gastrocnemius` | Gastrocnemius | calves |
| `soleus` | Soleus | calves |

#### Advanced View - Back Body
| Key | Display Name | Parent (Simple) |
|-----|--------------|-----------------|
| `upper-trapezius` | Upper Trapezius | traps |
| `lateral-deltoid` | Lateral Deltoid | rear-shoulders |
| `posterior-deltoid` | Posterior Deltoid | rear-shoulders |
| `traps-middle` | Mid Traps | traps-middle |
| `lower-trapezius` | Lower Trapezius | traps-middle |
| `lateral-head-triceps` | Lateral Triceps | triceps |
| `long-head-triceps` | Long Head Triceps | triceps |
| `medial-head-triceps` | Medial Triceps | triceps |
| `lats` | Lats | lats |
| `lowerback` | Lower Back | lowerback |
| `gluteus-medius` | Gluteus Medius | glutes |
| `gluteus-maximus` | Gluteus Maximus | glutes |
| `lateral-hamstrings` | Lateral Hamstrings | hamstrings |
| `medial-hamstrings` | Medial Hamstrings | hamstrings |
| `gastrocnemius` | Gastrocnemius | calves |
| `soleus` | Soleus | calves |

## Usage

### JavaScript API

```javascript
// Initialize (with optional debug mode)
const selector = new MuscleSelector('muscle-selector-container', { debug: true });

// Get selected muscle IDs (internal keys)
const ids = selector.getSelectedMuscleIds();
// => ['upper-pectoralis', 'mid-lower-pectoralis', 'biceps']

// Get display names
const names = selector.getSelectedMuscleNames();
// => ['Upper Chest', 'Mid/Lower Chest', 'Biceps']

// Get backend-friendly names (for API)
const backendNames = selector.getSelectedMusclesForBackend();
// => ['Upper Chest', 'Mid Chest', 'Biceps']

// Get current view mode
const mode = selector.getViewMode();
// => 'simple' or 'advanced'

// Set selection programmatically
selector.setSelection(['upper-pectoralis', 'long-head-bicep']);

// Enable/disable debug mode
selector.setDebugMode(true);
```

### Integration with Plan Generator

In `app.js`:

```javascript
// Collect selected muscles
let targetMuscleGroups = [];
if (window.muscleSelector) {
    targetMuscleGroups = window.muscleSelector.getSelectedMusclesForBackend();
}

// Send to API
const response = await fetch('/generate_starter_plan', {
    method: 'POST',
    body: JSON.stringify({
        // ... other params
        target_muscle_groups: targetMuscleGroups.length > 0 ? targetMuscleGroups : null
    })
});
```

## View Modes

### Simple Mode
- Shows broad muscle group regions
- Clicking a region selects ALL its child (advanced) muscles
- Parent shows "selected" if ALL children are selected
- Parent shows "partial" (yellow) if SOME children are selected

### Advanced Mode
- Shows granular muscle regions
- Each muscle is independently selectable
- Selections persist when switching between modes

## Styling

### CSS Custom Properties

```css
/* Body diagram background */
--body-diagram-bg: #e9ecef;

/* Body outline color */
--outline-color: #6c757d;

/* Bootstrap color tokens are used for muscle regions */
```

### State Classes

| Class | Description |
|-------|-------------|
| `.selected` | Muscle is fully selected (green) |
| `.partial` | Some children selected in Simple mode (yellow) |
| `.hover` | Mouse is over the region (blue highlight) |

## Backend Integration

The `target_muscle_groups` parameter flows through:

1. **Frontend** (`app.js`) → `getSelectedMusclesForBackend()` returns array like `['Chest', 'Biceps']`
2. **Route** (`routes/workout_plan.py`) → Passes to `GeneratorConfig`
3. **Plan Generator** (`utils/plan_generator.py`) → Filters exercises in `_is_exercise_allowed()`

```python
# plan_generator.py
if self.config.target_muscle_groups:
    exercise_muscles = set(exercise_obj.get('muscle_groups', []))
    if not exercise_muscles.intersection(set(self.config.target_muscle_groups)):
        return False  # Skip exercises not targeting selected muscles
```

## Testing

Key test scenarios:

1. **Selection toggling**: Click muscle → selected, click again → deselected
2. **View switching**: Select muscles in Simple → switch to Advanced → verify children selected
3. **Mapping integrity**: Ensure all Advanced keys map back to Simple parents
4. **Backend payload**: Verify `getSelectedMusclesForBackend()` returns correct names
5. **Empty selection**: No muscles selected → API receives `null` → targets all muscles
6. **Left/Right sync**: Clicking left bicep should also highlight/select right bicep

## Debug Mode

Enable debug mode to validate regions:

```javascript
// Via constructor
const selector = new MuscleSelector('container', { debug: true });

// Or toggle at runtime
selector.setDebugMode(true);
```

Debug mode features:
- Shows muscle key next to label in legend
- Displays key in tooltip when hovering
- Adds stronger stroke to muscle regions for visibility

## Troubleshooting

### Muscle not highlighting on hover
- Check browser console for JS errors
- Verify SVG path has `data-muscle` attribute (not `data-muscle-id`)
- Ensure the SVG loaded correctly (check Network tab)

### Selection not persisting
- Selections are stored in `selectedMuscles` Set using Advanced keys
- Simple mode derives state from children

### Backend not filtering correctly
- Check that `MUSCLE_TO_BACKEND` mapping returns names the backend recognizes
- Verify `target_muscle_groups` is not empty array (should be `null` if none selected)

### SVG not loading
- Check that SVG files exist in `/static/svg/` directory
- Verify file permissions
- Check browser Network tab for 404 errors
