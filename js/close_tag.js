document.addEventListener('DOMContentLoaded', function () {
    const confirmButton = document.getElementById('confirm-checks');
    const closeTagButton = document.getElementById('close-tag-btn');

    // בדוק אם יש תמונה או מודל אישור רגיל
    const drawingModal = document.getElementById('drawing-modal');
    const regularModal = document.getElementById('custom-confirm');
    
    // מצב התחלתי: כפתור אישור בצבע אדום, כפתור סגירה נעול
    confirmButton.style.background = 'linear-gradient(45deg, #dc3545, #ff6b6b, #dc3545)';
    confirmButton.style.boxShadow = 'none';
    closeTagButton.disabled = true;

    // אם יש מודל ציור (יש תמונה)
    if (drawingModal) {
        const canvas = document.getElementById('drawing-canvas');
        const checkImage = document.getElementById('check-image');
        const checkerSelect = document.querySelector('select[name="checker"]');
        const clearBtn = document.getElementById('clear-drawing');
        const saveBtn = document.getElementById('save-drawing');
        const cancelBtn = document.getElementById('cancel-drawing');
        const warning = document.getElementById('drawing-warning');
        const zoomInBtn = document.getElementById('zoom-in');
        const zoomOutBtn = document.getElementById('zoom-out');
        const zoomResetBtn = document.getElementById('zoom-reset');
        const zoomLevelLabel = document.getElementById('zoom-level');
        const zoomWarning = document.getElementById('zoom-warning');
        const tagId = drawingModal.getAttribute('data-tag-id');
        const saveUrl = drawingModal.getAttribute('data-save-url');
        const ctx = canvas.getContext('2d');

        let imageLoaded = false;
        let snapshotSaved = false;
        let hasMarks = false;
        let originalWidth = 0;
        let originalHeight = 0;
        let baseScale = 1;
        let imageScale = 1;
        let zoomFactor = 1;
        let targetWidth = 0;
        let targetHeight = 0;

        const MIN_ZOOM = 0.8;
        const MAX_ZOOM = 3;
        const ZOOM_STEP = 0.2;
        const DEFAULT_ZOOM = 1.25;

        const MARK_TYPES = {
            CHECK: 'check',
            X: 'x'
        };

        const marks = [];

        function extractLines(value) {
            if (!value) {
                return [];
            }
            if (Array.isArray(value)) {
                return value.map(line => String(line).trim()).filter(line => line.length > 0);
            }
            return String(value)
                .split(/\n|\|/)
                .map(line => line.trim())
                .filter(line => line.length > 0);
        }

        let textEntries = [];
        const textMapAttr = canvas.getAttribute('data-text-map');

        if (textMapAttr) {
            try {
                const parsed = JSON.parse(textMapAttr);
                if (Array.isArray(parsed)) {
                    textEntries = parsed.map((entry) => {
                        const lines = extractLines(entry.lines && entry.lines.length > 0 ? entry.lines : entry.text);
                        return {
                            id: entry.id ? String(entry.id) : null,
                            lines,
                            x: Number.isFinite(entry.x) ? entry.x : 50,
                            y: Number.isFinite(entry.y) ? entry.y : 50,
                            fontSize: Number.isFinite(entry.fontSize) ? entry.fontSize : 20,
                            fontFamily: entry.fontFamily || 'Arial',
                            color: entry.color || '#000000',
                            bold: Boolean(entry.bold),
                            lineSpacing: Number.isFinite(entry.lineSpacing) ? entry.lineSpacing : 6,
                            background: entry.background !== undefined ? entry.background : 'rgba(255, 255, 255, 0.8)'
                        };
                    }).filter(entry => entry.lines.length > 0);
                }
            } catch (err) {
                console.error('Could not parse data-text-map JSON:', err);
            }
        }

        if (textEntries.length === 0) {
            const fallbackRaw = canvas.getAttribute('data-text') || '';
            const fallbackLines = extractLines(fallbackRaw);
            if (fallbackLines.length > 0) {
                textEntries.push({
                    id: null,
                    lines: fallbackLines,
                    x: parseInt(canvas.getAttribute('data-text-x')) || 50,
                    y: parseInt(canvas.getAttribute('data-text-y')) || 50,
                    fontSize: parseInt(canvas.getAttribute('data-text-size')) || 20,
                    fontFamily: canvas.getAttribute('data-text-font') || 'Arial',
                    color: canvas.getAttribute('data-text-color') || '#000000',
                    bold: canvas.getAttribute('data-text-bold') === 'true',
                    lineSpacing: parseInt(canvas.getAttribute('data-text-line-spacing')) || 6,
                    background: canvas.getAttribute('data-text-background') || 'rgba(255, 255, 255, 0.8)'
                });
            }
        }

        const hasTextEntries = textEntries.length > 0;
        
        const img = new Image();
        img.crossOrigin = 'anonymous';

        function drawPredefinedText(scale = 1) {
            if (!hasTextEntries) {
                return;
            }

            textEntries.forEach(entry => {
                const lines = entry.lines || [];
                if (lines.length === 0) {
                    return;
                }

                const fontSize = entry.fontSize * scale;
                const fontFamily = entry.fontFamily;
                const fontWeight = entry.bold ? 'bold' : 'normal';
                ctx.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
                ctx.fillStyle = entry.color;
                ctx.textAlign = 'right';
                ctx.textBaseline = 'top';

                const x = entry.x * scale;
                const y = entry.y * scale;
                const padding = 5 * scale;
                const lineHeight = fontSize + (entry.lineSpacing * scale);
                const lineWidths = lines.map(line => ctx.measureText(line).width);
                const maxLineWidth = Math.max(...lineWidths, 0);
                const totalHeight = lineHeight * lines.length;

                const background = entry.background || 'rgba(255, 255, 255, 0.8)';
                if (background && background !== 'none') {
                    ctx.fillStyle = background;
                    ctx.fillRect(
                        x - maxLineWidth - padding,
                        y - padding,
                        maxLineWidth + (padding * 2),
                        totalHeight + (padding * 2)
                    );
                    ctx.fillStyle = entry.color;
                }

                lines.forEach((line, index) => {
                    ctx.fillText(line, x, y + index * lineHeight);
                });
            });
        }

        function drawMark(mark) {
            if (!mark) {
                return;
            }
            const x = mark.x * targetWidth;
            const y = mark.y * targetHeight;
            const size = Math.max(targetWidth, targetHeight) * 0.015;
            ctx.save();
            ctx.lineWidth = Math.max(1, size * 0.08);
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            if (mark.type === MARK_TYPES.CHECK) {
                ctx.strokeStyle = '#15803d';
                ctx.beginPath();
                ctx.moveTo(x - size * 0.45, y);
                ctx.lineTo(x - size * 0.1, y + size * 0.35);
                ctx.lineTo(x + size * 0.55, y - size * 0.45);
                ctx.stroke();
            } else if (mark.type === MARK_TYPES.X) {
                ctx.strokeStyle = '#dc2626';
                ctx.beginPath();
                ctx.moveTo(x - size * 0.5, y - size * 0.5);
                ctx.lineTo(x + size * 0.5, y + size * 0.5);
                ctx.moveTo(x + size * 0.5, y - size * 0.5);
                ctx.lineTo(x - size * 0.5, y + size * 0.5);
                ctx.stroke();
            }
            ctx.restore();
        }

        function drawMarks() {
            if (!marks.length) {
                return;
            }
            marks.forEach(drawMark);
        }

        function refreshCanvas() {
            if (!imageLoaded || !targetWidth || !targetHeight) {
                return;
            }
            ctx.clearRect(0, 0, targetWidth, targetHeight);
            ctx.drawImage(img, 0, 0, targetWidth, targetHeight);
            if (hasTextEntries) {
                drawPredefinedText(imageScale);
            }
            drawMarks();
        }
        
        function setCanvasScale(scale) {
            if (!originalWidth || !originalHeight) {
                return;
            }
            imageScale = scale;
            targetWidth = originalWidth * scale;
            targetHeight = originalHeight * scale;
            canvas.width = targetWidth;
            canvas.height = targetHeight;
            refreshCanvas();
        }

        function loadImageToCanvas() {
            const imageSrc = checkImage ? checkImage.src : null;

            if (!imageSrc) {
                console.error('לא נמצא נתיב תמונה');
                return;
            }

            img.onload = function() {
                originalWidth = img.width;
                originalHeight = img.height;
                const maxWidth = Math.min(window.innerWidth * 0.95, originalWidth);
                const maxHeight = Math.min(window.innerHeight * 0.85, originalHeight);
                baseScale = Math.min(maxWidth / originalWidth, maxHeight / originalHeight);

                zoomFactor = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, DEFAULT_ZOOM));
                imageLoaded = true;
                setCanvasScale(baseScale * zoomFactor);
                updateZoomUI();
                hasMarks = marks.length > 0;
                updateSaveButton();
            };

            img.onerror = function() {
                console.error('שגיאה בטעינת התמונה');
                alert('שגיאה בטעינת תמונת הבדיקות');
            };

            img.src = imageSrc;
        }

        function updateZoomUI() {
            if (zoomLevelLabel) {
                zoomLevelLabel.textContent = `${Math.round(zoomFactor * 100)}%`;
            }
        }

        function applyZoom(delta) {
            if (marks.length > 0) {
                if (zoomWarning) {
                    zoomWarning.style.display = 'flex';
                    setTimeout(() => {
                        zoomWarning.style.display = 'none';
                    }, 3000);
                }
                return;
            }
            const newZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoomFactor + delta));
            if (newZoom === zoomFactor) {
                return;
            }
            zoomFactor = newZoom;
            setCanvasScale(baseScale * zoomFactor);
            updateZoomUI();
        }

        function resetZoom() {
            if (marks.length > 0) {
                if (zoomWarning) {
                    zoomWarning.style.display = 'flex';
                    setTimeout(() => {
                        zoomWarning.style.display = 'none';
                    }, 3000);
                }
                return;
            }
            zoomFactor = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, DEFAULT_ZOOM));
            setCanvasScale(baseScale * zoomFactor);
            updateZoomUI();
        }

        function getRelativePosition(clientX, clientY) {
            const rect = canvas.getBoundingClientRect();
            return {
                x: (clientX - rect.left) / rect.width,
                y: (clientY - rect.top) / rect.height
            };
        }

        function resetConfirmButtonVisual() {
            confirmButton.style.background = 'linear-gradient(45deg, #dc3545, #ff6b6b, #dc3545)';
            confirmButton.style.boxShadow = 'none';
            closeTagButton.disabled = true;
        }

        function addMark(type, clientX, clientY) {
            if (!imageLoaded) {
                return;
            }
            const { x, y } = getRelativePosition(clientX, clientY);
            if (x < 0 || x > 1 || y < 0 || y > 1) {
                return;
            }
            marks.push({ type, x, y });
            hasMarks = marks.length > 0;
            snapshotSaved = false;
            resetConfirmButtonVisual();
            updateSaveButton();
            refreshCanvas();
        }

        function handlePointerEvent(event) {
            if (!imageLoaded) {
                return;
            }
            event.preventDefault();
            if (event.type === 'mousedown') {
                if (event.button === 0) {
                    addMark(MARK_TYPES.CHECK, event.clientX, event.clientY);
                } else if (event.button === 2) {
                    addMark(MARK_TYPES.X, event.clientX, event.clientY);
                }
            }
        }

        function handleTouchEvent(event) {
            if (!imageLoaded) {
                return;
            }
            event.preventDefault();
            if (!event.touches || event.touches.length === 0) {
                return;
            }
            const touch = event.touches[0];
            addMark(MARK_TYPES.CHECK, touch.clientX, touch.clientY);
        }

        function updateSaveButton() {
            if (hasMarks) {
                saveBtn.disabled = false;
                if (warning) {
                    warning.style.display = 'none';
                }
            } else {
                saveBtn.disabled = true;
                if (warning) {
                    warning.style.display = 'block';
                }
            }
        }

        function captureCanvasSnapshot() {
            if (!imageLoaded || !targetWidth || !targetHeight) {
                return null;
            }
            refreshCanvas();
            return canvas.toDataURL('image/png');
        }

        function uploadSnapshot(imageData, options = {}) {
            const { showLoading = false } = options;

            if (!saveUrl || !tagId) {
                return Promise.reject(new Error('לא ניתן לשמור את דף הבדיקות. נתוני תג חסרים.'));
            }
            if (!imageData) {
                return Promise.reject(new Error('לא ניתן ליצור תמונה לשמירה.'));
            }

            let originalButtonHTML = null;
            if (showLoading && saveBtn) {
                originalButtonHTML = saveBtn.innerHTML;
                saveBtn.disabled = true;
                saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> שומר...';
            }

            return fetch(saveUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image_data: imageData
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (!data || !data.success) {
                        throw new Error(data && data.error ? data.error : 'שגיאה בשמירת דף הבדיקות');
                    }
                    return data;
                })
                .finally(() => {
                    if (showLoading && saveBtn && originalButtonHTML !== null) {
                        saveBtn.disabled = false;
                        saveBtn.innerHTML = originalButtonHTML;
                    }
                });
        }

        function updateTextEntry(entryId, value) {
            if (!entryId) {
                return false;
            }
            const normalizedLines = extractLines(value);
            let updated = false;
            textEntries.forEach(entry => {
                if (entry.id === entryId) {
                    entry.lines = normalizedLines;
                    updated = true;
                }
            });
            return updated;
        }

        canvas.addEventListener('contextmenu', function(event) {
            event.preventDefault();
        });
        canvas.addEventListener('mousedown', handlePointerEvent);
        canvas.addEventListener('touchstart', handleTouchEvent);

        canvas.addEventListener('touchmove', function(event) {
            event.preventDefault();
        }, { passive: false });
        
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', function() {
                applyZoom(ZOOM_STEP);
            });
        }

        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', function() {
                applyZoom(-ZOOM_STEP);
            });
        }

        if (zoomResetBtn) {
            zoomResetBtn.addEventListener('click', function() {
                resetZoom();
            });
        }

        clearBtn.addEventListener('click', function() {
            if (confirm('האם אתה בטוח שברצונך למחוק את כל הסימונים?')) {
                marks.length = 0;
                hasMarks = false;
                snapshotSaved = false;
                resetConfirmButtonVisual();
                refreshCanvas();
                updateSaveButton();
                if (zoomWarning) {
                    zoomWarning.style.display = 'none';
                }
            }
        });
        
        saveBtn.addEventListener('click', function() {
            if (!hasMarks) {
                if (warning) {
                warning.style.display = 'block';
                }
                return;
            }
            
            const snapshotData = captureCanvasSnapshot();
            if (!snapshotData) {
                alert('לא ניתן לשמור את דף הבדיקות. אנא נסה שוב.');
                return;
            }

            uploadSnapshot(snapshotData, { showLoading: true })
                .then(() => {
                    snapshotSaved = true;
            drawingModal.style.display = 'none';
            confirmButton.style.background = 'linear-gradient(45deg, #28a745, #34ce57, #28a745)';
            confirmButton.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
            closeTagButton.disabled = false;
                    if (warning) {
                        warning.style.display = 'none';
                    }
                })
                .catch(err => {
                    console.error('Failed to save final check snapshot:', err);
                    alert(err && err.message ? err.message : 'אירעה שגיאה בשמירת דף הבדיקות. אנא נסה שוב.');
                });
        });

        cancelBtn.addEventListener('click', function() {
            drawingModal.style.display = 'none';
            resetConfirmButtonVisual();
        });
        
        confirmButton.addEventListener('click', function () {
            drawingModal.style.display = 'block';
            if (zoomWarning) {
                zoomWarning.style.display = 'none';
            }
            
            if (!imageLoaded) {
                loadImageToCanvas();
            } else {
                refreshCanvas();
            }

            hasMarks = marks.length > 0;
            updateSaveButton();
        });

        if (checkerSelect) {
            const initialChecker = checkerSelect.value && checkerSelect.value.trim() ? checkerSelect.value.trim() : 'לא זמין';
            updateTextEntry('checker', initialChecker);

            checkerSelect.addEventListener('change', function() {
                const selectedValue = this.value && this.value.trim() ? this.value.trim() : 'לא זמין';
                const updated = updateTextEntry('checker', selectedValue);
                if (!updated) {
                    return;
                }

                if (!imageLoaded) {
                    return;
                }

                refreshCanvas();

                if (snapshotSaved && hasMarks) {
                    const snapshotData = canvas.toDataURL('image/png');
                    uploadSnapshot(snapshotData)
                        .then(() => {
                            snapshotSaved = true;
                        })
                        .catch(err => {
                            console.error('Failed to update snapshot after checker change:', err);
                            alert(err && err.message ? err.message : 'אירעה שגיאה בעדכון דף הבדיקות. אנא פתח מחדש את הסימונים ושמור שוב.');
                        });
                }
            });
        }
    }
    // אם יש מודל רגיל (אין תמונה)
    else if (regularModal) {
        const yesBtn = document.getElementById('confirm-yes');
        const noBtn = document.getElementById('confirm-no');

        confirmButton.addEventListener('click', function () {
            regularModal.style.display = 'block';
        });

        yesBtn.addEventListener('click', function () {
            regularModal.style.display = 'none';
            confirmButton.style.background = 'linear-gradient(45deg, #28a745, #34ce57, #28a745)';
            confirmButton.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
            closeTagButton.disabled = false;
        });

        noBtn.addEventListener('click', function () {
            regularModal.style.display = 'none';
            confirmButton.style.background = 'linear-gradient(45deg, #dc3545, #ff6b6b, #dc3545)';
            confirmButton.style.boxShadow = 'none';
            closeTagButton.disabled = true;
        });
    }
});
