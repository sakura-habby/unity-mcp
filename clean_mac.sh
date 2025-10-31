#!/bin/sh
# Close all Unity Editor instances
rm -fr MCPForUnity/UnityMcpServer\~/src
cp -R Server MCPForUnity/UnityMcpServer\~/src
rm -f MCPForUnity/UnityMcpServer\~/src/README.md
rm -fr ~/Library/Application\ Support/UnityMCP/UnityMcpServer
rm ~/.unity-mcp/*.json
# Re-open Unity Editor instances
# Run `npx @modelcontextprotocol/inspector` to test
# Quit claude code and run `claude --resume`
# Quit codex and run `codex resume`
# In Cursor, disable and enable UnityMCP
