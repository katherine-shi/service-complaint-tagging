"""Command line entry point: python run.py [fetch|tag|report|all]"""
import argparse

from dotenv import load_dotenv

from src import db, fetch, report, tag


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=["fetch", "tag", "report", "all"])
    parser.add_argument("--limit", type=int, default=300, help="max complaints to tag per run")
    parser.add_argument("--workers", type=int, default=8, help="concurrent LLM requests while tagging")
    parser.add_argument("--mock", action="store_true", help="offline keyword tagger, for testing only")
    args = parser.parse_args()

    conn = db.connect()
    if args.step in ("fetch", "all"):
        fetch.run(conn)
    if args.step in ("tag", "all"):
        tag.run(conn, limit=args.limit, mock=args.mock, workers=args.workers)
    if args.step in ("report", "all"):
        report.run(conn)


if __name__ == "__main__":
    main()
