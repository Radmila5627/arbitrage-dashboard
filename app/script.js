async function loadData() {
  const response = await fetch('orders.csv');
  const data = await response.text();

  const rows = data.trim().split('\n').slice(1); // Preskoči zaglavlje
  const content = document.getElementById('content');

  rows.reverse().forEach(row => {
    const [timestamp, token, buyExchange, sellExchange, buyPrice, sellPrice, profit, profitPercentage] = row.split(',');

    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <h2>${token}</h2>
      <p><strong>Vrijeme:</strong> ${timestamp}</p>
      <p><strong>Kupi na:</strong> ${buyExchange} (${buyPrice})</p>
      <p><strong>Prodaj na:</strong> ${sellExchange} (${sellPrice})</p>
      <p><strong>Profit:</strong> ${profit} (${profitPercentage}%)</p>
    `;
    content.appendChild(card);
  });
}

window.onload = loadData;
