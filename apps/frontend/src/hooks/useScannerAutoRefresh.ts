import { useState, useEffect } from 'react';
import axios from 'axios';

export const useScannerAutoRefresh = (token: string | null, market: string, timeframe: string) => {
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        if (!token) return;
        try {
            const response = await axios.get('/api/scanner/results', {
                params: { market, timeframe, latest_only: true },
                headers: { Authorization: `Bearer ${token}` }
            });
            setResults(response.data);
        } catch (err) {
            console.error("Auto-refresh failed", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // Auto-refresh setiap 30 detik agar data selalu terbaru tanpa klik tombol
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, [token, market, timeframe]);

    return { results, loading, refresh: fetchData };
};
