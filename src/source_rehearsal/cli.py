import argparse
import os
from dataclasses import asdict
from pathlib import Path

from . import demo
from .discovery import Candidate, SearchClient
from .engine import checks, compare, describe
from .evidence import to_html, to_json
from .network import HttpClient
from .publishers import download, our_world_in_data, world_bank


def main():
    parser = argparse.ArgumentParser(
        description="Run a synthetic rehearsal or verify real search/publisher downloads."
    )
    parser.add_argument("--scenario", choices=demo.SCENARIOS, default="Threshold flip")
    parser.add_argument("--output", type=Path, default=Path("reports/demo"))
    live = parser.add_mutually_exclusive_group()
    live.add_argument(
        "--check-public-sources",
        action="store_true",
        help="Download real 2020–2022 IND/USA/BRA data; no SerpApi key required.",
    )
    live.add_argument(
        "--check-discovery",
        action="store_true",
        help="Verify search/discovered downloads using SERPAPI_API_KEY from your shell.",
    )
    args = parser.parse_args()
    if args.check_discovery:
        key = os.environ.get("SERPAPI_API_KEY", "").strip()
        if not key:
            parser.error(
                "Set SERPAPI_API_KEY in your shell; never pass or publish the key in evidence."
            )
        contract = demo.demo_contract()
        baseline_url = "https://data.worldbank.org/indicator/SP.POP.TOTL"
        result = {
            "contract": asdict(contract),
            "baseline_source": baseline_url,
            **SearchClient(key, Path(".cache/search.sqlite")).discover(contract, baseline_url),
        }
        results = []
        for candidate in result["candidates"]:
            try:
                data = download(Candidate(**candidate), contract)
                results.append(
                    {"status": "downloaded", **describe(data), "checks": checks(data, contract)}
                )
            except ValueError as exc:
                results.append(
                    {"status": "failed", "publisher": candidate["publisher"], "error": str(exc)}
                )
        result["downloads"] = results
        result["status"] = (
            "verified search and downloads"
            if results
            and not result["errors"]
            and all(r["status"] == "downloaded" for r in results)
            else "incomplete"
        )
        result["limits"] = (
            "Verification only: no baseline download, metadata approval, or report rehearsal. "
            "Inspect checks before accepting coverage. Cached search evidence is labelled."
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.with_suffix(".json").write_text(to_json(result), encoding="utf-8")
        print(to_json(result))
        raise SystemExit(int(result["status"] == "incomplete"))
    if args.check_public_sources:
        results = {}
        for name, loader in [("World Bank", world_bank), ("Our World in Data", our_world_in_data)]:
            try:
                data = loader(demo.demo_contract(), HttpClient())
                results[name] = {
                    "status": "downloaded",
                    **describe(data),
                    "checks": checks(data, demo.demo_contract()),
                }
            except ValueError as exc:
                results[name] = {"status": "failed", "error": str(exc)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.with_suffix(".json").write_text(to_json(results), encoding="utf-8")
        print(to_json(results))
        print("Download check only; metadata review and SerpApi discovery remain separate.")
        raise SystemExit(int(any(result["status"] == "failed" for result in results.values())))
    result = compare(demo.baseline(), demo.candidate(args.scenario), demo.demo_contract())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(to_json(result), encoding="utf-8")
    args.output.with_suffix(".html").write_text(to_html(result), encoding="utf-8")
    print("SYNTHETIC DEMONSTRATION — not real population data")
    print(result["verdict"])
    print(result["summary"])
    print(f"Evidence: {args.output.with_suffix('.html')}")


if __name__ == "__main__":
    main()
