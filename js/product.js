function callSignature(serialNumber, sku) {
    console.log("Calling signature with:", serialNumber, sku);
    const formData = new FormData();
    formData.append('serial_number', serialNumber);
    formData.append('sku', sku);

    fetch('/print_signature', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessAlert(data.message);
        } else {
            showErrorAlert(data.error);
        }
    })
    .catch(error => {
        console.error("Error calling signature:", error);
        showErrorAlert("שגיאה בהדפסת התג");
    });
}
// Success alert like approved_skus.js
function showSuccessAlert(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success fade show';
    alertDiv.innerHTML = message;
    alertDiv.style.cssText = `
        position: fixed;
        top: -100px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        min-width: 300px;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        transition: top 0.3s ease;
    `;
    document.body.appendChild(alertDiv);
    setTimeout(() => {
        alertDiv.style.top = '20px';
    }, 10);
    setTimeout(() => {
        alertDiv.style.top = '-100px';
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 300);
    }, 2000);
}

document.addEventListener('DOMContentLoaded', function() {
    if (window.successMessage) {
        showSuccessAlert(window.successMessage);
    }
}); 