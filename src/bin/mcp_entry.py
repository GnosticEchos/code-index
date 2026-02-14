#!/usr/bin/env python3
"""Entry point for MCP server binary."""

import argparse

from code_index.mcp_server.server import sync_main


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Code Index MCP server")
    parser.add_argument(
        "--config",
        default="code_index.json",
        help="Path to configuration file (defaults to code_index.json in working directory)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sync_main(config_path=args.config)
