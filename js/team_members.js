// פונקציה להצגת alert הצלחה
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

// פונקציה למחיקת עובד עם AJAX
function deleteMember(memberId, memberName) {
    console.log('deleteMember called with:', { memberId, memberName });
    
    if (confirm(`האם אתה בטוח שאתה רוצה למחוק את העובד ${memberName}?`)) {
        const formData = new FormData();
        formData.append('delete_member', '1');
        formData.append('member_id', memberId);
        
        console.log('Sending request with member_id:', memberId);
        
        fetch(window.location.href, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Response data:', data);
            if (data.success) {
                showSuccessAlert(data.message);
                // מחק את השורה מהטבלה
                const row = document.querySelector(`[data-member-id="${memberId}"]`).closest('tr');
                row.remove();
            } else {
                showErrorAlert(data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showErrorAlert('אירעה שגיאה במחיקת העובד');
        });
    }
}

// פונקציה להוספת עובד לטבלה
function addMemberToTable(memberData) {
    const tbody = document.querySelector('tbody');
    const newRow = document.createElement('tr');
    
    let roleText = '';
    if (memberData.role === 'performer') {
        roleText = 'מבצע';
    } else if (memberData.role === 'checker') {
        roleText = 'בודק';
    } else if (memberData.role === 'both') {
        roleText = 'מבצע ובודק';
    }
    
    newRow.innerHTML = `
        <td>${memberData.name}</td>
        <td>${memberData.id_number}</td>
        <td>${roleText}</td>
        <td>
            ${memberData.signature ? 
                `<canvas id="signature_${memberData.member_id}" class="signature-display" width="200" height="100" data-signature="${memberData.signature}"></canvas>
                 <button type="button" class="btn btn-sm btn-outline-primary edit-signature-btn" data-member-id="${memberData.member_id}" data-signature="${memberData.signature}">ערוך</button>` :
                '<span class="text-muted">אין חתימה</span>'
            }
        </td>
        <td>
            <button type="button" name="delete_member" class="btn btn-danger btn-sm delete-btn" data-member-id="${memberData.member_id}">מחק</button>
        </td>
    `;
    tbody.appendChild(newRow);
    
    // הוסף event listener לכפתור המחיקה החדש
    const deleteButton = newRow.querySelector('[name="delete_member"]');
    deleteButton.addEventListener('click', function(e) {
        e.preventDefault();
        const memberId = this.getAttribute('data-member-id');
        const memberName = this.closest('tr').querySelector('td:first-child').textContent;
        deleteMember(memberId, memberName);
    });
}

// פונקציה להוספת עובד עם AJAX
function addMember() {
    const name = document.getElementById('name').value.trim();
    const idNumber = document.getElementById('id_number').value.trim();
    const role = document.getElementById('role').value.trim();
    const signature = canvasToBase64('signature_canvas');
    
    console.log('addMember called with:', { name, idNumber, role, signature: signature ? 'exists' : 'empty' });
    
    if (!name || !idNumber || !role) {
        showErrorAlert('יש למלא את כל השדות');
        return;
    }
    
    if (!signature || signature === 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==') {
        showErrorAlert('יש לצייר חתימה');
        return;
    }
    
    const formData = new FormData();
    formData.append('add_member', '1');
    formData.append('name', name);
    formData.append('id_number', idNumber);
    formData.append('role', role);
    formData.append('signature', signature);
    
    console.log('Sending add request...');
    
    fetch(window.location.href, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Add response status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('Add response data:', data);
        if (data.success) {
            showSuccessAlert(data.message);
            // נקה את השדות
            document.getElementById('name').value = '';
            document.getElementById('id_number').value = '';
            document.getElementById('role').value = '';
            clearCanvas('signature_canvas');
            // הוסף את העובד החדש לטבלה
            addMemberToTable(data.member);
            // טען את החתימה החדשה
            if (data.member.signature) {
                setTimeout(() => {
                    loadSignatureToCanvas(`signature_${data.member.member_id}`, data.member.signature);
                }, 100);
            }
        } else {
            showErrorAlert(data.error);
        }
    })
    .catch(error => {
        console.error('Add error:', error);
        showErrorAlert('אירעה שגיאה בהוספת העובד');
    });
}

// משתנים גלובליים לחתימה
let isDrawing = false;
let currentSignatureCanvas = null;
let currentSignatureContext = null;
let currentMemberId = null;

// פונקציה לאתחול canvas חתימה
function initSignatureCanvas(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    
    const ctx = canvas.getContext('2d');
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    
    // הסר event listeners קודמים אם יש
    canvas.removeEventListener('mousedown', startDrawing);
    canvas.removeEventListener('mousemove', draw);
    canvas.removeEventListener('mouseup', stopDrawing);
    canvas.removeEventListener('mouseout', stopDrawing);
    canvas.removeEventListener('touchstart', handleTouchStart);
    canvas.removeEventListener('touchmove', handleTouchMove);
    canvas.removeEventListener('touchend', stopDrawing);
    
    // אירועי עכבר
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseout', stopDrawing);
    
    // אירועי מגע (למכשירים ניידים)
    canvas.addEventListener('touchstart', handleTouchStart);
    canvas.addEventListener('touchmove', handleTouchMove);
    canvas.addEventListener('touchend', stopDrawing);
    
    return { canvas, ctx };
}

// פונקציות לציור
function startDrawing(e) {
    isDrawing = true;
    draw(e);
}

function draw(e) {
    if (!isDrawing) return;
    
    e.preventDefault();
    const rect = currentSignatureCanvas.getBoundingClientRect();
    const x = (e.clientX || e.touches[0].clientX) - rect.left;
    const y = (e.clientY || e.touches[0].clientY) - rect.top;
    
    currentSignatureContext.lineTo(x, y);
    currentSignatureContext.stroke();
    currentSignatureContext.beginPath();
    currentSignatureContext.moveTo(x, y);
}

function stopDrawing() {
    isDrawing = false;
    currentSignatureContext.beginPath();
}

// פונקציות לטיפול במגע
function handleTouchStart(e) {
    e.preventDefault();
    const touch = e.touches[0];
    const mouseEvent = new MouseEvent('mousedown', {
        clientX: touch.clientX,
        clientY: touch.clientY
    });
    currentSignatureCanvas.dispatchEvent(mouseEvent);
}

function handleTouchMove(e) {
    e.preventDefault();
    const touch = e.touches[0];
    const mouseEvent = new MouseEvent('mousemove', {
        clientX: touch.clientX,
        clientY: touch.clientY
    });
    currentSignatureCanvas.dispatchEvent(mouseEvent);
}

// פונקציה לניקוי canvas
function clearCanvas(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // עדכן את השדה הנסתר
    const signatureInput = document.getElementById('signature');
    if (signatureInput) {
        signatureInput.value = '';
    }
}

// פונקציה להמרת canvas ל-base64
function canvasToBase64(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return '';
    
    return canvas.toDataURL('image/png');
}

// פונקציה לטעינת חתימה ל-canvas
function loadSignatureToCanvas(canvasId, signatureData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !signatureData) return;
    
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.onload = function() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
    img.src = signatureData;
}

// פונקציה להצגת חתימות בטבלה
function displaySignatures() {
    const signatureDisplays = document.querySelectorAll('.signature-display');
    signatureDisplays.forEach(canvas => {
        const signatureData = canvas.getAttribute('data-signature');
        if (signatureData && canvas.id) {
            loadSignatureToCanvas(canvas.id, signatureData);
        }
    });
}

// פונקציה לעריכת חתימה
function editSignature(memberId, currentSignature) {
    currentMemberId = memberId;
    
    // אתחל את ה-canvas בעריכה
    const result = initSignatureCanvas('edit_signature_canvas');
    if (result) {
        currentSignatureCanvas = result.canvas;
        currentSignatureContext = result.ctx;
    }
    
    // טען את החתימה הנוכחית אם קיימת
    if (currentSignature) {
        loadSignatureToCanvas('edit_signature_canvas', currentSignature);
    } else {
        clearCanvas('edit_signature_canvas');
    }
    
    // הצג את ה-modal
    $('#editSignatureModal').modal('show');
}

// פונקציה לשמירת חתימה מעודכנת
function saveUpdatedSignature() {
    const signatureData = canvasToBase64('edit_signature_canvas');
    
    if (!signatureData || signatureData === 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==') {
        showErrorAlert('יש לצייר חתימה לפני השמירה');
        return;
    }
    
    const formData = new FormData();
    formData.append('update_signature', '1');
    formData.append('member_id', currentMemberId);
    formData.append('signature', signatureData);
    
    fetch(window.location.href, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessAlert(data.message);
            // עדכן את הטבלה
            location.reload();
        } else {
            showErrorAlert(data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showErrorAlert('אירעה שגיאה בעדכון החתימה');
    });
}

// הוסף event listeners כשהדף נטען
document.addEventListener('DOMContentLoaded', function() {
    // אתחל את canvas החתימה הראשי
    const result = initSignatureCanvas('signature_canvas');
    if (result) {
        currentSignatureCanvas = result.canvas;
        currentSignatureContext = result.ctx;
    }
    
    // הצג חתימות קיימות בטבלה
    displaySignatures();
    
    // הוסף validation לקלט מספר תעודת זהות - רק מספרים
    const idNumberInput = document.getElementById('id_number');
    if (idNumberInput) {
        idNumberInput.addEventListener('input', function(e) {
            // הסר כל תו שאינו מספר
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    }
    
    // הוסף event listener לטופס ההוספה
    const addForm = document.querySelector('form');
    if (addForm) {
        addForm.addEventListener('submit', function(e) {
            e.preventDefault();
            addMember();
        });
    }
    
    // כפתור ניקוי חתימה ראשי
    const clearSignatureBtn = document.getElementById('clear_signature');
    if (clearSignatureBtn) {
        clearSignatureBtn.addEventListener('click', function() {
            clearCanvas('signature_canvas');
        });
    }
    
    // כפתור ניקוי חתימה בעריכה
    const clearEditSignatureBtn = document.getElementById('clear_edit_signature');
    if (clearEditSignatureBtn) {
        clearEditSignatureBtn.addEventListener('click', function() {
            clearCanvas('edit_signature_canvas');
        });
    }
    
    // כפתור שמירת חתימה
    const saveSignatureBtn = document.getElementById('save_signature');
    if (saveSignatureBtn) {
        saveSignatureBtn.addEventListener('click', saveUpdatedSignature);
    }
    
    // event listeners לכפתורי עריכת חתימה
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('edit-signature-btn')) {
            const memberId = e.target.getAttribute('data-member-id');
            const signature = e.target.getAttribute('data-signature');
            editSignature(memberId, signature);
        }
    });
    
    // הוסף event listeners לכפתורי המחיקה
    const deleteButtons = document.querySelectorAll('[name="delete_member"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const memberId = this.getAttribute('data-member-id');
            const memberName = this.closest('tr').querySelector('td:first-child').textContent;
            deleteMember(memberId, memberName);
        });
    });
    
    // הוסף event listeners לכפתורי סגירת alerts
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('close')) {
            e.target.closest('.alert').remove();
        }
    });
}); 