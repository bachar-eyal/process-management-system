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

// פונקציה להוספת תקלה לטבלה
function addIssueToTable(issueData) {
    const tbody = document.querySelector('tbody');
    const newRow = document.createElement('tr');
    
    const solutionText = issueData.solution ? 
        `<div class="solution-text">${issueData.solution.replace(/\n/g, '<br>')}</div><button type="button" class="btn btn-sm btn-outline-primary edit-solution-btn ml-2" data-issue-id="${issueData.issue_id}" data-current-solution="${issueData.solution}"><i class="fas fa-edit"></i></button>` :
        `<button type="button" class="btn btn-sm btn-outline-primary edit-solution-btn" data-issue-id="${issueData.issue_id}" data-current-solution=""><i class="fas fa-plus"></i></button>`;
    
    newRow.innerHTML = `
        <td>${issueData.description || '-'}</td>
        <td>${solutionText}</td>
        <td>
            <button type="button" name="delete_issue" class="btn btn-danger btn-sm delete-btn" data-issue-id="${issueData.issue_id}">מחק</button>
        </td>
    `;
    tbody.appendChild(newRow);
    
    // הוסף event listener לכפתור המחיקה החדש
    const deleteButton = newRow.querySelector('[name="delete_issue"]');
    deleteButton.addEventListener('click', function(e) {
        e.preventDefault();
        const issueId = this.getAttribute('data-issue-id');
        const issueDescription = this.closest('tr').querySelector('td:first-child').textContent;
        deleteIssue(issueId, issueDescription);
    });
    
    // הוסף event listener לכפתור עריכת פתרון החדש
    const editSolutionButton = newRow.querySelector('.edit-solution-btn');
    if (editSolutionButton) {
        editSolutionButton.addEventListener('click', function() {
            const issueId = this.getAttribute('data-issue-id');
            const currentSolution = this.getAttribute('data-current-solution');
            
            document.getElementById('editIssueId').value = issueId;
            document.getElementById('editSolutionText').value = currentSolution;
            $('#editSolutionModal').modal('show');
        });
    }
}

// פונקציה להוספת תקלה עם AJAX
function addIssue() {
    const description = document.getElementById('description').value.trim();
    const solution = document.getElementById('solution').value.trim();
    
    console.log('addIssue called with:', { description, solution });
    
    if (!description) {
        showErrorAlert('יש להזין תיאור תקלה');
        return;
    }
    
    const formData = new FormData();
    formData.append('add_issue', '1');
    formData.append('description', description);
    formData.append('solution', solution);
    
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
            document.getElementById('description').value = '';
            document.getElementById('solution').value = '';
            // הוסף את התקלה החדשה לטבלה
            addIssueToTable(data.issue);
        } else {
            showErrorAlert(data.error);
        }
    })
    .catch(error => {
        console.error('Add error:', error);
        showErrorAlert('אירעה שגיאה בהוספת התקלה');
    });
}

// פונקציה למחיקת תקלה עם AJAX
function deleteIssue(issueId, issueDescription) {
    console.log('deleteIssue called with:', { issueId, issueDescription });
    
    if (confirm(`האם אתה בטוח שאתה רוצה למחוק את תקלה ${issueDescription}?`)) {
        const formData = new FormData();
        formData.append('delete_issue', '1');
        formData.append('issue_id', issueId);
        
        console.log('Sending request with issue_id:', issueId);
        
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
                const row = document.querySelector(`[data-issue-id="${issueId}"]`).closest('tr');
                row.remove();
            } else {
                showErrorAlert(data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showErrorAlert('אירעה שגיאה במחיקת התקלה');
        });
    }
}

// הוסף event listeners כשהדף נטען
document.addEventListener('DOMContentLoaded', function() {
    // הוסף event listener לטופס ההוספה
    const addForm = document.querySelector('form');
    if (addForm) {
        addForm.addEventListener('submit', function(e) {
            e.preventDefault();
            addIssue();
        });
    }
    
    // הוסף event listeners לכפתורי המחיקה
    const deleteButtons = document.querySelectorAll('[name="delete_issue"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const issueId = this.getAttribute('data-issue-id');
            const issueDescription = this.closest('tr').querySelector('td:first-child').textContent;
            deleteIssue(issueId, issueDescription);
        });
    });
    
    // הוסף event listeners לכפתורי סגירת alerts
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('close')) {
            e.target.closest('.alert').remove();
        }
    });
    
    // הוסף event listeners לכפתורי עריכת פתרון
    const editSolutionButtons = document.querySelectorAll('.edit-solution-btn');
    editSolutionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const issueId = this.getAttribute('data-issue-id');
            const currentSolution = this.getAttribute('data-current-solution');
            
            // מלא את המודל עם הנתונים הנוכחיים
            document.getElementById('editIssueId').value = issueId;
            document.getElementById('editSolutionText').value = currentSolution;
            
            // פתח את המודל
            $('#editSolutionModal').modal('show');
        });
    });
    
    // הוסף event listener לכפתור שמירת פתרון
    const saveSolutionBtn = document.getElementById('saveSolutionBtn');
    if (saveSolutionBtn) {
        saveSolutionBtn.addEventListener('click', function() {
            saveSolution();
        });
    }
});

// פונקציה לשמירת פתרון
function saveSolution() {
    const issueId = document.getElementById('editIssueId').value;
    const solution = document.getElementById('editSolutionText').value.trim();
    
    if (!issueId) {
        showErrorAlert('שגיאה: לא נמצא מזהה תקלה');
        return;
    }
    
    const formData = new FormData();
    formData.append('edit_solution', '1');
    formData.append('issue_id', issueId);
    formData.append('solution', solution);
    
    fetch(window.location.href, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessAlert(data.message);
            $('#editSolutionModal').modal('hide');
            
            // עדכן את הטבלה
            setTimeout(function() {
                location.reload();
            }, 1000);
        } else {
            showErrorAlert(data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showErrorAlert('אירעה שגיאה בשמירת הפתרון');
    });
} 