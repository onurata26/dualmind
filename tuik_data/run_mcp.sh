#!/bin/bash
# Script to run the custom stdio Model Context Protocol (MCP) server
# This script can be added to your MCP client configuration (e.g. Claude Desktop, Cursor, Gemini-MCP)

python3 "$(dirname "$0")/mcp_server.py"
