console.log("Script loaded successfully");

function getFormData() {
    return {
        // User Profile
        age: document.getElementById('age')?.value,
        weight_lb: document.getElementById('weight_lb')?.value,
        flat_speed_mph: document.getElementById('flat_speed_mph')?.value,
        vertical_speed_fph: document.getElementById('vertical_speed_fph')?.value,
        fitness_level: document.getElementById('fitness_level')?.value,

        // Trail Data
        activity_type: document.getElementById('activity_type')?.value,
        difficulty: document.getElementById('difficulty')?.value,
        distance_mi: document.getElementById('distance_mi')?.value,
        elevation_gain_ft: document.getElementById('elevation_gain_ft')?.value
    };
}

function updateUI(data) {
    // updates the UI with the latest data from the server
    if(document.getElementById('time_hr')) 
        document.getElementById('time_hr').textContent = data.time_hr + " hr";

    if(document.getElementById('calories')) 
        document.getElementById('calories').textContent = data.calories + " kcal";
    
    if(document.getElementById('fatigue')) 
        document.getElementById('fatigue').textContent = data.fatigue + " / 10";
    
    if(document.getElementById('paceValue')) 
        document.getElementById('paceValue').textContent = data.pace + " min/mi";
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('updateBtn');
    
    if(btn) {
        btn.addEventListener('click', async () => {
            console.log("Button Clicked!");
            
            // 1. Get Data
            const payload = getFormData();
            console.log("Sending:", payload);

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

                if(result.error) {
                    alert("Error: " + result.error);
                } else {
                    updateUI(result);
                }

            } catch (error) {
                console.error("Connection Failed:", error);
                alert("Could not connect to Python");
            }
        });
    } else {
        console.error("Could not find 'updateBtn'");
    }
});