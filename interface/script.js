console.log("Script loaded successfully");

function getFormData() {
    // Helper: return trimmed value or null (so empty fields become null in JSON)
    const valOrNull = (id) => {
        const v = document.getElementById(id)?.value?.trim();
        return (v && v.length > 0) ? v : null;
    };

    return {
        // User Profile
        age: valOrNull('age'),
        weight_lb: valOrNull('weight_lb'),
        flat_speed_mph: valOrNull('flat_speed_mph'),
        vertical_speed_fph: valOrNull('vertical_speed_fph'),
        fitness_level: valOrNull('fitness_level'),

        // Trail Data
        activity_type: document.getElementById('activity_type')?.value,
        difficulty: document.getElementById('difficulty')?.value,
        distance_mi: valOrNull('distance_mi'),
        elevation_gain_ft: valOrNull('elevation_gain_ft'),

        // Trail Coordinates (optional — triggers OpenRouteService)
        start_lat: valOrNull('start_lat'),
        start_lon: valOrNull('start_lon'),
        end_lat:   valOrNull('end_lat'),
        end_lon:   valOrNull('end_lon'),
    };
}

function updateUI(data) {
    // Update prediction stat boxes
    if(document.getElementById('time_hr')) 
        document.getElementById('time_hr').textContent = data.time_hr + " hr";

    if(document.getElementById('calories')) 
        document.getElementById('calories').textContent = data.calories + " kcal";
    
    if(document.getElementById('fatigue')) 
        document.getElementById('fatigue').textContent = data.fatigue + " / 10";
    
    if(document.getElementById('paceValue')) {
        // Get pace in seconds per mile from whichever field the server sends
        let totalSec = data.pace_sec_per_mi || data.pace || 0;
        if (totalSec > 0) {
            const m = Math.floor(totalSec / 60);
            const s = Math.floor(totalSec % 60);
            document.getElementById('paceValue').textContent = m + ":" + String(s).padStart(2, '0') + " min/mi";
        } else {
            document.getElementById('paceValue').textContent = "-- : --";
        }
    }

    // Reset auto badges (hide until trail data confirms them)
    document.getElementById('dist_auto').style.display = 'none';
    document.getElementById('elev_auto').style.display = 'none';

    // Auto-fill distance & elevation if trail data came back from ORS
    if (data.trail_distance_mi != null) {
        document.getElementById('distance_mi').value = data.trail_distance_mi;
        document.getElementById('dist_auto').style.display = 'inline';
    }
    if (data.trail_elevation_gain_ft != null) {
        document.getElementById('elevation_gain_ft').value = data.trail_elevation_gain_ft;
        document.getElementById('elev_auto').style.display = 'inline';
    }

    // Display elevation graph if one was returned
    const graphSlot = document.getElementById('elevationGraphSlot');
    if (graphSlot) {
        if (data.elevation_graph) {
            graphSlot.innerHTML = '<img src="data:image/png;base64,' + data.elevation_graph + '" alt="Elevation vs Time" style="width:100%; border-radius:6px;">';
            graphSlot.classList.add('chart-filled');
        } else {
            // Reset to placeholder if no graph this time
            graphSlot.innerHTML = '[Graph Here]';
            graphSlot.classList.remove('chart-filled');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('updateBtn');
    
    if(btn) {
        btn.addEventListener('click', async () => {
            console.log("Button Clicked!");
            
            // 1. Get Data
            const payload = getFormData();
            console.log("Sending:", payload);

            // Show loading state
            btn.textContent = "Loading...";
            btn.disabled = true;

            try {
                // 2. Send to Python (main.py)
                const response = await fetch('http://127.0.0.1:5001/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                // 3. Get Answer
                const result = await response.json();
                console.log("Response:", result);
                console.log("Pace (sec/mi):", result.pace_sec_per_mi, "Formatted:", result.pace_min_per_mi_str);

                if(result.error) {
                    alert("Error: " + result.error);
                } else {
                    updateUI(result);
                }

            } catch (error) {
                console.error("Connection Failed:", error);
                alert("Could not connect to Python");
            } finally {
                btn.textContent = "Update Prediction";
                btn.disabled = false;
            }
        });
    } else {
        console.error("Could not find 'updateBtn'");
    }
});
