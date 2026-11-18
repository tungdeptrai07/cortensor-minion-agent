"""
Local OpenAI-Compatible Inference Endpoint simulating a Cortensor Portal Node.
Allows OpenMinion 0.1.x `Agent` & `APIRuntime` to execute genuine HTTP model turns
with native OpenAI tool_calls and structured JSON output without requiring paid API keys.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class CortensorLocalInferenceHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return  # Keep terminal output focused on OpenMinion SDK logs

    def do_POST(self) -> None:
        if not self.path.endswith("/chat/completions"):
            self.send_response(404)
            self.end_headers()
            return

        content_len = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_len).decode("utf-8")
        req = json.loads(raw_body)

        messages = req.get("messages", [])
        tools = req.get("tools", [])

        # Find messages belonging to the CURRENT turn (after the most recent user message)
        last_user_idx = -1
        for i, m in enumerate(messages):
            if m.get("role") == "user":
                last_user_idx = i
        current_turn_msgs = messages[last_user_idx + 1 :] if last_user_idx >= 0 else messages
        has_tool_result_this_turn = any(m.get("role") == "tool" for m in current_turn_msgs)

        last_user = ""
        if last_user_idx >= 0:
            raw_u = messages[last_user_idx].get("content", "")
            last_user = (
                " ".join(str(p.get("text", "")) for p in raw_u if isinstance(p, dict))
                if isinstance(raw_u, list)
                else str(raw_u)
            )

        if not has_tool_result_this_turn and tools:
            tool_names = [t["function"]["name"] for t in tools if "function" in t]
            if "archive_audit_receipt" in tool_names and "archive" in last_user.lower():
                chosen_tool = "archive_audit_receipt"
                args = {"node_id": "miner-sol-gpu-042", "verdict": "HEALTHY"}
            elif "verify_poi_receipt" in tool_names and "poi" in last_user.lower() and "inspect" not in last_user.lower():
                chosen_tool = "verify_poi_receipt"
                args = {"session_id": 1}
            elif "inspect_cortensor_node" in tool_names:
                chosen_tool = "inspect_cortensor_node"
                args = {"node_id": "miner-sol-gpu-042"}
            else:
                chosen_tool = tool_names[0]
                args = {}

            resp_payload = {
                "id": f"chatcmpl-cortensor-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.get("model", "cortensor-oss-20b-local"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": f"call_cortensor_{int(time.time() * 1000) % 100000}",
                            "type": "function",
                            "function": {
                                "name": chosen_tool,
                                "arguments": json.dumps(args)
                            }
                        }]
                    },
                    "finish_reason": "tool_calls"
                }],
                "usage": {"prompt_tokens": 112, "completion_tokens": 24, "total_tokens": 136}
            }
        else:
            tool_msgs = [m.get("content", "") for m in current_turn_msgs if m.get("role") == "tool"]
            tool_summary = tool_msgs[-1] if tool_msgs else "Telemetry verified."

            all_text = " ".join(str(m.get("content", "")) for m in messages)
            if "archive" in last_user.lower():
                final_content = f"Audit receipt archived on disk for miner-sol-gpu-042. ({tool_summary[:180]})"
            elif (
                "health_status" in all_text
                or "NodeAuditSummary" in all_text
                or "audit cortensor node" in last_user.lower()
                or req.get("response_format")
            ):
                final_content = json.dumps({
                    "node_id": "miner-sol-gpu-042",
                    "health_status": "HEALTHY",
                    "poi_verified": True,
                    "vram_utilization_pct": 68.4,
                    "summary": f"Node miner-sol-gpu-042 passed Cortensor PoI & latency audit. Tool output: {tool_summary[:140]}"
                })
            else:
                final_content = f"Audit completed via CortensorOps OpenMinion runtime. Result: {tool_summary[:220]}"

            resp_payload = {
                "id": f"chatcmpl-cortensor-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.get("model", "cortensor-oss-20b-local"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": final_content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 184, "completion_tokens": 58, "total_tokens": 242}
            }

        encoded = json.dumps(resp_payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def start_background_server(host: str = "127.0.0.1", port: int = 11435) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), CortensorLocalInferenceHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
