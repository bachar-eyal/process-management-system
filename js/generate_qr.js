document.addEventListener('DOMContentLoaded', function() {
            const skuInput = document.querySelector('input[name="sku"]');
            const errorMessage = document.getElementById('sku-error');
            const qrForm = document.getElementById('qrForm');
            const formFields = document.getElementById('formFields');
            const qrContainer = document.getElementById('qrContainer');
            const skuOptions = document.querySelectorAll('#sku-options option');
            const validSkus = new Set();
            skuOptions.forEach(option => {
                validSkus.add(option.value);
            });

            // ולידציה בעת הקלדה בשדה SKU
            skuInput.addEventListener('input', function() {
                const value = this.value.trim();
                if (value && !validSkus.has(value)) {
                    errorMessage.style.display = 'block';
                } else {
                    errorMessage.style.display = 'none';
                }
            });

            // ולידציה בעת עזיבת שדה SKU
            skuInput.addEventListener('blur', function() {
                const value = this.value.trim();
                if (value && !validSkus.has(value)) {
                    errorMessage.style.display = 'block';
                    this.value = '';
                } else {
                    errorMessage.style.display = 'none';
                }
            });

            // טיפול בשליחת הטופס
            qrForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const value = skuInput.value.trim();
                
                // בדיקה אם ה-SKU תקין לפני שליחת הטופס
                if (!value || !validSkus.has(value)) {
                    errorMessage.style.display = 'block';
                    skuInput.value = '';
                    return;
                }

                const formData = new FormData(this);
                fetch(this.action, {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.text())
                .then(html => {
                    document.open();
                    document.write(html);
                    document.close();
                    const qrContainer = document.getElementById('qrContainer');
                    const formFields = document.getElementById('formFields');
                    if (qrContainer) {
                        qrContainer.classList.add('active');
                        formFields.classList.add('hidden');
                        setTimeout(() => formFields.style.display = 'none', 300);
                    }
                })
                .catch(error => console.error('Error:', error));
            });
        });

        // פונקציית הדפסת QR
        function printQR() {
            const qrImage = document.getElementById('qrImage').src;
            const printWindow = window.open('', '', 'height=600,width=800');
            printWindow.document.write(`
                <html><head><title>הדפסת QR</title>
                <style>
                    body { margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
                    img { max-width: 100%; max-height: 100%; }
                </style></head>
                <body><img src="${qrImage}" onload="window.print();window.close()"></body></html>
            `);
            printWindow.document.close();
        }