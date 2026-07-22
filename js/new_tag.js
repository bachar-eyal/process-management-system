function markAllOk() {
    const checkboxes = document.querySelectorAll('input[name="test_results[]"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
    });
}

// הודעת הצלחה תוצג רק אם הטופס נשלח בהצלחה (ללא שגיאות)
// אם יש שגיאה, הטופס לא יישלח ולכן לא תוצג הודעת הצלחה

// רשימת תקלות מאושרות
let approvedIssues = [];

// פונקציה לבדיקת תקלה קיימת
function isIssueApproved(issueText) {
    return approvedIssues.includes(issueText);
}

// פונקציה לוולידציה של הטופס
document.querySelector('form').addEventListener('submit', function(e) {
    const issueInput = document.getElementById('issue_input');
    const issueText = issueInput.value.trim();
    
    if (!issueText) {
        e.preventDefault();
        alert('חובה להזין תיאור תקלה');
        return false;
    }
    
    // בדוק אם התקלה מאושרת
    if (!isIssueApproved(issueText)) {
        e.preventDefault();
        alert(`תיאור התקלה "${issueText}" לא נמצא במערכת. אנא בחר תקלה מהרשימה או הוסף אותה בדף ניהול תקלות.`);
        return false;
    }
    
    // אם הכל תקין, אפשר שליחה רגילה (ללא הודעת הצלחה מיידית)
    // הודעת ההצלחה תוצג רק אחרי שהשרת מחזיר תשובה חיובית
});

// הוסף event listeners כשהדף נטען
document.addEventListener('DOMContentLoaded', function() {
    // קבל את רשימת התקלות המאושרות מה-datalist
    const datalist = document.getElementById('issues_list');
    const options = datalist.querySelectorAll('option');
    approvedIssues = Array.from(options).map(option => option.value);
    
    console.log('Approved issues:', approvedIssues);
});