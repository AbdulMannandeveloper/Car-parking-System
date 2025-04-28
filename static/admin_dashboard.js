document.addEventListener('DOMContentLoaded', () => {
    const responseContainer = document.getElementById('response-container');

    document.querySelectorAll('.sidebar a').forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const action = event.target.getAttribute('data-action');
            fetch(`/admin_action/${action}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        responseContainer.innerHTML = `<p>Error: ${data.error}</p>`;
                    } else {
                        responseContainer.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                    }
                })
                .catch(error => {
                    responseContainer.innerHTML = `<p>Error: ${error}</p>`;
                });
        });
    });
});
