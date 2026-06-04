#!/usr/bin/env python3
"""
core/cli.py
===========
Command-line interface for SimplePod Swarm.

ELI5: This is the labeled switch panel at the front door.
      Instead of crawling into the basement to flip breakers,
      you just read the label and press the button.

Usage:
    simplepod server        # Start the FastAPI backend
    simplepod orbitscribe   # Run relationship analysis demo
    simplepod test          # Run the test suite
    simplepod version       # Show version info
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

__version__ = "2.6.0"

PROJECT_ROOT = Path(__file__).parent.parent


def server(args: argparse.Namespace) -> int:
    """ELI5: Flip the main breaker and start the generator."""
    import uvicorn

    print(f"\n🔥 SimplePod Swarm v{__version__}")
    print("Starting server on http://127.0.0.1:8000")
    print("API docs: http://127.0.0.1:8000/docs")
    print("OrbitScribe: http://127.0.0.1:8000/unified/demo/orbitscribe/report\n")

    uvicorn.run(
        "interfaces.web_ui.backend.main:app",
        host="0.0.0.0" if args.host is None else args.host,
        port=args.port,
        log_level="info",
        reload=args.reload,
    )
    return 0


def orbitscribe(args: argparse.Namespace) -> int:
    """ELI5: Call the master electrician for a full diagnostic."""
    from core.unified.orbitscribe_demo import OrbitScribeEngine

    print(f"\n🔍 OrbitScribe Relationship Engine v{__version__}")
    print(f"Mode: {args.mode}\n")

    engine = OrbitScribeEngine(use_llm=(args.mode == "llm"))
    report = engine.generate_full_report()

    print(f"Device Owner: {report.device_owner}")
    print(f"Risk Level:   {report.risk_level.upper()}")
    print(f"LLM Used:     {'YES' if report.llm_used else 'NO (synthetic)'}")
    print()

    print("ATTACHMENT ANALYSES:")
    for a in report.attachment_analyses:
        print(f"  {a.subject} ↔ {a.partner}: {a.attachment_style} ({a.confidence:.0%})")

    print("\nTRIANGULATION EVENTS:")
    for t in report.triangulation_events:
        print(f"  {t.speaker} → {t.listener} (about {t.target}): {t.manipulative_score:.0%} manipulative")

    print("\nEMOTIONAL TRAJECTORIES:")
    for et in report.emotional_trajectories:
        print(f"  {et.thread_id}: {et.start_sentiment} → {et.end_sentiment} ({et.trajectory})")

    print("\nRELATIONSHIP GRAPH:")
    for n in report.relationship_graph:
        print(f"  {n.name} ({n.role}): {n.risk_profile} | centrality {(n.centrality_score * 100):.0f}%")

    print("\nNARRATIVE:")
    print(report.overall_narrative)
    print()
    return 0


def test(args: argparse.Namespace) -> int:
    """ELI5: Run the full load calculation on every circuit."""
    print(f"\n🧪 Running SimplePod test suite...\n")
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    if args.cov:
        cmd.extend(["--cov=core", "--cov-report=term-missing"])
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def version(args: argparse.Namespace) -> int:
    """ELI5: Read the nameplate on the panel door."""
    print(f"SimplePod Surgical Strike Swarm v{__version__}")
    print("https://github.com/sevengramdab/simplepod-v2")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="simplepod",
        description="SimplePod Swarm — Distributed Agentic Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  simplepod server --reload           # Dev server with auto-reload
  simplepod orbitscribe --mode llm    # Full LLM analysis
  simplepod test --cov                # Run tests with coverage
  simplepod version                   # Show version
        """,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # server
    srv = subparsers.add_parser("server", help="Start the FastAPI backend")
    srv.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    srv.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    srv.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    srv.set_defaults(func=server)

    # orbitscribe
    orb = subparsers.add_parser("orbitscribe", help="Run OrbitScribe relationship analysis")
    orb.add_argument("--mode", choices=["synthetic", "auto", "llm"], default="synthetic",
                     help="Analysis mode (default: synthetic)")
    orb.set_defaults(func=orbitscribe)

    # test
    tst = subparsers.add_parser("test", help="Run the test suite")
    tst.add_argument("--cov", action="store_true", help="Enable coverage reporting")
    tst.set_defaults(func=test)

    # version (also handled by --version flag)
    ver = subparsers.add_parser("version", help="Show version information")
    ver.set_defaults(func=version)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
