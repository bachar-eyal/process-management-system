// פונקציה להצגת alert הצלחה
function showSuccessAlert(message) {
    console.log('showSuccessAlert called with:', message);
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
        border-radius: 15px;
        border: none;
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        color: white;
        font-weight: 600;
        padding: 1rem 1.5rem;
    `;
    
    // הוסף את ה-alert לגוף הדף
    document.body.appendChild(alertDiv);
    
    // אנימציית כניסה
    setTimeout(() => {
        alertDiv.style.top = '20px';
    }, 10);
    
    // אנימציית יציאה
    setTimeout(() => {
        alertDiv.style.top = '-100px';
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 300);
    }, 3000);
}

// פונקציה להצגת alert שגיאה
function showErrorAlert(message) {
    console.log('showErrorAlert called with:', message);
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger fade show';
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
        border-radius: 15px;
        border: none;
        background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        color: white;
        font-weight: 600;
        padding: 1rem 1.5rem;
    `;
    
    // הוסף את ה-alert לגוף הדף
    document.body.appendChild(alertDiv);
    
    // אנימציית כניסה
    setTimeout(() => {
        alertDiv.style.top = '20px';
    }, 10);
    
    // אנימציית יציאה
    setTimeout(() => {
        alertDiv.style.top = '-100px';
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 300);
    }, 3000);
}