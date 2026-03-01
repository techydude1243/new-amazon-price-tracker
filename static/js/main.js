document.addEventListener('DOMContentLoaded', function() {
    const trackForm = document.getElementById('trackForm');
    const trackButton = document.getElementById('trackButton');
    const clearAllBtn = document.getElementById('clearAllBtn');
    const spinner = trackButton.querySelector('.spinner-border');

    trackForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Show loading state
        trackButton.disabled = true;
        spinner.classList.remove('d-none');
        
        const formData = new FormData(trackForm);
        
        try {
            const response = await fetch('/track', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Reload page to show updated list
                window.location.reload();
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while tracking the product');
        } finally {
            // Reset loading state
            trackButton.disabled = false;
            spinner.classList.add('d-none');
        }
    });

    clearAllBtn.addEventListener('click', async function() {
        if (confirm('Are you sure you want to clear all tracked products?')) {
            try {
                const response = await fetch('/clear', {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    window.location.reload();
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while clearing products');
            }
        }
    });
});
