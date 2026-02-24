const pieCtx = document.getElementById('pieChart').getContext('2d');
new Chart(pieCtx, {
    type:'pie',
    data:{
        labels: {{ category_totals.keys()|list }},
        datasets:[{ data: {{ category_totals.values()|list }}, backgroundColor:['#9b59b6','#8e44ad','#d6c1ff','#b89fff','#6c5ce7','#a29bfe'] }]
    },
    options:{ responsive:true, maintainAspectRatio:false }
});

const barCtx = document.getElementById('barChart').getContext('2d');
new Chart(barCtx, {
    type:'bar',
    data:{
        labels: {{ expenses|map(attribute='date')|list }},
        datasets:[{ label:'Amount Spent', data: {{ expenses|map(attribute='amount')|list }}, backgroundColor:'#8e44ad' }]
    },
    options:{ responsive:true, maintainAspectRatio:false }
});