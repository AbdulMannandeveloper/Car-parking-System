document.addEventListener('DOMContentLoaded', () => {
    // Function to handle updating the UI with fetched data
    function updateUI(data) {
        if (data) {
            document.getElementById('name').textContent = data.name || '__';
            document.getElementById('entrance-time').textContent = data.entrance_time || '__';
            document.getElementById('exit-time').textContent = data.exit_time || '__';
            document.getElementById('balance').textContent = data.current_balance || '__';
            document.getElementById('vehicle-name').textContent = data.vehicle_name || '__';
            document.getElementById('semester').textContent = data.semester || '__';
            document.getElementById('department').textContent = data.department || '__';
        } else {
            alert('RFID tag not found or error occurred.');
        }
    }

    // Function to fetch RFID data from server
    function fetchRFIDData() {
        fetch('/student_info')
            .then(response => response.json())
            .then(data => {
                console.log('Data Received:', data);
                updateUI(data);
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }

    // Fetch RFID data on page load
    fetchRFIDData();
});
