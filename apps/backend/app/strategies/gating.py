from app.core.database import supabase

async def is_strategy_allowed(strategy_name: str, timeframe: str) -> bool:
    """
    Checks if a strategy is allowed to produce signals based on backtest performance.
    FAIL CLOSED principle.
    """
    try:
        # Fetch the latest backtest run for this strategy/timeframe
        resp = supabase.table("backtest_runs") \
            .select("verdict, expectancy, sample_size") \
            .eq("strategy", strategy_name) \
            .eq("timeframe", timeframe) \
            .order("run_date", desc=True) \
            .limit(1) \
            .execute()

        if not resp.data:
            return False # NOT_TESTED -> BLOCKED

        run = resp.data[0]

        # Policy:
        # 1. Must be PROVEN_POSITIVE
        # 2. Expectancy > 0
        # 3. Sample size >= 30
        if run['verdict'] == "PROVEN_POSITIVE" and run['expectancy'] > 0 and run['sample_size'] >= 30:
            return True

        return False
    except:
        return False # On error, fail closed
