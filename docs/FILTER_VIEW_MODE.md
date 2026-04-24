# Filter View Mode (Simple/Advanced)

## Overview

This feature adds a global toggle that switches between **Simple** and **Advanced** muscle naming throughout the application. The toggle affects:

- Filter dropdowns (Primary, Secondary, Tertiary Muscle Group, Advanced Isolated Muscles)
- Workout Plan Table columns (Primary Muscle, Secondary Muscle, Tertiary Muscle, Isolated Muscles)
- Weekly Summary page
- Session Summary page

## User Experience

### Simple Mode (Default)
User-friendly muscle group names for newcomers:

**Front Body:**
- front-shoulders → Front Shoulders
- chest → Chest
- biceps → Biceps
- forearms → Forearms
- abdominals → Abdominals
- obliques → Obliques
- quads → Quads

**Rear Body:**
- traps → Traps
- traps-middle → Middle Traps
- rear-shoulders → Rear Shoulders
- middle-shoulders → Middle Shoulders
- triceps → Triceps
- lats → Lats
- lower-back → Lower Back
- glutes → Glutes
- hamstrings → Hamstrings
- calves → Calves
- upper-back → Upper Back

### Advanced Mode
Anatomically precise muscle names for experienced users:

**Front Body:**
- anterior-deltoid → Anterior Deltoid
- upper-pectoralis → Upper Pectoralis
- long-head-bicep → Long Head Bicep
- short-head-bicep → Short Head Bicep
- wrist-extensors → Wrist Extensors
- wrist-flexors → Wrist Flexors
- upper-abdominals → Upper Abdominals
- lower-abdominals → Lower Abdominals
- obliques → Obliques
- inner-thigh → Inner Thigh
- rectus-femoris → Rectus Femoris
- outer-quadricep → Outer Quadricep

**Rear Body:**
- upper-trapezius → Upper Trapezius
- lower-trapezius → Lower Trapezius
- lateral-deltoid → Lateral Deltoid
- posterior-deltoid → Posterior Deltoid
- lateral-head-triceps → Lateral Head Triceps
- long-head-triceps → Long Head Triceps
- medial-head-triceps → Medial Head Triceps
- gluteus-maximus → Gluteus Maximus
- gluteus-medius → Gluteus Medius
- lateral-hamstrings → Lateral Hamstrings
- medial-hamstrings → Medial Hamstrings
- soleus → Soleus
- gastrocnemius → Gastrocnemius

## Technical Implementation

### Files Modified/Created

| File | Type | Description |
|------|------|-------------|
| `static/js/modules/filter-view-mode.js` | **New** | Core module with mappings and state management |
| `routes/filters.py` | Modified | Backend expansion of simple→DB values |
| `static/js/modules/workout-plan.js` | Modified | Table display transformation |
| `templates/base.html` | Modified | Global script include |
| `templates/workout_plan.html` | Modified | Toggle UI + dropdown population |
| `templates/weekly_summary.html` | Modified | Toggle UI + display transformation |
| `templates/session_summary.html` | Modified | Toggle UI + display transformation |
| `static/css/pages-workout-plan.css` | Modified | Toggle button styling within the workout-plan page bundle |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FilterViewMode Module                     │
│                 (filter-view-mode.js)                        │
├─────────────────────────────────────────────────────────────┤
│  State Management                                            │
│  ├─ getViewMode() → 'simple' | 'advanced'                   │
│  ├─ setViewMode(mode) → saves to localStorage               │
│  └─ toggleViewMode() → switches and saves                   │
├─────────────────────────────────────────────────────────────┤
│  Mappings                                                    │
│  ├─ SIMPLE_MUSCLES: key → {label, side}                     │
│  ├─ ADVANCED_MUSCLES: key → {label, side}                   │
│  ├─ DB_TO_SIMPLE: dbValue → simpleKey                       │
│  ├─ SIMPLE_TO_DB: simpleKey → [dbValues]                    │
│  ├─ SIMPLE_TO_ADVANCED: simpleKey → [advancedKeys]          │
│  └─ ADVANCED_TO_SIMPLE: advancedKey → simpleKey             │
├─────────────────────────────────────────────────────────────┤
│  Transformations                                             │
│  ├─ transformMuscleDisplay(dbValue, mode)                   │
│  ├─ transformIsolatedMuscleDisplay(isolatedValue, mode)     │
│  └─ getMuscleFilterOptions(muscleType, mode)                │
├─────────────────────────────────────────────────────────────┤
│  UI                                                          │
│  ├─ createToggleButton(container)                           │
│  └─ updateToggleUI(wrapper, mode)                           │
└─────────────────────────────────────────────────────────────┘
```

### Backend Filter Logic

When a user filters by a simple muscle key (e.g., "biceps"), the backend expands it:

```python
# Simple mode filter for isolated muscles
"biceps" → ["long-head-bicep", "short-head-bicep"]

# Simple mode filter for primary muscle group  
"glutes" → ["Gluteus Maximus", "Hip-Adductors"]
```

The `filter_exercises_with_expanded_muscles()` function builds SQL with OR conditions:

```sql
WHERE ... AND (
    muscle LIKE '%long-head-bicep%' 
    OR muscle LIKE '%short-head-bicep%'
)
```

### Event Flow

```
User clicks toggle
       ↓
setViewMode(newMode)
       ↓
localStorage.setItem()
       ↓
dispatch 'filterViewModeChanged' event
       ↓
    ┌──┴──────────────────────────┐
    ↓                             ↓
updateMuscleFilterDropdowns()   updateMuscleDisplaysInTable()
    ↓                             ↓
Repopulate <select> options    Update cell.textContent
```

### Storage

- **Key:** `hypertrophy_filter_view_mode`
- **Values:** `'simple'` (default) or `'advanced'`
- **Persistence:** localStorage (survives page reloads)

## CSS Styling

The toggle uses Bootstrap button groups with custom styling:

```css
.filter-view-toggle .btn.btn-primary {
    background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%);
}
```

Dark mode is fully supported with appropriate color adjustments.

## Testing

Existing filter tests pass:
```
tests/test_priority0_filters.py - 17 passed
```

## Usage

1. Navigate to Workout Plan page
2. Look for **Simple | Advanced** toggle in the "Filter Exercises" header
3. Click to switch modes
4. Filter dropdowns and table columns update immediately
5. Setting persists across page navigation and browser sessions
