document.addEventListener('DOMContentLoaded', function() {
    const qrInput = document.querySelector('input[name="qr_code"]');
    const skuInput = document.querySelector('input[name="sku"]');
    const errorMessage = document.getElementById('sku-error');
    const searchButton = document.querySelector('button[name="action"][value="search"]');

    // קבלת רשימת המק"טים המאושרים
    const skuOptions = document.querySelectorAll('#sku-options option');
    const validSkus = new Set();
    skuOptions.forEach(option => {
        validSkus.add(option.value);
    });

    // ולידציה בשדה ה-SKU בזמן הקלדה
    skuInput.addEventListener('input', function() {
        const value = this.value.trim();
        if (value && !validSkus.has(value)) {
            errorMessage.style.display = 'block';
        } else {
            errorMessage.style.display = 'none';
        }
    });

    // ולידציה כשעוזבים את שדה ה-SKU
    skuInput.addEventListener('blur', function() {
        const value = this.value.trim();
        if (value && !validSkus.has(value)) {
            errorMessage.style.display = 'block';
            this.value = '';
        } else {
            errorMessage.style.display = 'none';
        }
    });

    // טיפול בהדבקה או סריקה של QR בפורמט 123:3
    qrInput.addEventListener('change', function(e) {
        const value = e.target.value.trim();

        if (value.includes(':')) {
            const parts = value.split(':');
            if (parts.length === 2) {
                const [serial, sku] = parts.map(x => x.trim());

                qrInput.value = serial;
                skuInput.value = sku;

                if (sku && !validSkus.has(sku)) {
                    errorMessage.style.display = 'block';
                    skuInput.value = '';
                } else {
                    errorMessage.style.display = 'none';
                    if (sku) {
                        searchButton.click();
                    }
                }
            }
        }
    });
});