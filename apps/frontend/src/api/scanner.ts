export const getScannerResults = async (market = 'idx', timeframe = '1d', limit = 10) => {
  const response = await fetch(`/api/scanner/results?market=${market}&timeframe=${timeframe}&limit=${limit}&latest_only=true`);
  if (!response.ok) throw new Error('Failed to fetch scanner results');
  return response.json();
};
