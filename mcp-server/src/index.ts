#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const RUSTCHAIN_API = "https://api.rustchain.io/v1";

interface RustChainConfig {
  apiUrl: string;
  apiKey?: string;
}

const config: RustChainConfig = {
  apiUrl: process.env.RUSTCHAIN_API_URL || RUSTCHAIN_API,
  apiKey: process.env.RUSTCHAIN_API_KEY,
};

async function rustchainRequest(endpoint: string): Promise<any> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (config.apiKey) headers["Authorization"] = `Bearer ${config.apiKey}`;
  const res = await fetch(`${config.apiUrl}${endpoint}`, { headers });
  if (!res.ok) throw new Error(`RustChain API error: ${res.status}`);
  return res.json();
}

const server = new Server(
  { name: "rustchain-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "rustchain_health",
      description: "Check RustChain node health status",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "rustchain_balance",
      description: "Get wallet balance for an address",
      inputSchema: {
        type: "object",
        properties: { address: { type: "string", description: "Wallet address" } },
        required: ["address"],
      },
    },
    {
      name: "rustchain_bounties",
      description: "List open RustChain bounties",
      inputSchema: {
        type: "object",
        properties: { limit: { type: "number", description: "Max results (default 10)" } },
      },
    },
    {
      name: "rustchain_miner_status",
      description: "Check miner attestation status",
      inputSchema: {
        type: "object",
        properties: { address: { type: "string", description: "Miner address" } },
        required: ["address"],
      },
    },
    {
      name: "rustchain_transactions",
      description: "Get recent transactions for an address",
      inputSchema: {
        type: "object",
        properties: {
          address: { type: "string", description: "Wallet address" },
          limit: { type: "number", description: "Max results (default 10)" },
        },
        required: ["address"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  try {
    switch (name) {
      case "rustchain_health": {
        const data = await rustchainRequest("/health");
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }
      case "rustchain_balance": {
        const data = await rustchainRequest(`/balance/${args!.address}`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }
      case "rustchain_bounties": {
        const limit = (args?.limit as number) || 10;
        const data = await rustchainRequest(`/bounties?limit=${limit}`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }
      case "rustchain_miner_status": {
        const data = await rustchainRequest(`/miner/${args!.address}/status`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }
      case "rustchain_transactions": {
        const limit = (args?.limit as number) || 10;
        const data = await rustchainRequest(`/transactions/${args!.address}?limit=${limit}`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }
      default:
        return { content: [{ type: "text", text: `Unknown tool: ${name}` }], isError: true };
    }
  } catch (error: any) {
    return { content: [{ type: "text", text: `Error: ${error.message}` }], isError: true };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("RustChain MCP Server running on stdio");
}

main().catch(console.error);
