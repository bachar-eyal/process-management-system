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

// פונקציה למחיקת מק"ט עם AJAX
function deleteSku(skuId, skuCode) {
    console.log('deleteSku called with:', { skuId, skuCode });
    console.log('deleteSku - confirm dialog will show');
    if (confirm(`האם אתה בטוח שאתה רוצה למחוק את מקט ${skuCode}?`)) {
        const formData = new FormData();
        formData.append('action', 'delete');
        formData.append('sku_id', skuId);
        console.log('Sending DELETE request to /manage_skus with:', Array.from(formData.entries()));
        fetch('/manage_skus', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log('deleteSku response:', data);
            if (data.success) {
                showSuccessAlert(data.message);
                // מחק את השורה מהטבלה
                const row = document.querySelector(`[data-sku-id="${skuId}"]`).closest('tr');
                row.remove();
            } else {
                showErrorAlert(data.error);
            }
        })
        .catch(error => {
            console.error('Error in deleteSku:', error);
            showErrorAlert('אירעה שגיאה במחיקת המק"ט');
        });
    }
}

// פונקציה להוספת מק"ט לטבלה
function addSkuToTable(skuData) {
    const tbody = document.querySelector('tbody');
    const newRow = document.createElement('tr');
    newRow.innerHTML = `
        <td>${skuData.sku_code}</td>
        <td>${skuData.description || '-'}</td>
        <td style="min-width:180px; vertical-align:middle;">
            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; min-height:120px;">
                <form method="post" enctype="multipart/form-data" style="display:flex; flex-direction:column; align-items:center; gap:6px;">
                    <input type="hidden" name="sku_id" value="${skuData.sku_id}">
                    <label style="cursor:pointer;">
                        <span class="btn btn-light btn-lg rounded-circle" style="width:54px; height:54px; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 8px #818cf822;">
                            <i class="fas fa-cloud-upload-alt fa-lg" style="color:#6366f1;"></i>
                        </span>
                        <input type="file" name="final_check_image" accept="image/*,.pdf" style="display:none;" onchange="this.form.submit()">
                    </label>
                    <button type="submit" name="upload_final_check" style="display:none;"></button>
                    <span style="font-size:0.95em; color:#6366f1;">העלה קובץ</span>
                </form>
            </div>
        </td>
        <td>
            <button type="button" name="delete_sku" class="btn btn-danger btn-sm delete-btn" data-sku-id="${skuData.sku_id}">מחק</button>
        </td>
    `;
    tbody.appendChild(newRow);
    
    // הוסף event listener לכפתור המחיקה החדש
    const deleteButton = newRow.querySelector('[name="delete_sku"]');
    deleteButton.addEventListener('click', function(e) {
        e.preventDefault();
        const skuId = this.getAttribute('data-sku-id');
        const skuCode = this.closest('tr').querySelector('td:first-child').textContent;
        deleteSku(skuId, skuCode);
    });
}

// פונקציה להוספת מק"ט עם AJAX
function addSku() {
    const skuCode = document.getElementById('sku_code').value.trim();
    const description = document.getElementById('description').value.trim();
    if (!skuCode) {
        showErrorAlert('יש להזין קוד מק"ט');
        return;
    }
    if (!/^\d+$/.test(skuCode)) {
        showErrorAlert('קוד המק"ט חייב להכיל מספרים בלבד');
        return;
    }
    const formData = new FormData();
    formData.append('action', 'add');
    formData.append('sku_code', skuCode);
    formData.append('description', description);
    console.log('Sending ADD request to /manage_skus with:', Array.from(formData.entries()));
    fetch('/manage_skus', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessAlert(data.message);
            // נקה את השדות
            document.getElementById('sku_code').value = '';
            document.getElementById('description').value = '';
            // הוסף את המק"ט החדש לטבלה
            if (data.sku) {
                addSkuToTable(data.sku);
            }
        } else {
            showErrorAlert(data.error);
        }
    })
    .catch(error => {
        console.error('Add error:', error);
        showErrorAlert('אירעה שגיאה בהוספת המק"ט');
    });
}

function initSkuTableEvents() {
    // הוסף validation לקלט המק"ט - רק מספרים
    const skuInput = document.getElementById('sku_code');
    if (skuInput) {
        skuInput.addEventListener('input', function(e) {
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    }
    // הוסף event listener לטופס ההוספה
    const addForm = document.querySelector('form');
    if (addForm) {
        addForm.addEventListener('submit', function(e) {
            e.preventDefault();
            addSku();
        });
    }
    // הוסף event listeners לכפתורי מחיקה
    const deleteButtons = document.querySelectorAll('[name="delete_sku"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const skuId = this.getAttribute('data-sku-id');
            const skuCode = this.closest('tr').querySelector('td:first-child').textContent;
            deleteSku(skuId, skuCode);
        });
    });
    // הוסף event listeners לכפתורי סגירת alerts
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('close')) {
            e.target.closest('.alert').remove();
        }
    });
    // הוסף event listeners להעלאת קובץ דף בדיקות סופיות - להסיר! (השרת כבר מרענן)
    // document.querySelectorAll('input[type="file"][name="final_check_image"]').forEach(input => {
    //     input.addEventListener('change', function() {
    //         setTimeout(() => {
    //             window.location.search = '?refresh=1';
    //         }, 1200);
    //     });
    // });
    // הוסף event listeners למחיקת קובץ דף בדיקות סופיות - להסיר! (השרת כבר מרענן)
    // document.querySelectorAll('button[name="delete_final_check"]').forEach(btn => {
    //     btn.closest('form').addEventListener('submit', function() {
    //         setTimeout(() => {
    //             window.location.search = '?refresh=1';
    //         }, 1200);
    //     });
    // });
    // הכרחת טעינה מחדש של תמונות (cache bust)
    document.querySelectorAll('img[alt="דף בדיקות"]').forEach(img => {
        const src = img.getAttribute('src');
        img.setAttribute('src', src.split('?')[0] + '?v=' + Date.now());
    });
}

// הוסף event listeners כשהדף נטען
document.addEventListener('DOMContentLoaded', function() {
    initSkuTableEvents();
}); 