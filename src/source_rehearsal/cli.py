import argparse
from pathlib import Path

from . import demo
from .engine import compare
from .evidence import to_html, to_json


def main():
    parser = argparse.ArgumentParser(
        description="Run a labelled synthetic SourceRehearsal scenario."
    )
    parser.add_argument("--scenario", choices=demo.SCENARIOS, default="Threshold flip")
    parser.add_argument("--output", type=Path, default=Path("reports/demo"))
    args = parser.parse_args()
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
