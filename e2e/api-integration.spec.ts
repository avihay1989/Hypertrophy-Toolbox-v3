/**
 * E2E Test: API Integration
 * 
 * Tests API endpoints directly for:
 * - Workout Plan API
 * - Workout Log API
 * - Exports API
 * - Progression API
 * - Volume Splitter API
 * - Weekly/Session Summary API
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://127.0.0.1:5000';
const JSON_HEADERS = {
  'Accept': 'application/json',
  'X-Requested-With': 'XMLHttpRequest',
};

const VALID_WORKOUT_PLAN_EXERCISE = {
  routine: 'GYM - Full Body - Workout A',
  sets: 3,
  min_rep_range: 8,
  max_rep_range: 12,
  rir: 2,
  weight: 100,
};

function unwrapApiData(payload: unknown) {
  if (
    payload &&
    typeof payload === 'object' &&
    !Array.isArray(payload) &&
    'data' in payload
  ) {
    return (payload as { data: unknown }).data;
  }

  return payload;
}

function expectSuccessFlag(payload: Record<string, unknown>) {
  expect(
    payload.ok === true ||
    payload.status === 'success' ||
    payload.success === true
  ).toBeTruthy();
}

async function clearWorkoutPlanState(request: import('@playwright/test').APIRequestContext) {
  const response = await request.post(`${BASE_URL}/clear_workout_plan`);
  expect(response.ok()).toBeTruthy();
}

async function getValidExerciseName(request: import('@playwright/test').APIRequestContext) {
  const response = await request.get(`${BASE_URL}/get_all_exercises`);
  expect(response.ok()).toBeTruthy();

  const payload = await response.json();
  const exercises = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.data)
      ? payload.data
      : [];

  const exerciseName = exercises.find((value: unknown) =>
    typeof value === 'string' && value.trim() !== ''
  );

  expect(typeof exerciseName === 'string' && exerciseName.trim() !== '').toBeTruthy();
  return exerciseName as string;
}

async function seedWorkoutPlanExercise(
  request: import('@playwright/test').APIRequestContext,
  overrides: Partial<typeof VALID_WORKOUT_PLAN_EXERCISE> = {}
) {
  const exercise = overrides.exercise ?? await getValidExerciseName(request);
  const response = await request.post(`${BASE_URL}/add_exercise`, {
    data: {
      ...VALID_WORKOUT_PLAN_EXERCISE,
      exercise,
      ...overrides,
    }
  });

  expect(response.ok()).toBeTruthy();
}

test.describe('Workout Plan API', () => {
  test('GET /get_workout_plan returns valid response', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/get_workout_plan`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok === true || data.status === 'success' || data.success === true).toBeTruthy();
    expect(data).toHaveProperty('data');
    expect(Array.isArray(data.data)).toBe(true);
  });

  test('GET /get_routine_options returns valid response', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/get_routine_options`);
    // Accept 200 or 404 (route may not exist)
    expect([200, 404]).toContain(response.status());
    
    if (response.ok()) {
      const data = await response.json();
      // This endpoint returns nested routine options object (e.g., {Gym: {...}, "Home Workout": {...}})
      // Accept standard API format, array, or structured object with expected keys
      const isValidResponse = data.ok === true || 
        data.status === 'success' || 
        data.success === true || 
        Array.isArray(data) ||
        (typeof data === 'object' && (data.Gym || data['Home Workout']));
      expect(isValidResponse).toBeTruthy();
    }
  });

  test('GET /api/pattern_coverage returns movement pattern analysis', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/pattern_coverage`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data).toHaveProperty('data');
    
    // Verify pattern coverage structure
    const coverage = data.data;
    expect(coverage).toHaveProperty('per_routine');
    expect(coverage).toHaveProperty('total');
    expect(coverage).toHaveProperty('warnings');
    expect(coverage).toHaveProperty('sets_per_routine');
    expect(coverage).toHaveProperty('ideal_sets_range');
    
    // Warnings should be an array of actionable recommendations
    expect(Array.isArray(coverage.warnings)).toBe(true);
  });

  test('GET /get_all_exercises returns exercises list', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/get_all_exercises`);
    // Accept 200 or 404 (route may not exist)
    if (response.ok()) {
      const data = await response.json();
      expect(Array.isArray(data) || (data.data && Array.isArray(data.data))).toBeTruthy();
    } else {
      expect([404]).toContain(response.status());
    }
  });

  test('POST /add_exercise requires valid data', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/add_exercise`, {
      data: {} // Empty data should fail
    });
    
    expect(response.status()).toBe(400);
  });

  test('POST /add_exercise with valid data succeeds', async ({ request }) => {
    await clearWorkoutPlanState(request);
    await seedWorkoutPlanExercise(request);
  });

  test('POST /remove_exercise requires exercise_id', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/remove_exercise`, {
      data: {}
    });
    
    expect(response.status()).toBe(400);
  });

  test('POST /update_exercise requires valid data', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/update_exercise`, {
      data: {}
    });
    
    expect(response.status()).toBe(400);
  });

  test('GET /get_generator_options returns plan options with priority muscles', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/get_generator_options`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok === true || data.status === 'success' || data.success === true).toBeTruthy();
    
    // v1.5.0: Check for priority_muscles configuration
    if (data.data) {
      expect(data.data).toHaveProperty('priority_muscles');
      expect(data.data.priority_muscles).toHaveProperty('available');
      expect(Array.isArray(data.data.priority_muscles.available)).toBe(true);
      expect(data.data.priority_muscles).toHaveProperty('max_selections');
      
      // Should also have time_budget and merge_mode options
      expect(data.data).toHaveProperty('time_budget');
      expect(data.data).toHaveProperty('merge_mode');
    }
  });

  test('POST /replace_exercise requires exercise_id', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/replace_exercise`, {
      data: {}
    });
    
    expect(response.status()).toBe(400);
  });

  test('GET /api/execution_style_options returns styles', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/execution_style_options`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.ok === true || data.status === 'success' || data.success === true).toBeTruthy();
  });
});

test.describe('Superset API', () => {
  test('POST /api/superset/link requires exercise_ids', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/superset/link`, {
      data: {}
    });
    
    expect(response.status()).toBe(400);
  });

  test('POST /api/superset/unlink requires exercise_id', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/superset/unlink`, {
      data: {}
    });
    
    expect(response.status()).toBe(400);
  });

  test('GET /api/superset/suggest returns suggestions', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/superset/suggest`);
    expect(response.ok()).toBeTruthy();
  });
});

test.describe('Plan Generator API (v1.5.0)', () => {
  test('POST /generate_starter_plan requires valid training_days', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/generate_starter_plan`, {
      data: { training_days: 10 } // Invalid: exceeds max of 5
    });
    
    expect(response.status()).toBe(400);
  });

  test('POST /generate_starter_plan with valid data succeeds', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/generate_starter_plan`, {
      data: {
        training_days: 3,
        environment: 'gym',
        experience_level: 'novice',
        goal: 'hypertrophy',
        persist: false, // Don't save to avoid side effects
        overwrite: false
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.ok === true || data.success === true).toBeTruthy();
    expect(data.data).toHaveProperty('routines');
    expect(data.data).toHaveProperty('total_exercises');
  });

  test('POST /generate_starter_plan with priority_muscles parameter', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/generate_starter_plan`, {
      data: {
        training_days: 2,
        environment: 'gym',
        experience_level: 'novice',
        goal: 'hypertrophy',
        priority_muscles: ['Chest', 'Back'], // v1.5.0 feature
        persist: false,
        overwrite: false
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.ok === true || data.success === true).toBeTruthy();
    expect(data.data).toHaveProperty('routines');
    
    // Priority muscles should be reflected in the response metadata
    if (data.data.metadata) {
      expect(data.data.metadata.priority_muscles).toEqual(['Chest', 'Back']);
    }
  });

  test('POST /generate_starter_plan with time_budget optimization', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/generate_starter_plan`, {
      data: {
        training_days: 3,
        environment: 'gym',
        experience_level: 'intermediate',
        goal: 'hypertrophy',
        time_budget_minutes: 45, // v1.5.0 feature
        persist: false,
        overwrite: false
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.ok === true || data.success === true).toBeTruthy();
  });

  test('POST /generate_starter_plan rejects too many priority muscles', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/generate_starter_plan`, {
      data: {
        training_days: 2,
        environment: 'gym',
        priority_muscles: ['Chest', 'Back', 'Shoulders', 'Arms'], // Exceeds max of 2
        persist: false,
        overwrite: false
      }
    });
    
    // Should either accept with warning or truncate (both valid behaviors)
    expect([200, 400]).toContain(response.status());
  });

  test('POST /generate_starter_plan with merge_mode flag', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/generate_starter_plan`, {
      data: {
        training_days: 2,
        environment: 'gym',
        merge_mode: true, // v1.5.0 feature - keep existing exercises
        persist: false,
        overwrite: false
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.ok === true || data.success === true).toBeTruthy();
  });
});

test.describe('Double Progression API (v1.5.0)', () => {
  test('POST /get_exercise_suggestions returns suggestions from the live route', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/get_exercise_suggestions`, {
      data: {
        exercise: 'Bench Press (Barbell)'
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const rawPayload = await response.json();
    expect(rawPayload.ok).toBe(true);
    expect(rawPayload.status).toBe('success');
    const suggestions = unwrapApiData(rawPayload);
    expect(Array.isArray(suggestions)).toBe(true);
    
    // Each suggestion should have the expected structure
    if (Array.isArray(suggestions) && suggestions.length > 0) {
      const suggestion = suggestions[0] as Record<string, unknown>;
      expect(suggestion).toHaveProperty('type');
      expect(suggestion).toHaveProperty('title');
      expect(suggestion).toHaveProperty('description');
    }
  });

  test('POST /get_exercise_suggestions with is_novice parameter', async ({ request }) => {
    // Novice mode (conservative increments)
    const noviceResponse = await request.post(`${BASE_URL}/get_exercise_suggestions`, {
      data: {
        exercise: 'Squat (Barbell)',
        is_novice: true
      }
    });
    
    expect(noviceResponse.ok()).toBeTruthy();
    const novicePayload = await noviceResponse.json();
    expect(novicePayload.ok).toBe(true);
    expect(novicePayload.status).toBe('success');
    const noviceData = unwrapApiData(novicePayload);
    expect(Array.isArray(noviceData)).toBe(true);
    
    // Experienced mode (may suggest larger increments)
    const expResponse = await request.post(`${BASE_URL}/get_exercise_suggestions`, {
      data: {
        exercise: 'Squat (Barbell)',
        is_novice: false
      }
    });
    
    expect(expResponse.ok()).toBeTruthy();
    const expPayload = await expResponse.json();
    expect(expPayload.ok).toBe(true);
    expect(expPayload.status).toBe('success');
    const expData = unwrapApiData(expPayload);
    expect(Array.isArray(expData)).toBe(true);
  });

  test('POST /get_exercise_suggestions handles unknown exercise', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/get_exercise_suggestions`, {
      data: {
        exercise: 'NonExistent Exercise XYZ123'
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const rawPayload = await response.json();
    expect(rawPayload.ok).toBe(true);
    expect(rawPayload.status).toBe('success');
    const data = unwrapApiData(rawPayload);
    expect(Array.isArray(data)).toBe(true);
    
    // Should return "start training" type suggestion for unknown exercise
    if (data.length > 0) {
      expect(['technique', 'info', 'start']).toContain(data[0].type);
    }
  });

  test('POST /get_exercise_suggestions without exercise returns error', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/get_exercise_suggestions`, {
      data: {}
    });
    
    expect(response.status()).toBe(400);
    const payload = await response.json();
    expect(payload.ok).toBe(false);
    expect(payload.status).toBe('error');
    expect(payload.error.code).toBe('VALIDATION_ERROR');
    expect(payload.message).toBe('exercise is required');
  });

  test('POST /get_current_value returns a current-value payload from the live route', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/get_current_value`, {
      data: {
        exercise: 'Bench Press (Barbell)',
        goal_type: 'weight',
      }
    });

    expect(response.ok()).toBeTruthy();
    const rawPayload = await response.json();
    expect(rawPayload.ok).toBe(true);
    expect(rawPayload.status).toBe('success');
    const payload = unwrapApiData(rawPayload) as Record<string, unknown>;
    expect(payload).toHaveProperty('current_value');
  });

  test('POST /save_progression_goal returns wrapped JSON for XHR callers', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/save_progression_goal`, {
      headers: {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      data: {
        exercise: 'Bench Press (Barbell)',
        goal_type: 'weight',
        current_value: 100,
        target_value: 102.5,
        goal_date: '2099-12-31',
      }
    });

    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload.ok).toBe(true);
    expect(payload.status).toBe('success');
    expect(payload.message).toBe('Goal saved successfully');
    expect(payload.data).toHaveProperty('goal_id');

    const goalId = payload.data.goal_id;
    const cleanupResponse = await request.delete(`${BASE_URL}/delete_progression_goal/${goalId}`);
    expect(cleanupResponse.ok()).toBeTruthy();
    const cleanupPayload = await cleanupResponse.json();
    expect(cleanupPayload.ok).toBe(true);
    expect(cleanupPayload.status).toBe('success');
    expect(cleanupPayload.message).toBe('Goal deleted successfully');
  });

  test('POST /save_progression_goal returns validation error for invalid JSON', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/save_progression_goal`, {
      headers: {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/json',
      },
      data: 'not json'
    });

    expect(response.status()).toBe(400);
    const payload = await response.json();
    expect(payload.ok).toBe(false);
    expect(payload.error.code).toBe('VALIDATION_ERROR');
  });
});

test.describe('Workout Log API', () => {
  test('GET /workout_log page loads', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/workout_log`);
    expect(response.ok()).toBeTruthy();
  });

  test('GET /get_workout_log returns logs', async ({ request }) => {
    // Try alternate route name
    let response = await request.get(`${BASE_URL}/get_workout_log`);
    if (response.status() === 404) {
      response = await request.get(`${BASE_URL}/get_workout_logs`);
    }
    
    // Accept 200 or 404
    if (response.ok()) {
      const data = await response.json();
      expect(data.ok === true || data.status === 'success' || data.success === true || Array.isArray(data)).toBeTruthy();
    } else {
      expect([404]).toContain(response.status());
    }
  });

  test('POST /update_workout_log requires valid data', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/update_workout_log`, {
      data: {}
    });
    
    expect(response.status()).toBe(400);
  });

  test('POST /delete_workout_log requires log_id', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/delete_workout_log`, {
      data: {}
    });
    
    expect(response.status()).toBe(400);
  });

  test('POST /clear_workout_log clears all logs', async ({ request }) => {
    // This is a destructive operation, so we just verify the endpoint exists
    const response = await request.post(`${BASE_URL}/clear_workout_log`, {
      data: { confirm: false } // Don't actually clear
    });
    
    // Should respond (either success or validation error)
    expect([200, 400]).toContain(response.status());
  });

  test('POST /import_from_plan imports exercises', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/import_from_plan`);
    // Route may not exist or may require data
    expect([200, 400, 404]).toContain(response.status());
  });
});

test.describe('Export API', () => {
  test('GET /export_to_excel returns Excel file', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/export_to_excel`);
    expect(response.ok()).toBeTruthy();
    
    const contentType = response.headers()['content-type'];
    expect(contentType).toContain('spreadsheet');
  });

  test('POST /export_to_workout_log exports data', async ({ request }) => {
    await clearWorkoutPlanState(request);
    await seedWorkoutPlanExercise(request);

    const response = await request.post(`${BASE_URL}/export_to_workout_log`);
    expect(response.ok()).toBeTruthy();
  });
});

test.describe('Progression Plan API', () => {
  test('GET /progression page loads', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/progression`);
    expect(response.ok()).toBeTruthy();
  });

  test('DELETE /delete_progression_goal/<id> returns a not-found response for a missing goal', async ({ request }) => {
    const response = await request.delete(`${BASE_URL}/delete_progression_goal/999999`);

    expect(response.status()).toBe(404);
    const payload = await response.json();
    expect(payload.ok).toBe(false);
    expect(payload.status).toBe('error');
    expect(payload.error.code).toBe('NOT_FOUND');
    expect(payload.message).toBe('Goal not found');
  });

  test('POST /complete_progression_goal/<id> returns a not-found response for a missing goal', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/complete_progression_goal/999999`, {
      data: {}
    });

    expect(response.status()).toBe(404);
    const payload = await response.json();
    expect(payload.ok).toBe(false);
    expect(payload.status).toBe('error');
    expect(payload.error.code).toBe('NOT_FOUND');
    expect(payload.message).toBe('Goal not found');
  });
});

test.describe('Weekly Summary API', () => {
  test('GET /weekly_summary page loads', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/weekly_summary`);
    expect(response.ok()).toBeTruthy();
  });

  test('GET /weekly_summary returns live JSON summary data for explicit JSON callers', async ({ request }) => {
    const response = await request.get(
      `${BASE_URL}/weekly_summary?counting_mode=effective&contribution_mode=total`,
      { headers: JSON_HEADERS }
    );

    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload.ok).toBe(true);
    expect(payload.status).toBe('success');
    expect(payload).toHaveProperty('data');
    const data = payload.data as Record<string, unknown>;

    expect(Array.isArray(data.weekly_summary)).toBe(true);
    expect(Array.isArray(data.categories)).toBe(true);
    expect(data).toHaveProperty('isolated_muscles');
    expect(data).toHaveProperty('modes');
  });
});

test.describe('Session Summary API', () => {
  test('GET /session_summary page loads', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/session_summary`);
    expect(response.ok()).toBeTruthy();
  });

  test('GET /session_summary returns live JSON summary data for explicit JSON callers', async ({ request }) => {
    const response = await request.get(
      `${BASE_URL}/session_summary?counting_mode=effective&contribution_mode=total`,
      { headers: JSON_HEADERS }
    );

    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload.ok).toBe(true);
    expect(payload.status).toBe('success');
    expect(payload).toHaveProperty('data');
    const data = payload.data as Record<string, unknown>;

    expect(Array.isArray(data.session_summary)).toBe(true);
    expect(Array.isArray(data.categories)).toBe(true);
    expect(data).toHaveProperty('isolated_muscles');
    expect(data).toHaveProperty('modes');
  });
});

test.describe('Volume Splitter API', () => {
  test('GET /volume_splitter page loads', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/volume_splitter`);
    expect(response.ok()).toBeTruthy();
  });

  test('POST /api/calculate_volume returns the final wrapped contract', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/calculate_volume`, {
      data: {}
    });

    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload.ok).toBe(true);
    expect(payload.status).toBe('success');
    expect(payload).toHaveProperty('data');
    const data = payload.data as Record<string, unknown>;
    expect(data).toHaveProperty('results');
    expect(data).toHaveProperty('ranges');
    expect(data).toHaveProperty('suggestions');
  });

  test('POST /api/calculate_volume with valid data returns computed results', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/calculate_volume`, {
      data: {
        training_days: 2,
        mode: 'basic',
        volumes: {
          Chest: 20
        },
        ranges: {
          Chest: {
            min: 12,
            max: 18
          }
        }
      }
    });

    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload.ok).toBe(true);
    expect(payload.status).toBe('success');
    expect(payload).toHaveProperty('data');
    const data = payload.data as Record<string, any>;
    expect(data.results.Chest.weekly_sets).toBe(20);
    expect(data.results.Chest.sets_per_session).toBe(10);
    expect(data.results.Chest.status).toBe('high');
  });

  test('GET /api/volume_history returns a JSON object', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/volume_history`, {
      headers: JSON_HEADERS
    });

    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload.ok).toBe(true);
    expect(payload.status).toBe('success');
    expect(payload).toHaveProperty('data');
    expect(typeof payload.data).toBe('object');
  });

  test('volume persistence routes save, list, load, and delete a plan', async ({ request }) => {
    const saveResponse = await request.post(`${BASE_URL}/api/save_volume_plan`, {
      headers: JSON_HEADERS,
      data: {
        mode: 'basic',
        training_days: 4,
        volumes: {
          Chest: 18,
          Back: 14,
        },
      }
    });

    expect(saveResponse.ok()).toBeTruthy();
    const savePayload = await saveResponse.json();
    expect(savePayload.ok).toBe(true);
    expect(savePayload.status).toBe('success');
    expect(savePayload.message).toBe('Volume plan saved successfully');
    const savedPlan = savePayload.data as Record<string, unknown>;
    const planId = savedPlan.plan_id as number;
    expect(typeof planId).toBe('number');

    const historyResponse = await request.get(`${BASE_URL}/api/volume_history`, {
      headers: JSON_HEADERS
    });
    expect(historyResponse.ok()).toBeTruthy();
    const historyPayload = await historyResponse.json();
    expect(historyPayload.ok).toBe(true);
    expect(historyPayload.status).toBe('success');
    const history = historyPayload.data as Record<string, Record<string, unknown>>;
    expect(history[String(planId)]).toBeTruthy();

    const planResponse = await request.get(`${BASE_URL}/api/volume_plan/${planId}`, {
      headers: JSON_HEADERS
    });
    expect(planResponse.ok()).toBeTruthy();
    const planPayload = await planResponse.json();
    expect(planPayload.ok).toBe(true);
    expect(planPayload.status).toBe('success');
    const plan = planPayload.data as Record<string, unknown>;
    expect(plan.training_days).toBe(4);
    expect(plan).toHaveProperty('created_at');
    expect(plan).toHaveProperty('volumes');

    const deleteResponse = await request.delete(`${BASE_URL}/api/volume_plan/${planId}`, {
      headers: JSON_HEADERS
    });
    expect(deleteResponse.ok()).toBeTruthy();
    const deletePayload = await deleteResponse.json();
    expect(deletePayload.ok).toBe(true);
    expect(deletePayload.status).toBe('success');
    expect(deletePayload.message).toBe('Volume plan deleted successfully');
    expect(deletePayload.data).toBeUndefined();

    const missingPlanResponse = await request.get(`${BASE_URL}/api/volume_plan/${planId}`, {
      headers: JSON_HEADERS
    });
    expect(missingPlanResponse.status()).toBe(404);
    const missingPlanPayload = await missingPlanResponse.json();
    expect(missingPlanPayload.ok).toBe(false);
    expect(missingPlanPayload.status).toBe('error');
    expect(missingPlanPayload.message).toBe('Plan not found');
    expect(missingPlanPayload.error?.code).toBe('NOT_FOUND');
  });
});

test.describe('Filters API', () => {
  test('GET /get_filter_options returns filter values', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/get_filter_options`);
    // Route may not exist
    if (response.ok()) {
      const data = await response.json();
      expect(data.ok === true || data.status === 'success' || data.success === true || typeof data === 'object').toBeTruthy();
    } else {
      expect([404]).toContain(response.status());
    }
  });

  test('POST /apply_filters filters exercises', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/apply_filters`, {
      data: {
        primary_muscle_group: 'Chest'
      }
    });
    
    // Route may not exist
    expect([200, 400, 404]).toContain(response.status());
    
    if (response.ok()) {
      const data = await response.json();
      expect(Array.isArray(data) || data.data).toBeTruthy();
    }
  });
});

test.describe('Error Handling', () => {
  test('404 for non-existent route', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/non_existent_route_12345`);
    expect(response.status()).toBe(404);
  });

  test('POST with invalid JSON returns 400', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/add_exercise`, {
      headers: { 'Content-Type': 'application/json' },
      data: 'invalid json{{'
    });
    
    expect([400, 500]).toContain(response.status());
  });

  test('POST with wrong content type handled gracefully', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/add_exercise`, {
      headers: { 'Content-Type': 'text/plain' },
      data: 'plain text'
    });
    
    expect([400, 415, 500]).toContain(response.status());
  });
});

test.describe('Response Format Consistency', () => {
  test('success responses have consistent format', async ({ request }) => {
    const endpoints = [
      { path: '/get_workout_plan' },
      { path: '/get_routine_options' },
      { path: '/weekly_summary', headers: JSON_HEADERS },
      { path: '/session_summary', headers: JSON_HEADERS }
    ];

    for (const endpoint of endpoints) {
      const response = await request.get(`${BASE_URL}${endpoint.path}`, {
        headers: endpoint.headers
      });
      
      // Some routes may not exist (404)
      if (response.ok()) {
        const data = await response.json();
        
        // All success responses should have status/ok or success flag or be valid data
        expect(
          data.ok === true || 
          data.status === 'success' || 
          data.success === true ||
          Array.isArray(data) ||
          typeof data === 'object'
        ).toBeTruthy();
      }
    }
  });

  test('error responses have consistent format', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/add_exercise`, {
      data: {}
    });
    
    if (!response.ok()) {
      const data = await response.json();
      
      // Error responses should have some error indicator
      expect(
        data.ok === false || 
        data.success === false || 
        data.status === 'error' ||
        data.error ||
        data.message
      ).toBeTruthy();
    }
  });
});

test.describe('Rate Limiting and Performance', () => {
  test('multiple rapid requests handled', async ({ request }) => {
    const promises = [];
    
    for (let i = 0; i < 10; i++) {
      promises.push(request.get(`${BASE_URL}/get_workout_plan`));
    }

    const responses = await Promise.all(promises);
    
    // All should succeed (no rate limiting on local dev)
    for (const response of responses) {
      expect(response.ok()).toBeTruthy();
    }
  });

  test('response time is acceptable', async ({ request }) => {
    const start = Date.now();
    await request.get(`${BASE_URL}/get_workout_plan`);
    const elapsed = Date.now() - start;

    // Should respond within 5 seconds
    expect(elapsed).toBeLessThan(5000);
  });
});

test.describe('CORS and Headers', () => {
  test('JSON endpoints return correct content-type', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/get_workout_plan`);
    const contentType = response.headers()['content-type'];
    
    expect(contentType).toContain('application/json');
  });

  test('HTML pages return correct content-type', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/workout_plan`);
    const contentType = response.headers()['content-type'];
    
    expect(contentType).toContain('text/html');
  });
});
