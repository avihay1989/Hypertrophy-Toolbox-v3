<script>
// Add tooltip functions
function get_category_tooltip(category) {
    const tooltips = {
        'Mechanic': 'Classification based on joint involvement in the exercise',
        'Utility': 'Classification based on exercise role in training',
        'Force': 'Classification based on primary force direction'
    };
    return tooltips[category] || '';
}

function get_subcategory_tooltip(category, subcategory) {
    const tooltips = {
        'Mechanic': {
            'Compound': 'Multi-joint exercises like squats and bench press',
            'Isolated': 'Single-joint exercises focusing on specific muscles'
        },
        'Utility': {
            'Auxiliary': 'Supportive exercises that complement main lifts',
            'Basic': 'Foundational exercises targeting major muscle groups'
        },
        'Force': {
            'Push': 'Exercises involving pushing motions away from body',
            'Pull': 'Exercises involving pulling motions toward body'
        }
    };
    return tooltips[category]?.[subcategory] || '';
}

// Function to get volume classification details
function getVolumeDetails(totalSets) {
    let volumeClass, volumeLabel;
    
    if (totalSets < 10) {
        volumeClass = 'low-volume';
        volumeLabel = 'Low Volume';
    } else if (totalSets < 20) {
        volumeClass = 'medium-volume';
        volumeLabel = 'Medium Volume';
    } else if (totalSets < 30) {
        volumeClass = 'high-volume';
        volumeLabel = 'High Volume';
    } else {
        volumeClass = 'ultra-volume';
        volumeLabel = 'Excessive Volume';
    }

    const ranges = {
        'Low Volume': 'Below 10 sets',
        'Medium Volume': '10-19 sets',
        'High Volume': '20-29 sets',
        'Excessive Volume': '30+ sets'
    };

    return {
        class: volumeClass,
        label: volumeLabel,
        tooltip: `${volumeLabel}: ${ranges[volumeLabel]} (Current: ${totalSets} sets)`
    };
}

// Function to update the session summary table based on the selected method
async function updateSessionSummary() {
    const method = document.getElementById("method").value;
    const tableBody = document.getElementById("session-summary-table");
    const categoryTableBody = document.querySelector(".table-responsive tbody");

    // Display loading spinner
    tableBody.innerHTML = `
        <tr>
            <td colspan="6" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </td>
        </tr>`;

    try {
        const response = await fetch(`/session_summary?method=${method}`, {
            headers: { "Accept": "application/json" }
        });

        if (!response.ok) throw new Error("Failed to fetch session summary.");

        const data = await response.json();

        if (data.session_summary.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">No data available.</td>
                </tr>`;
        } else {
            // Populate the table with fetched data
            tableBody.innerHTML = data.session_summary.map(row => {
                const volume = getVolumeDetails(row.total_sets);
                return `
                    <tr>
                        <td>${row.routine || "N/A"}</td>
                        <td>${row.muscle_group || "N/A"}</td>
                        <td>${row.total_sets}</td>
                        <td>${row.total_reps}</td>
                        <td>${row.total_volume || (row.total_sets * row.total_reps * row.weight) || 0}</td>
                        <td>
                            <div class="volume-classification" 
                                 data-bs-toggle="tooltip"
                                 title="${volume.tooltip}">
                                <span class="volume-badge ${volume.class}">
                                    ${volume.label}
                                </span>
                            </div>
                        </td>
                    </tr>
                `;
            }).join("");
        }

        // Update categories table
        if (data.categories.length === 0) {
            categoryTableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-muted">No categories data available.</td>
                </tr>`;
        } else {
            categoryTableBody.innerHTML = data.categories.map(cat => `
                <tr>
                    <td>
                        <span data-bs-toggle="tooltip" 
                              title="${get_category_tooltip(cat.category)}">
                            ${cat.category}
                        </span>
                    </td>
                    <td>
                        <span data-bs-toggle="tooltip" 
                              title="${get_subcategory_tooltip(cat.category, cat.subcategory)}">
                            ${cat.subcategory}
                        </span>
                    </td>
                    <td>${cat.total_exercises}</td>
                </tr>
            `).join('');
        }

        // Initialize tooltips
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

    } catch (error) {
        console.error("Error fetching data:", error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-danger">Failed to load data.</td>
            </tr>`;
    }
}

// Initialize table when the page loads
document.addEventListener("DOMContentLoaded", updateSessionSummary);
</script>