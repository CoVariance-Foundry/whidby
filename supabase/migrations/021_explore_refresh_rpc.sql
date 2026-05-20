-- RPC to refresh the explore_market_cells materialized view.
-- Called after bulk scoring or individual score updates to surface new data.

CREATE OR REPLACE FUNCTION public._refresh_explore_market_cells()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.explore_market_cells;
END;
$$;

REVOKE ALL ON FUNCTION public._refresh_explore_market_cells() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public._refresh_explore_market_cells() TO service_role;
