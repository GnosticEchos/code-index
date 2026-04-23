"""
MCP entry point for the code index tool.
"""
import asyncio
import os
import sys

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code_index.mcp_server.server import CodeIndexMCPServer


async def main():
    """Main entry point for MCP server."""
    # Default to current directory if no config specified
    config_path = "code_index.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        
    server = CodeIndexMCPServer(config_path=config_path)
    try:
        await server.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error starting MCP server: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
