"""CLI entrypoint for running the research agent.

Usage:
    python -m src.research_agent.run_research_agent [--run-id RUN_ID] [--max-iterations N]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from src.research_agent.deep_agent import run_research_session
from src.research_agent.loop.ralph_loop import LoopConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Widby research agent")
    parser.add_argument(
        "--scoring-input",
        type=str,
        default=None,
        help="Path to a JSON file with scoring results to analyze",
    )
    parser.add_argument("--run-id", type=str, default=None, help="Run identifier")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum loop iterations (default: 10)",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=50.0,
        help="Maximum API budget in USD (default: 50.0)",
    )
    parser.add_argument(
        "--graph-path",
        type=str,
        default=None,
        help="Path to persistent knowledge graph JSON",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to write the output report (default: stdout)",
    )
    args = parser.parse_args()

    scoring_results: dict = {}
    if args.scoring_input:
        with open(args.scoring_input) as f:
            scoring_results = json.load(f)
    else:
        scoring_results = _demo_scoring_results()

    config = LoopConfig(
        max_iterations=args.max_iterations,
        budget_limit_usd=args.budget,
    )
    if args.run_id:
        config.run_id = args.run_id

    logger.info("Starting research session: run_id=%s", config.run_id)
    result = run_research_session(
        scoring_results=scoring_results,
        config=config,
        graph_path=args.graph_path,
    )

    report = result.get("report", "")
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        logger.info("Report written to %s", args.output)
    else:
        print(report)

    outcome = result.get("outcome")
    if outcome:
        logger.info(
            "Session complete: %d iterations, stop_reason=%s, cost=$%.2f",
            outcome.get("iterations_completed", 0),
            outcome.get("stop_reason", "unknown"),
            outcome.get("total_cost_usd", 0),
        )


def _demo_scoring_results() -> dict:
    """Provide demo scoring data for testing without real API calls."""
    return {
        "metros": [
            {
                "cbsa_code": "38060",
                "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
                "scores": {
                    "demand": 72,
                    "organic_competition": 45,
                    "local_competition": 58,
                    "monetization": 81,
                    "ai_resilience": 92,
                    "opportunity": 71,
                },
                "signals": {
                    "effective_search_volume": 4500,
                    "avg_top5_da": 35,
                    "local_pack_review_count_avg": 42,
                    "avg_cpc": 8.50,
                    "aio_trigger_rate": 0.06,
                },
            },
            {
                "cbsa_code": "47900",
                "cbsa_name": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
                "scores": {
                    "demand": 85,
                    "organic_competition": 30,
                    "local_competition": 35,
                    "monetization": 78,
                    "ai_resilience": 88,
                    "opportunity": 62,
                },
                "signals": {
                    "effective_search_volume": 7200,
                    "avg_top5_da": 52,
                    "local_pack_review_count_avg": 95,
                    "avg_cpc": 12.00,
                    "aio_trigger_rate": 0.08,
                },
            },
            {
                "cbsa_code": "12060",
                "cbsa_name": "Atlanta-Sandy Springs-Alpharetta, GA",
                "scores": {
                    "demand": 68,
                    "organic_competition": 55,
                    "local_competition": 62,
                    "monetization": 70,
                    "ai_resilience": 90,
                    "opportunity": 69,
                },
                "signals": {
                    "effective_search_volume": 3800,
                    "avg_top5_da": 28,
                    "local_pack_review_count_avg": 35,
                    "avg_cpc": 7.20,
                    "aio_trigger_rate": 0.05,
                },
            },
        ]
    }


if __name__ == "__main__":
    main()
