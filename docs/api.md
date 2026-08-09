# API Specification

Base URL (dev): `http://localhost:8000/api`
Format: JSON. Semua timestamp dalam ISO 8601 UTC.

## 1. Health

```
GET /health
```
```json
{ "status": "ok", "version": "0.1.0" }
```

## 2. Stocks

```
GET /stocks?market=idx|us&search=BBCA
```
```json
{
  "results": [
    { "symbol": "BBCA.JK", "name": "Bank Central Asia", "market": "idx" }
  ]
}
```

```
GET /stocks/{symbol}/candles?timeframe=daily&start=2025-01-01&end=2026-08-01
```
```json
{
  "symbol": "BBCA.JK",
  "timeframe": "daily",
  "candles": [
    { "time": "2026-08-07T00:00:00Z", "open": 9800, "high": 9950,
      "low": 9750, "close": 9900, "volume": 45000000 }
  ]
}
```

## 3. Scanner

```
GET /scanner/morning?market=idx|us|all
```
Menjalankan/menampilkan hasil morning scan terbaru.
```json
{
  "generated_at": "2026-08-08T01:00:00Z",
  "candidates": [
    {
      "symbol": "BBCA.JK",
      "strategy": "correction",
      "score": 94,
      "status": "WAIT_FOR_CANDLE_CONFIRMATION"
    }
  ]
}
```

```
GET /scanner/live?symbols=BBCA.JK,BBRI.JK
```
Status live terbaru untuk kandidat/watchlist tertentu (dipanggil polling
dari frontend, atau untuk debugging scheduler backend).

## 4. Setups

```
GET /setups/{symbol}
```
Detail setup yang sedang aktif untuk 1 simbol, termasuk breakdown skor
per komponen (sesuai `strategy-rules.md` §9).
```json
{
  "symbol": "BBCA.JK",
  "strategy": "bullish_divergence",
  "status": "READY",
  "score": 94,
  "score_breakdown": {
    "major_trend": true,
    "five_movement": true,
    "divergence": true,
    "indicator_confirmation": true,
    "fibonacci_zone": true,
    "lower_tf_confirmation": true,
    "candle_confirmation": true,
    "risk_reward": true
  },
  "risk": {
    "entry": 9900, "stop_loss": 9700, "take_profit": 10800,
    "risk_pct": 2.02, "reward_pct": 9.09, "risk_reward_ratio": 4.5
  },
  "status_history": [
    { "status": "WATCH", "at": "2026-08-05T02:00:00Z" },
    { "status": "APPROACHING", "at": "2026-08-06T07:00:00Z" },
    { "status": "READY", "at": "2026-08-08T02:15:00Z" }
  ]
}
```

```
GET /setups?status=READY&market=idx
```
List semua setup aktif, filter by status/market/strategy.

## 5. Watchlist

```
GET /watchlist
POST /watchlist         { "symbol": "NVDA" }
DELETE /watchlist/{symbol}
```

## 6. Charts (overlay data untuk frontend chart component)

```
GET /charts/{symbol}/overlay?timeframe=daily
```
```json
{
  "symbol": "BBCA.JK",
  "swings": [
    { "time": "2026-07-01T00:00:00Z", "price": 9500, "type": "swing_low" }
  ],
  "movements": [
    { "from": "2026-07-01T00:00:00Z", "to": "2026-07-10T00:00:00Z",
      "movement_number": 3, "type": "major" }
  ],
  "fibonacci": {
    "type": "retracement",
    "low": 9500, "high": 10200,
    "levels": { "0.382": 9932, "0.5": 9850, "0.618": 9768 }
  },
  "divergence_points": [
    { "price_point": { "time": "...", "price": 9600 },
      "indicator_point": { "time": "...", "value": 32 },
      "indicator": "RSI" }
  ]
}
```

## 7. Backtest

```
POST /backtest/run
```
Body:
```json
{
  "strategy": "bullish_divergence",
  "symbols": ["BBCA.JK", "BBRI.JK"],
  "timeframe": "daily",
  "start": "2023-01-01",
  "end": "2026-08-01"
}
```
Response:
```json
{
  "run_id": "bt_20260808_001",
  "status": "queued"
}
```

```
GET /backtest/{run_id}
```
```json
{
  "run_id": "bt_20260808_001",
  "status": "completed",
  "metrics": {
    "total_trades": 42,
    "win_rate": 0.55,
    "avg_risk_reward": 2.3,
    "avg_return_pct": 4.1,
    "max_drawdown_pct": -12.5,
    "profit_factor": 1.8,
    "expectancy": 1.4
  },
  "trades": [
    { "symbol": "BBCA.JK", "entry_time": "2024-03-01T00:00:00Z",
      "entry": 8500, "exit": 9200, "exit_reason": "TP_HIT", "return_pct": 8.2 }
  ]
}
```

## 8. Feedback (koreksi manual, non-ML)

```
POST /feedback
```
Body:
```json
{
  "symbol": "BBCA.JK",
  "type": "missed_setup",
  "strategy": "hidden_bullish",
  "note": "Scanner tidak deteksi ini padahal ada pattern triangle jelas",
  "chart_time": "2026-08-05T00:00:00Z"
}
```

```
GET /feedback?type=missed_setup
```
Dipakai manual untuk kalibrasi ulang `config/pivot_thresholds.yaml` dan
`config/scoring_weights.yaml` — tidak otomatis mengubah parameter.

## 9. Error Format (konsisten di semua endpoint)

```json
{
  "error": {
    "code": "SYMBOL_NOT_FOUND",
    "message": "Symbol BBXX.JK tidak ditemukan di universe"
  }
}
```

## 10. Catatan Desain

- Semua endpoint scanner/setup **read-only** dari sisi hasil — tidak ada
  endpoint yang melakukan order/eksekusi trading (di luar scope proyek).
- Response tidak pernah mengandung rekomendasi "BUY"/"SELL" eksplisit —
  hanya status + score, sesuai constraint di `strategy-rules.md` §11.