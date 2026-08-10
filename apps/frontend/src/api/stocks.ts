export const getStocks = async (symbol?: string) => {
  const url = symbol ? `/api/stocks/?symbol=${symbol}` : '/api/stocks/';
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to fetch stocks');
  return response.json();
};

export const getRecentIPOs = async (limit = 5) => {
  const response = await fetch(`/api/stocks/ipo?limit=${limit}`);
  if (!response.ok) throw new Error('Failed to fetch recent IPOs');
  return response.json();
};
