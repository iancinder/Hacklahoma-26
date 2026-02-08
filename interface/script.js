console.log("Script loaded successfully!");

function getFormData() {
    return {
        // User Profile
        age: document.getElementById('age')?.value,
        height: document.getElementById('height')?.value,
        weight: document.getElementById('weight')?.value,
        experience: document.getElementById('experience')?.value,

        // Trail Data
        distance: document.getElementById('distance')?.value,
        elevation: document.getElementById('elevation')?.value
    };
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('updateBtn');
    
    if(btn) {
        // We found the button, now listen for clicks
        btn.addEventListener('click', () => {
            console.log("Button was clicked!");

            // 1. Collect the data
            const allData = getFormData();

            // 2. Print it to the console so you can see it
            console.log("payload:", allData);
        });
    } else {
        console.error("Could not find element with id='updateBtn'");
    }
});