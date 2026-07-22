$(document).ready(function () {
    $('#tagsTable').DataTable({
        pageLength: 10, // מספר פריטים לעמוד
        lengthChange: false, // הסתרת אפשרות שינוי מספר פריטים לעמוד
        order: [[5, 'desc']], // מיון ראשוני לפי תאריך (אינדקס 5) בסדר יורד
        pagingType: 'full_numbers', // הצגת כפתורי "ראשון", "קודם", "הבא", "אחרון"
        searching: false, // השבתת תיבת החיפוש
        language: {
            paginate: {
                first: 'ראשון',
                previous: 'קודם',
                next: 'הבא',
                last: 'אחרון'
            },
            info: 'מציג _START_ עד _END_ מתוך _TOTAL_ פריטים',
            emptyTable: 'אין נתונים זמינים בטבלה'
        },
        drawCallback: function () {
            $('html, body').animate({
                scrollTop: $('#tagsTable').offset().top
            }, 300);
        },
        columnDefs: [
            { 
                targets: [0, 3, 4], // עמודות פעולות, תיאור תקלה, פעולות שבוצעו
                orderable: false // השבתת מיון
            },
            { 
                targets: [1, 2], // עמודות מספר סידורי, מק"ט
                orderable: true // הפעלת מיון
            },
            { 
                targets: 5, // עמודה 5 (תאריך)
                orderable: true, // הפעלת מיון
                orderDataType: 'dom-text', // מיון לפי ערך ה-data-sort
                type: 'string' // סוג נתונים למיון
            },
            { 
                targets: 6, // עמודה 6 (ימים פתוחים)
                orderable: true, // הפעלת מיון
                orderDataType: 'dom-text', // מיון לפי ערך ה-data-sort
                type: 'num' // סוג נתונים למיון
            }
        ]
    });
});