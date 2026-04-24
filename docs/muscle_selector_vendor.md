# Muscle Selector Vendor Integration

This document describes how the MuscleSelector component integrates vendor SVG assets from [react-body-highlighter](https://github.com/giavinh79/react-body-highlighter).

## Source Attribution

- **Package**: `react-body-highlighter` v2.0.5 (npm)
- **Repository**: https://github.com/giavinh79/react-body-highlighter
- **License**: MIT
- **Original SVG Source**: The polygon data originated from [react-native-body-highlighter](https://github.com/HichamELBSI/react-native-body-highlighter)

The vendor files are located at:
```
static/vendor/react-body-highlighter/
├── ATTRIBUTION.md       # This file
├── LICENSE             # MIT License
├── body_anterior.svg   # Front view body diagram
└── body_posterior.svg  # Back view body diagram
```

## Mapping Architecture

The muscle selector uses a three-layer mapping system:

```
Vendor SVG Slugs  →  Canonical Keys  →  Backend Names
     (raw)            (internal)         (API)
```

### Layer 1: Vendor SVG Slugs

These are the `data-muscle` attribute values in the vendor SVGs. They come directly from react-body-highlighter:

**Anterior (Front) View:**
| Vendor Slug | Description |
|-------------|-------------|
| `head` | Head/face (not selectable) |
| `neck` | Neck muscles |
| `front-deltoids` | Front shoulder |
| `chest` | Pectorals |
| `biceps` | Front upper arm |
| `triceps` | Back upper arm |
| `abs` | Abdominals |
| `obliques` | Side core |
| `forearm` | Lower arm |
| `abductors` | Inner thigh (misnamed in upstream) |
| `quadriceps` | Front thigh |
| `knees` | Knee area (not selectable) |
| `calves` | Lower leg |

**Posterior (Back) View:**
| Vendor Slug | Description |
|-------------|-------------|
| `head` | Back of head (not selectable) |
| `trapezius` | Upper back/neck |
| `back-deltoids` | Rear shoulder |
| `upper-back` | Mid back |
| `triceps` | Back upper arm |
| `lower-back` | Lower back |
| `forearm` | Lower arm |
| `gluteal` | Buttocks |
| `abductor` | Hip abductors |
| `hamstring` | Back thigh |
| `knees` | Back of knee (not selectable) |
| `calves` | Lower leg |
| `left-soleus` | Left calf (deep) |
| `right-soleus` | Right calf (deep) |

### Layer 2: Canonical Keys

Internal normalized keys used throughout the application:

| Canonical Key | Vendor Slug(s) | View |
|---------------|----------------|------|
| `neck` | `neck` | Front |
| `front-shoulders` | `front-deltoids` | Front |
| `chest` | `chest` | Front |
| `biceps` | `biceps` | Front |
| `triceps` | `triceps` | Both |
| `forearms` | `forearm` | Both |
| `abdominals` | `abs` | Front |
| `obliques` | `obliques` | Front |
| `adductors` | `abductors` | Front |
| `quads` | `quadriceps` | Front |
| `calves` | `calves`, `left-soleus`, `right-soleus` | Both |
| `traps` | `trapezius` | Back |
| `rear-shoulders` | `back-deltoids` | Back |
| `upper-back` | `upper-back` | Back |
| `lowerback` | `lower-back` | Back |
| `glutes` | `gluteal` | Back |
| `hip-abductors` | `abductor` | Back |
| `hamstrings` | `hamstring` | Back |

**Non-selectable regions:**
- `head` → `null` (displayed but not clickable)
- `knees` → `null` (displayed but not clickable)

### Layer 3: Backend Names

Final mapping to strings expected by the backend API:

| Canonical Key | Backend Name |
|---------------|--------------|
| `front-shoulders` | `Shoulders` |
| `rear-shoulders` | `Shoulders` |
| `chest` | `Chest` |
| `biceps` | `Biceps` |
| `triceps` | `Triceps` |
| `forearms` | `Forearms` |
| `abdominals` | `Abs` |
| `obliques` | `Obliques` |
| `quads` | `Quads` |
| `adductors` | `Adductors` |
| `neck` | `Neck` |
| `calves` | `Calves` |
| `traps` | `Traps` |
| `upper-back` | `Upper Back` |
| `lats` | `Lats` |
| `lowerback` | `Lower Back` |
| `glutes` | `Glutes` |
| `hip-abductors` | `Glutes` |
| `hamstrings` | `Hamstrings` |

## Simple vs Advanced Mode

### Simple Mode (Default)

Highlights entire muscle groups. The SVG shows the full region.

**Available Canonical Keys:**
- Front: `neck`, `front-shoulders`, `chest`, `biceps`, `triceps`, `forearms`, `abdominals`, `obliques`, `adductors`, `quads`, `calves`
- Back: `traps`, `rear-shoulders`, `upper-back`, `lats`, `triceps`, `lowerback`, `forearms`, `glutes`, `hip-abductors`, `hamstrings`, `calves`

### Advanced Mode

Allows selection of the same muscle groups (vendor SVGs don't have sub-regions), but prepares the system for future detailed SVGs. The legend shows more specific options when available.

**Note:** The vendor SVGs don't include sub-muscle regions. In Advanced mode, clicking a muscle still selects the entire group, but the UI indicates advanced mode is active.

## Bilateral Synchronization

Both left and right sides of bilateral muscles (biceps, triceps, quads, etc.) share the same `data-muscle` attribute. When the user:
- Hovers over either side → both sides highlight
- Clicks either side → both sides select/deselect
- Uses the legend → both sides respond

This is handled by the `handleMuscleHover()` and `toggleMuscle()` methods in `MuscleSelector`.

## SVG Coordinate System

The vendor SVGs use:
- **Anterior**: `viewBox="0 0 100 200"` 
- **Posterior**: `viewBox="0 0 100 220"` (slightly taller for soleus)

All coordinates are relative to this viewBox. The polygons are rendered as `<polygon points="...">` elements.

## CSS Integration

The SVGs include inline styles via `<defs><style>`, but these are overridden by the main CSS file:

```css
/* Override vendor styles */
.muscle-region {
    fill: rgba(52, 152, 219, 0.18);
    stroke: rgba(52, 152, 219, 0.35);
    ...
}
```

See `static/css/pages-workout-plan.css` for the current bundled style definitions.

## Adding New Muscle Regions

To add a new muscle region:

1. **Add polygon to SVG:**
   ```xml
   <polygon class="muscle-region" data-muscle="new-slug"
     points="x1,y1 x2,y2 x3,y3 ..."/>
   ```

2. **Add to mapping in JS:**
   ```javascript
   const VENDOR_SLUG_TO_CANONICAL = {
       // ...
       'new-slug': 'new-canonical-key',
   };
   ```

3. **Add label:**
   ```javascript
   const MUSCLE_LABELS = {
       // ...
       'new-canonical-key': 'Display Name',
   };
   ```

4. **Add backend mapping:**
   ```javascript
   const MUSCLE_TO_BACKEND = {
       // ...
       'new-canonical-key': 'Backend Name',
   };
   ```

5. **Add to side list:**
   ```javascript
   const MUSCLES_BY_SIDE = {
       front: [..., 'new-canonical-key'],
       // or
       back: [..., 'new-canonical-key'],
   };
   ```

## Testing

The mapping can be validated by checking:

1. All vendor slugs in SVG have a mapping in `VENDOR_SLUG_TO_CANONICAL`
2. All canonical keys have entries in `MUSCLE_LABELS` and `MUSCLE_TO_BACKEND`
3. All canonical keys appear in at least one `MUSCLES_BY_SIDE` array

A validation test is included in `tests/test_muscle_selector_mapping.py`.

## Troubleshooting

**Problem:** Muscle doesn't highlight on hover
- Check if `data-muscle` attribute exists on the polygon
- Check if the slug is mapped in `VENDOR_SLUG_TO_CANONICAL`
- Check browser console for "Unknown vendor slug" warnings

**Problem:** Clicking a muscle does nothing
- The region may be marked as non-selectable (`null` mapping)
- Check if the `.non-selectable` class is applied

**Problem:** Both sides don't highlight together
- Ensure both left and right polygons have the same `data-muscle` value
- The selector finds all elements with matching `data-canonicalMuscle`
