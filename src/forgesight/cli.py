"""A small, reproducible command interface for the complete model lifecycle."""

import argparse
import json

from .paths import ARTIFACTS, DATA, ROOT


def main():
    parser = argparse.ArgumentParser(description="ForgeSight model and inspection workbench")
    parser.add_argument(
        "command", choices=["download", "fit", "evaluate", "setup", "serve", "activate"]
    )
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8010, type=int)
    parser.add_argument("--model-id")
    args = parser.parse_args()
    dataset = DATA / "datasets"
    if args.command in {"download", "setup"}:
        from .data import download_dataset

        download_dataset(dataset)
    if args.command in {"fit", "setup"}:
        from .training import fit

        fit(dataset, ARTIFACTS, device=args.device)
    if args.command in {"evaluate", "setup"}:
        from .evaluation import evaluate
        from .paths import atomic_json
        from .registry import read_bundle

        report = evaluate(dataset, ARTIFACTS, device=args.device)
        atomic_json(ROOT / "reports" / "bottle-baseline.json", report)
        folder, metadata = read_bundle(ARTIFACTS)
        atomic_json(ROOT / "reports" / "model-card.json", metadata)
        atomic_json(
            ROOT / "reports" / "split.json",
            json.loads((folder / "split.json").read_text(encoding="utf-8")),
        )
    if args.command == "activate":
        from .registry import activate

        if not args.model_id:
            parser.error("--model-id is required")
        activate(ARTIFACTS, args.model_id)
        print(
            json.dumps({"active": args.model_id, "note": "Restart the server to load this model."})
        )
    if args.command == "serve":
        import os

        import uvicorn

        os.environ["FORGESIGHT_DEVICE"] = args.device
        uvicorn.run("forgesight.api:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
