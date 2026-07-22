$(document).ready(function () {
    if (document.getElementById('tagsTable')) {
        $('#tagsTable').DataTable({
            pageLength: 10,
            lengthChange: false,
            order: [[4, 'desc']],
            pagingType: 'full_numbers',
            language: {
                paginate: {
                    first: 'ראשון',
                    previous: 'קודם',
                    next: 'הבא',
                    last: 'אחרון'
                },
                info: 'מציג _START_ עד _END_ מתוך _TOTAL_ פריטים',
                search: 'חיפוש:'
            }
        });
    }

    if (document.getElementById('statusBarChart')) {
        const ctxBar = document.getElementById('statusBarChart').getContext('2d');
        new Chart(ctxBar, {
            type: 'bar',
            data: {
                labels: Object.keys(window.reportData.statusCounts),
                datasets: [{
                    label: '',
                    data: Object.values(window.reportData.statusCounts),
                    backgroundColor: (context) => {
                        const chart = context.chart;
                        const { ctx, chartArea } = chart;
                        if (!chartArea) return;
                        const index = context.dataIndex;
                        const labels = Object.keys(window.reportData.statusCounts);
                        const status = labels[index];
                        if (status === 'שמיש') return '#28a745';
                        else if (status === 'תקול') return '#dc3545';
                        else return '#ffc107';
                    },
                    borderColor: (context) => {
                        const labels = Object.keys(window.reportData.statusCounts);
                        const status = labels[context.dataIndex];
                        return status === 'שמיש' ? '#1e7e34' : status === 'תקול' ? '#c82333' : '#e0a800';
                    },
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                aspectRatio: 1.3,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'מספר תגים',
                            font: { size: 16, weight: 'bold', family: 'Roboto' }
                        },
                        ticks: { font: { size: 14, family: 'Roboto' } }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'סטטוס',
                            font: { size: 16, weight: 'bold', family: 'Roboto' }
                        },
                        ticks: { font: { size: 14, family: 'Roboto' } }
                    }
                },
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'חלוקת תגים לפי סטטוס',
                        font: { size: 20, weight: 'bold', family: 'Roboto' },
                        color: '#1a2e44',
                        padding: { top: 10, bottom: 20 }
                    }
                }
            }
        });
    }

    if (document.getElementById('openCloseTagsBySKUChart')) {
        const ctxOpenClose = document.getElementById('openCloseTagsBySKUChart').getContext('2d');
        new Chart(ctxOpenClose, {
            type: 'bar',
            data: {
                labels: window.reportData.skuSummaryKeys,
                datasets: [
                    {
                        label: 'תגים שנפתחו',
                        data: window.reportData.openedCounts,
                        backgroundColor: '#f4a261',
                        borderColor: '#e07628',
                        borderWidth: 2,
                        borderRadius: 8
                    },
                    {
                        label: 'תגים שנסגרו',
                        data: window.reportData.closedCounts,
                        backgroundColor: '#b4a7d6',
                        borderColor: '#8e7cc3',
                        borderWidth: 2,
                        borderRadius: 8
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                aspectRatio: 1.3,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'מספר תגים',
                            font: { size: 16, weight: 'bold', family: 'Roboto' }
                        },
                        ticks: { font: { size: 14, family: 'Roboto' } }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'מק"ט',
                            font: { size: 16, weight: 'bold', family: 'Roboto' }
                        },
                        ticks: { font: { size: 14, family: 'Roboto' } }
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    title: {
                        display: true,
                        text: 'תגים שנפתחו ונסגרו לפי מק"ט בתקופה',
                        font: { size: 20, weight: 'bold', family: 'Roboto' },
                        color: '#1a2e44',
                        padding: { top: 10, bottom: 20 }
                    }
                }
            }
        });
    }

    if (document.getElementById('monthlyOpenTagsChart')) {
        const ctxMonthly = document.getElementById('monthlyOpenTagsChart').getContext('2d');
        new Chart(ctxMonthly, {
            type: 'line',
            data: {
                labels: window.reportData.timeLabels,
                datasets: [{
                    label: 'תגים שנפתחו',
                    data: window.reportData.timeData,
                    borderColor: '#ff9999',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                aspectRatio: 1.5,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'מספר תגים שנפתחו',
                            font: { size: 16, weight: 'bold', family: 'Roboto' }
                        },
                        ticks: { font: { size: 14, family: 'Roboto' } }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'חודשים',
                            font: { size: 16, weight: 'bold', family: 'Roboto' }
                        },
                        ticks: { 
                            font: { size: 12, family: 'Roboto' },
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                },
                plugins: {
                    legend: { display: true, position: 'top' },
                    title: {
                        display: true,
                        text: 'תגים שנפתחו לפי חודשים',
                        font: { size: 20, weight: 'bold', family: 'Roboto' },
                        color: '#1a2e44',
                        padding: { top: 10, bottom: 20 }
                    }
                }
            }
        });
    }

    $('.toggle-open-tags').on('click', function () {
        const sku = $(this).data('sku');
        const $list = $('#open-tags-' + sku);
        const $button = $(this);
        $list.toggle();
        $button.text($list.is(':visible') ? '▲' : '▼');
    });
});