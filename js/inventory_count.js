// ספירת מלאי - JavaScript
document.addEventListener('DOMContentLoaded', function() {
    let isCondensedHeader = false;
    let isAutoScrolling = false;
    let scrollTimer = null;
    const checkboxes = document.querySelectorAll('.tag-check');
    const selectAllBtn = document.getElementById('select-all-btn');
    const deselectAllBtn = document.getElementById('deselect-all-btn');
    const exitInventoryBtn = document.getElementById('exit-inventory-btn');
    const searchInput = document.getElementById('search-input');
    const clearSearchBtn = document.getElementById('clear-search-btn');
    const searchResultsInfo = document.getElementById('search-results-info');
    const resultsCount = document.getElementById('results-count');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const totalTagsEl = document.getElementById('total-tags');
    const foundTagsEl = document.getElementById('found-tags');
    const missingTagsEl = document.getElementById('missing-tags');
    const completionMessage = document.getElementById('completion-message');
    const completionTotal = document.getElementById('completion-total');
    const completionFound = document.getElementById('completion-found');

    let totalTags = checkboxes.length;
    let checkedCount = 0;

    // נקה את הספירה כשעוזבים את הדף
    window.addEventListener('beforeunload', function() {
        // רק אם הספירה הושלמה
        if (checkedCount === totalTags && totalTags > 0) {
            clearSavedStatus();
        }
    });

    // נקה את הספירה כשעוברים לדף אחר
    window.addEventListener('pagehide', function() {
        if (checkedCount === totalTags && totalTags > 0) {
            clearSavedStatus();
        }
    });

    // אתחול
    updateStats();
    
    // בדוק אם זה כניסה חדשה לדף (לא רענון)
    if (performance.navigation.type === 1) { // TYPE_NAVIGATE
        // נקה את הספירה הקודמת
        clearSavedStatus();
    } else {
        // טען את הספירה השמורה
        loadSavedStatus();
    }

    // מאזין לכל checkbox ול-label המקביל
    checkboxes.forEach(checkbox => {
        // אפשר סימון בעזרת Enter על ה-checkbox בפוקוס
        checkbox.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.click();
            }
        });

        // תמיכה ב-Enter/Space על ה-label (שהוא האלמנט הנראה והפוקוסבילי)
        const label = checkbox.closest('.tag-checkbox')?.querySelector('.checkbox-label');
        if (label) {
            label.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    checkbox.click();
                }
            });
        }

        checkbox.addEventListener('change', function() {
            const tagItem = this.closest('.tag-item');
            const tagId = tagItem.dataset.tagId;
            const isChecked = this.checked;

            // עדכן את המראה הויזואלי
            if (isChecked) {
                tagItem.classList.add('checked');
                checkedCount++;
            } else {
                tagItem.classList.remove('checked');
                checkedCount--;
            }

            // עדכן aria-checked על ה-label הנוכחי
            if (label) {
                label.setAttribute('aria-checked', isChecked ? 'true' : 'false');
            }

            // שמור את הסטטוס
            saveTagStatus(tagId, isChecked);

            // עדכן סטטיסטיקות
            updateStats();

            // בדוק אם הושלמה הספירה
            checkCompletion();

            // אם סומן כ"נמצא" – גלול לתג הבא והתמקד ב-checkbox הבא
            if (isChecked) {
                const tagItems = Array.from(document.querySelectorAll('.tag-item'));
                const currentIndex = tagItems.indexOf(tagItem);

                // מצא את התג הבא שאינו נסתר
                let nextItem = null;
                for (let i = currentIndex + 1; i < tagItems.length; i++) {
                    if (!tagItems[i].classList.contains('hidden')) {
                        nextItem = tagItems[i];
                        break;
                    }
                }

                if (nextItem) {
                    // גלילה מדויקת כך שהתג הבא יופיע מתחת לכותרת
                    const rect = nextItem.getBoundingClientRect();
                    const header = document.querySelector('.header');
                    const headerHeight = header ? header.offsetHeight : 0;
                    const targetTop = window.scrollY + rect.top - headerHeight - 10;

                    isAutoScrolling = true;
                    window.scrollTo({ top: targetTop, left: 0, behavior: 'smooth' });

                    const nextCheckbox = nextItem.querySelector('.tag-check');
                    const nextLabel = nextItem.querySelector('.checkbox-label');
                    if (nextLabel) {
                        setTimeout(() => {
                            nextLabel.focus({ preventScroll: true });
                            isAutoScrolling = false;
                        }, 320);
                    } else if (nextCheckbox) {
                        setTimeout(() => {
                            nextCheckbox.focus({ preventScroll: true });
                            isAutoScrolling = false;
                        }, 320);
                    } else {
                        setTimeout(() => { isAutoScrolling = false; }, 320);
                    }
                }
            }
        });
    });

    // כפתור סמן הכל
    selectAllBtn.addEventListener('click', function() {
        checkboxes.forEach(checkbox => {
            if (!checkbox.checked) {
                checkbox.checked = true;
                checkbox.dispatchEvent(new Event('change'));
            }
        });
    });

    // כפתור בטל הכל
    deselectAllBtn.addEventListener('click', function() {
        checkboxes.forEach(checkbox => {
            if (checkbox.checked) {
                checkbox.checked = false;
                checkbox.dispatchEvent(new Event('change'));
            }
        });
    });

    // כפתור יציאה מספירת מלאי
    exitInventoryBtn.addEventListener('click', function() {
        if (confirm('האם אתה בטוח שברצונך לצאת מספירת המלאי?')) {
            // נקה את הספירה
            clearSavedStatus();
            // עבור לדף הבית
            window.location.href = '/index';
        }
    });

    // פונקציית חיפוש
    function performSearch() {
        const searchTerm = searchInput.value.trim().toLowerCase();
        const tagItems = document.querySelectorAll('.tag-item');
        let visibleCount = 0;

        if (searchTerm === '') {
            // אם אין טקסט חיפוש, הצג הכל
            tagItems.forEach(tag => {
                tag.classList.remove('hidden', 'highlight');
            });
            searchResultsInfo.style.display = 'none';
            clearSearchBtn.style.display = 'none';
            return;
        }

        // חיפוש לפי מספר סידורי
        tagItems.forEach(tag => {
            const serialNumber = tag.querySelector('.detail-value')?.textContent.toLowerCase() || '';
            
            if (serialNumber.includes(searchTerm)) {
                tag.classList.remove('hidden');
                tag.classList.add('highlight');
                visibleCount++;
                
                // הסר את ה-highlight אחרי שנייה
                setTimeout(() => {
                    tag.classList.remove('highlight');
                }, 1000);
            } else {
                tag.classList.add('hidden');
                tag.classList.remove('highlight');
            }
        });

        // הצג מידע על תוצאות
        resultsCount.textContent = visibleCount;
        searchResultsInfo.style.display = 'block';
        clearSearchBtn.style.display = 'block';
    }

    // חיפוש בזמן הקלדה
    searchInput.addEventListener('input', performSearch);

    // כפתור ניקוי חיפוש
    clearSearchBtn.addEventListener('click', function() {
        searchInput.value = '';
        performSearch();
        searchInput.focus();
    });

    function updateStats() {
        const foundCount = checkedCount;
        const missingCount = totalTags - checkedCount;
        const percentage = totalTags > 0 ? Math.round((foundCount / totalTags) * 100) : 0;

        // עדכן את הסטטיסטיקות
        foundTagsEl.textContent = foundCount;
        missingTagsEl.textContent = missingCount;
        totalTagsEl.textContent = totalTags;

        // עדכן את פס ההתקדמות
        progressFill.style.width = percentage + '%';
        progressText.textContent = percentage + '% הושלם';

        // עדכן את צבע פס ההתקדמות
        if (percentage === 100) {
            progressFill.style.background = 'linear-gradient(135deg, #4CAF50, #45a049)';
        } else if (percentage >= 75) {
            progressFill.style.background = 'linear-gradient(135deg, #8BC34A, #689F38)';
        } else if (percentage >= 50) {
            progressFill.style.background = 'linear-gradient(135deg, #FFC107, #FF8F00)';
        } else {
            progressFill.style.background = 'linear-gradient(135deg, #FF9800, #F57C00)';
        }
    }

    function checkCompletion() {
        if (checkedCount === totalTags && totalTags > 0) {
            setTimeout(() => {
                showCompletionMessage();
            }, 500);
        }
    }

    function showCompletionMessage() {
        completionTotal.textContent = totalTags;
        completionFound.textContent = checkedCount;
        completionMessage.style.display = 'flex';

        // הוסף אנימציה
        setTimeout(() => {
            completionMessage.querySelector('.message-content').style.animation = 'slideIn 0.5s ease';
        }, 100);
    }

    function saveTagStatus(tagId, isPresent) {
        fetch('/update_inventory_status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                tag_id: tagId,
                is_present: isPresent
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('שגיאה בשמירת סטטוס:', data.error);
            }
        })
        .catch(error => {
            console.error('שגיאה בשמירת סטטוס:', error);
        });
    }

    function loadSavedStatus() {
        fetch('/get_inventory_status')
        .then(response => response.json())
        .then(data => {
            if (data.tags) {
                data.tags.forEach(tag => {
                    const checkbox = document.getElementById(`tag-${tag[0]}`);
                    if (checkbox && tag[8] === 1) { // is_present
                        checkbox.checked = true;
                        checkbox.dispatchEvent(new Event('change'));
                    }
                });
            }
        })
        .catch(error => {
            console.error('שגיאה בטעינת סטטוס:', error);
        });
    }

    function clearSavedStatus() {
        fetch('/update_inventory_status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                clear_all: true
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('שגיאה בניקוי סטטוס:', data.error);
            }
        })
        .catch(error => {
            console.error('שגיאה בניקוי סטטוס:', error);
        });
    }

    // סגור הודעת השלמה בלחיצה על הרקע
    completionMessage.addEventListener('click', function(e) {
        if (e.target === completionMessage) {
            completionMessage.style.display = 'none';
        }
    });

    // סגור הודעת השלמה בלחיצה על ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && completionMessage.style.display === 'flex') {
            completionMessage.style.display = 'none';
        }
    });

    // כפתור חזרה לדף הבית
    const backToHomeBtn = document.getElementById('back-to-home-btn');
    if (backToHomeBtn) {
        backToHomeBtn.addEventListener('click', function() {
            // נקה את הספירה לפני החזרה
            clearSavedStatus();
            // עבור לדף הבית
            window.location.href = '/index';
        });
    }

    // הוסף אפקטים ויזואליים נוספים
    checkboxes.forEach(checkbox => {
        const tagItem = checkbox.closest('.tag-item');
        
        // אפקט hover
        tagItem.addEventListener('mouseenter', function() {
            if (!checkbox.checked) {
                this.style.transform = 'translateY(-2px)';
            }
        });
        
        tagItem.addEventListener('mouseleave', function() {
            if (!checkbox.checked) {
                this.style.transform = 'translateY(0)';
            }
        });
    });

    // הוסף אנימציה לכפתורים
    [selectAllBtn, deselectAllBtn].forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // הוסף אפקט לחיצה לכפתורים
    [selectAllBtn, deselectAllBtn].forEach(btn => {
        btn.addEventListener('mousedown', function() {
            this.style.transform = 'translateY(0)';
        });
        
        btn.addEventListener('mouseup', function() {
            this.style.transform = 'translateY(-2px)';
        });
    });

    // הוסף אפקטים לכפתור חזרה לדף הבית
    if (backToHomeBtn) {
        backToHomeBtn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        backToHomeBtn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
        
        backToHomeBtn.addEventListener('mousedown', function() {
            this.style.transform = 'translateY(0)';
        });
        
        backToHomeBtn.addEventListener('mouseup', function() {
            this.style.transform = 'translateY(-2px)';
        });
    }
    
    // אנימציית כניסה לתגים
    function animateTagsEntry() {
        const tagItems = document.querySelectorAll('.tag-item');
        tagItems.forEach((tag, index) => {
            tag.style.opacity = '0';
            tag.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                tag.style.transition = 'all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                tag.style.opacity = '1';
                tag.style.transform = 'translateY(0)';
            }, index * 80);
        });
    }
    
    // הפעל אנימציה בטעינה
    setTimeout(animateTagsEntry, 100);

    // שינוי עיצוב הדף בעת גלילה – היסטרזיס ו-debounce למניעת קפיצות
    function handleScrollStylingImmediate() {
        if (isAutoScrolling) return;
        const y = window.scrollY || document.documentElement.scrollTop || 0;
        if (!isCondensedHeader && y > 160) {
            isCondensedHeader = true;
            document.body.classList.add('scrolled');
        } else if (isCondensedHeader && y < 80) {
            isCondensedHeader = false;
            document.body.classList.remove('scrolled');
        }
    }
    function handleScrollStyling() {
        if (scrollTimer) clearTimeout(scrollTimer);
        scrollTimer = setTimeout(handleScrollStylingImmediate, 80);
    }
    window.addEventListener('scroll', handleScrollStyling, { passive: true });
    handleScrollStylingImmediate();

    // במעבר לדף – התמקדות ב-checkbox הראשון שלא מסומן
    const firstUnchecked = Array.from(document.querySelectorAll('.tag-item .tag-check')).find(cb => !cb.checked);
    if (firstUnchecked) {
        setTimeout(() => firstUnchecked.focus({ preventScroll: true }), 200);
    }
});
