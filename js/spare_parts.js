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
    }, 2000);
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
    }, 2000);
}

// פונקציה למחיקת חלק חילוף עם AJAX
function deletePart(partId, partNumber) {
    console.log('deletePart called with:', { partId, partNumber });
    
    if (!confirm(`האם אתה בטוח שברצונך למחוק את חלק החילוף "${partNumber}"?`)) {
        return;
    }
    
    const formData = new FormData();
    formData.append('action', 'delete');
    formData.append('part_id', partId);
    
    console.log('Sending DELETE request to /spare_parts with:', Array.from(formData.entries()));
    
    fetch('/spare_parts', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Delete response:', data);
        if (data.success) {
            showSuccessAlert(data.message);
            // מחק את השורה מהטבלה
            const row = document.querySelector(`tr[data-part-id="${partId}"]`);
            if (row) {
                row.remove();
            }
        } else {
            showErrorAlert(data.error);
        }
    })
    .catch(error => {
        console.error('Delete error:', error);
        showErrorAlert('אירעה שגיאה במחיקת חלק החילוף');
    });
}

// פונקציה להוספת חלק לטבלה
function addPartToTable(partData) {
    const tableBody = document.querySelector('#partsTable tbody');
    const newRow = document.createElement('tr');
    newRow.setAttribute('data-part-id', partData.part_id);
    
    newRow.innerHTML = `
        <td>${partData.part_number}</td>
        <td>${partData.description || '-'}</td>
        <td>${partData.manufacturer || '-'}</td>
        <td>
            <button type="button" class="btn btn-danger btn-sm delete-btn" 
                    data-part-id="${partData.part_id}" 
                    data-part-number="${partData.part_number}">מחק</button>
        </td>
    `;
    
    tableBody.appendChild(newRow);
    
    // הוסף event listener לכפתור המחיקה החדש
    const deleteBtn = newRow.querySelector('.delete-btn');
    const partId = deleteBtn.getAttribute('data-part-id');
    const partNumber = deleteBtn.getAttribute('data-part-number');
    deleteBtn.addEventListener('click', function() {
        deletePart(partId, partNumber);
    });
}

// פונקציה להוספת חלק חילוף עם AJAX
function addPart() {
    const partNumber = document.getElementById('part_number').value.trim();
    const description = document.getElementById('description').value.trim();
    const manufacturer = document.getElementById('manufacturer').value.trim();
    
    if (!partNumber) {
        showErrorAlert('יש להזין מספר חלק');
        return;
    }
    
    const formData = new FormData();
    formData.append('action', 'add');
    formData.append('part_number', partNumber);
    formData.append('description', description);
    formData.append('manufacturer', manufacturer);
    
    console.log('Sending ADD request to /spare_parts with:', Array.from(formData.entries()));
    
    fetch('/spare_parts', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessAlert(data.message);
            // נקה את השדות
            document.getElementById('part_number').value = '';
            document.getElementById('description').value = '';
            document.getElementById('manufacturer').value = '';
            // הוסף את החלק החדש לטבלה
            if (data.part) {
                addPartToTable(data.part);
            }
        } else {
            showErrorAlert(data.error);
        }
    })
    .catch(error => {
        console.error('Add error:', error);
        showErrorAlert('אירעה שגיאה בהוספת חלק החילוף');
    });
}

// אתחול הדף
document.addEventListener('DOMContentLoaded', function() {
    // הוסף event listeners לכפתורי מחיקה קיימים
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        const partId = button.getAttribute('data-part-id');
        const partNumber = button.getAttribute('data-part-number');
        button.addEventListener('click', function() {
            deletePart(partId, partNumber);
        });
    });
    
    // הוסף event listener לטופס הוספה
    document.getElementById('addPartForm').addEventListener('submit', function(e) {
        e.preventDefault();
        addPart();
    });
    
    // הוסף Enter key support לשדה מספר החלק
    document.getElementById('part_number').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            addPart();
        }
    });
    
    // הוסף Enter key support לשדה התיאור
    document.getElementById('description').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            addPart();
        }
    });
});
