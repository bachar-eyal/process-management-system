// פונקציות להצגת הודעות
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
    }, 3000);
}

function showErrorAlert(message) {
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
    }, 3000);
}

// פונקציות לניהול צריכת חלפים
function showAddSpareModal() {
    $('#addSpareModal').modal('show');
}

function addSpareUsage() {
    const tagId = window.location.pathname.split('/').pop(); // קבל tag_id מה-URL
    const partId = document.getElementById('spare_part_select').value;
    const serialNumber = document.getElementById('spare_serial_number').value.trim();
    
    if (!partId || !serialNumber) {
        showErrorAlert('יש למלא את כל השדות');
        return;
    }
    
    fetch('/add_spare_usage', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            tag_id: tagId,
            part_id: partId,
            serial_number: serialNumber
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Server response:', data);
        if (data.success) {
            showSuccessAlert(data.message);
            addUsageToTable(data.usage);
            $('#addSpareModal').modal('hide');
            // נקה את הטופס
            document.getElementById('spare_part_select').value = '';
            document.getElementById('spare_serial_number').value = '';
        } else {
            showErrorAlert(data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        console.error('Error details:', error.message);
        showErrorAlert(`שגיאה בהוספת חלק החילוף: ${error.message}`);
    });
}

function deleteSpareUsage(usageId) {
    if (!confirm('האם אתה בטוח שברצונך למחוק צריכת חלק זה?')) {
        return;
    }
    
    fetch('/delete_spare_usage', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            usage_id: usageId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessAlert(data.message);
            // מחק את השורה מהטבלה
            const row = document.querySelector(`tr[data-usage-id="${usageId}"]`);
            if (row) {
                row.remove();
            }
            // בדוק אם הטבלה ריקה
            checkIfTableEmpty();
        } else {
            showErrorAlert(data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showErrorAlert('אירעה שגיאה במחיקת צריכת החלק');
    });
}

function addUsageToTable(usage) {
    console.log('addUsageToTable called with:', usage);
    
    // חפש את הטבלה - יש שתי אפשרויות במבנה ההTML
    let tableBody = document.querySelector('tbody#usedPartsTable');
    
    // אם לא מצאנו, זה אומר שהטבלה מוסתרת ונמצאת בדיב הנסתר
    if (!tableBody) {
        console.log('Table body not found, looking for hidden table');
        const hiddenTableDiv = document.querySelector('div#usedPartsTable');
        if (hiddenTableDiv) {
            console.log('Found hidden div, showing it');
            hiddenTableDiv.style.display = 'block';
            tableBody = hiddenTableDiv.querySelector('tbody');
            
            // הסתר גם את הודעת "לא נעשה שימוש"
            const cardBody = document.querySelector('.spare-parts-section .card-body');
            const noUsageMessage = cardBody.querySelector('.text-muted.text-center');
            if (noUsageMessage) {
                noUsageMessage.style.display = 'none';
            }
        }
    } else {
        console.log('Found existing tbody with id usedPartsTable');
    }
    
    // אם עדיין לא מצאנו, זה אומר שמשהו לא בסדר
    if (!tableBody) {
        console.error('Could not find or create table body!');
        return;
    }
    
    console.log('Table body found:', tableBody);
    
    // יצור שורה חדשה
    const newRow = document.createElement('tr');
    newRow.setAttribute('data-usage-id', usage.usage_id);
    
    // פרמט תאריך עם זמן מקומי
    const dateObj = new Date(usage.date_used);
    const dateFormatted = dateObj.toLocaleString('he-IL', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    newRow.innerHTML = `
        <td class="part-number-cell">
            <span class="part-badge">${usage.part_number}</span>
        </td>
        <td class="description-cell">${usage.description || '-'}</td>
        <td class="manufacturer-cell">${usage.manufacturer || '-'}</td>
        <td class="serial-cell">
            <span class="serial-badge">${usage.serial_number}</span>
        </td>
        <td class="date-cell">
            <small class="text-muted">
                <i class="fas fa-clock mr-1"></i>${dateFormatted}
            </small>
        </td>
        <td class="actions-cell">
            <button type="button" class="btn btn-danger btn-sm delete-usage-btn" onclick="deleteSpareUsage(${usage.usage_id})">
                <i class="fas fa-trash mr-1"></i>מחק
            </button>
        </td>
    `;
    
    // הוסף את השורה לטבלה עם אנימציה
    console.log('Adding row to table. Current rows count:', tableBody.children.length);
    
    newRow.style.opacity = '0';
    newRow.style.transform = 'translateY(20px)';
    
    if (tableBody.firstChild) {
        console.log('Inserting row at the beginning');
        tableBody.insertBefore(newRow, tableBody.firstChild);
    } else {
        console.log('Appending row to empty table');
        tableBody.appendChild(newRow);
    }
    
    console.log('Row added. New rows count:', tableBody.children.length);
    
    // אנימציית כניסה
    setTimeout(() => {
        newRow.style.transition = 'all 0.5s ease';
        newRow.style.opacity = '1';
        newRow.style.transform = 'translateY(0)';
    }, 10);
    
    console.log('Row added successfully with animation');
}

function checkIfTableEmpty() {
    const tableBody = document.querySelector('tbody#usedPartsTable');
    if (tableBody && tableBody.children.length === 0) {
        // הסתר את הטבלה הראשית ותציג את הודעת "לא נעשה שימוש"
        const mainTable = tableBody.closest('table');
        if (mainTable) {
            mainTable.style.display = 'none';
        }
        
        // הצג את הודעת "לא נעשה שימוש"
        const cardBody = document.querySelector('.spare-parts-section .card-body');
        if (cardBody && !cardBody.querySelector('.text-muted.text-center')) {
            const noUsageMessage = document.createElement('p');
            noUsageMessage.className = 'text-muted text-center';
            noUsageMessage.textContent = 'לא נעשה שימוש בחלקי חילוף עדיין';
            cardBody.appendChild(noUsageMessage);
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const isVerifiedFault = "{{ is_verified_fault }}";
    console.log("is_verified_fault from template:", isVerifiedFault);
    const checkbox = document.getElementById('is_verified_fault');
    if (isVerifiedFault === "כן") {
        checkbox.checked = true;
        console.log("Checkbox set to checked based on template value");
    } else {
        console.log("Checkbox not checked, value is:", isVerifiedFault);
    }
});
