"""CLI: ``python -m data_gen --out data/raw [--preset small] [--seed 7]``."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date

from .config import PRESETS, get_config
from .generator import generate
from .writer import SYNTHETIC_NOTICE, write_dataset


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m data_gen", description=SYNTHETIC_NOTICE)
    p.add_argument("--out", default="data/raw", help="output directory (default: data/raw)")
    p.add_argument("--preset", default="default", choices=sorted(PRESETS))
    p.add_argument("--format", default="parquet", choices=["parquet", "csv"], dest="fmt")
    p.add_argument("--seed", type=int, help="random seed (default: 42)")
    p.add_argument("--start-date", type=date.fromisoformat, help="YYYY-MM-DD")
    p.add_argument("--end-date", type=date.fromisoformat, help="YYYY-MM-DD")
    p.add_argument("--stores", type=int, dest="n_stores")
    p.add_argument("--products", type=int, dest="n_products")
    p.add_argument("--customers", type=int, dest="n_customers")
    args = p.parse_args(argv)

    cfg = get_config(
        args.preset,
        seed=args.seed,
        start_date=args.start_date,
        end_date=args.end_date,
        n_stores=args.n_stores,
        n_products=args.n_products,
        n_customers=args.n_customers,
    )
    t0 = time.perf_counter()
    ds = generate(cfg)
    write_dataset(ds, args.out, cfg, fmt=args.fmt)
    print(f"Generated synthetic data ({args.preset}, seed={cfg.seed}) in "
          f"{time.perf_counter() - t0:.1f}s -> {args.out}")
    for name, n in ds.row_counts().items():
        print(f"  {name:<20} {n:>10,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
