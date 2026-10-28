"""Try the Phase 3 analytics engine on Online Retail II from the command line.

Usage (from the project folder):
    python scripts/demo_analytics.py
    python scripts/demo_analytics.py --start 2011-01-01 --end 2011-03-31
    python scripts/demo_analytics.py --country France --top 5 --freq week
"""

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

# Allow "python scripts/demo_analytics.py" to import the src package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analytics import breakdowns, kpis  # noqa: E402
from src.analytics.definitions import ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES  # noqa: E402
from src.analytics.errors import AnalyticsError  # noqa: E402
from src.analytics.prepare import prepare_transactions  # noqa: E402
from src.data.online_retail import load_online_retail_ii  # noqa: E402


def money(value) -> str:
    return "n/a" if value is None else f"GBP {value:,.2f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", help="first date, e.g. 2011-01-01 (inclusive)")
    parser.add_argument("--end", help="last date, e.g. 2011-12-31 (inclusive)")
    parser.add_argument("--country", action="append", help="limit to a country (repeatable)")
    parser.add_argument("--top", type=int, default=10, help="how many products to rank")
    parser.add_argument("--freq", default="month", choices=list(breakdowns.FREQUENCIES))
    args = parser.parse_args()

    pd.set_option("display.width", 140)
    pd.set_option("display.max_columns", 12)
    pd.set_option("display.max_rows", 120)
    pd.set_option("display.float_format", "{:,.2f}".format)

    began = time.perf_counter()
    df = prepare_transactions(load_online_retail_ii(), ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES)
    print(f"Loaded and prepared {len(df):,} rows in {time.perf_counter() - began:.1f}s")

    try:
        selected = kpis.filter_transactions(df, start=args.start, end=args.end, countries=args.country)
        summary = kpis.kpi_summary(selected)
        print(f"\nFilters: start={args.start or 'first'}  end={args.end or 'last'}  "
              f"country={args.country or 'all'}  ({len(selected):,} rows)")

        print("\n=== Headline KPIs ===")
        print(f"Net sales (revenue)   {money(summary['net_sales'])}")
        print(f"Gross product sales   {money(summary['gross_sales'])}")
        print(f"Cancellations         {money(summary['cancellations'])}")
        print(f"Orders                {summary['orders']:,}")
        print(f"Average order value   {money(summary['average_order_value'])}")
        print(f"Units sold            {summary['units_sold']:,}")
        rate = summary["cancellation_rate"]
        print(f"Cancellation rate     {'n/a' if rate is None else f'{rate:.2%}'}")
        print(f"Active customers      {summary['active_customers']:,} "
              f"(sales with a customer ID: {(summary['identified_sales_share'] or 0):.1%})")

        print(f"\n=== Top {args.top} products by net sales ===")
        top = breakdowns.top_n(selected, "product", n=args.top)
        print(top[["rank", "product_id", "product_name", "net_sales", "orders", "units_sold"]].to_string(index=False))

        print(f"\n=== Sales by {args.freq} ===")
        trend = breakdowns.sales_over_time(selected, args.freq, coverage_start=args.start, coverage_end=args.end)
        print(trend[["period", "net_sales", "orders", "average_order_value", "is_partial"]].to_string(index=False))

        print("\n=== Asking for something the data cannot answer ===")
        kpis.gross_profit(selected)
    except AnalyticsError as error:
        print(f"Cannot answer: {error}")


if __name__ == "__main__":
    main()
