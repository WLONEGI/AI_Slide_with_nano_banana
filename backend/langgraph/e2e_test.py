import asyncio
import json
import os
import aiohttp
import sys
import subprocess
import uuid

# default remote
DEFAULT_REMOTE_URL = "https://ai-slide-backend-1021289594562.asia-northeast1.run.app"
SERVICE_URL = os.getenv("SERVICE_URL", DEFAULT_REMOTE_URL)
CHAT_ENDPOINT = f"{SERVICE_URL}/api/chat/stream"

# auth flag (default to True unless explicitly False)
USE_AUTH = os.getenv("USE_AUTH", "true").lower() == "true"

# Test Scenarios
INITIAL_PROMPT = "SIerの歴史の変遷について、IT業界の初心者に向けた5枚のスライドを作成してください。各スライドには画像を含めてください。"
DEEP_EDIT_PROMPT = "現在の市場シェア上位の企業について追加して"

async def get_identity_token():
    """gcloudコマンドでIDトークンを取得"""
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-identity-token"], text=True
        ).strip()
        return token
    except subprocess.CalledProcessError as e:
        print(f"Error getting identity token: {e}")
        # Local development typically doesn't need this if auth is disabled
        return None

async def stream_chat(session, messages, thread_id=None, step_name="Initial Generation"):
    """チャットAPIにリクエストを送り、ストリーミングレスポンスを表示"""
    headers = {
        "Content-Type": "application/json"
    }
    
    if USE_AUTH:
        print("Getting identity token for auth...")
        token = await get_identity_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
             print("Warning: Failed to get identity token, proceeding without it.")

    payload = {
        "messages": messages,
        "debug": True,
        "deep_thinking_mode": True,
        "search_before_planning": True,
        "thread_id": thread_id
    }
    
    print(f"\n{'='*20} {step_name} {'='*20}")
    print(f"Target URL: {CHAT_ENDPOINT}")
    print(f"Thread ID: {thread_id}")
    print(f"Messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")

    try:
        async with session.post(CHAT_ENDPOINT, json=payload, headers=headers) as response:
            if response.status != 200:
                text = await response.text()
                print(f"Error: {response.status} - {text}")
                return None

            print(f"\n--- Streaming Response for {step_name} ---")
            
            # SSE stream processing
            current_event_type = None
            
            async for line_bytes in response.content:
                line = line_bytes.decode('utf-8').strip()
                if not line:
                    continue
                
                if line.startswith("event: "):
                    current_event_type = line[7:].strip()
                elif line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        # Parse the data payload
                        data = json.loads(data_str)
                        
                        # Handle double encoding if present
                        if isinstance(data, str):
                            try:
                                actual_data = json.loads(data)
                            except:
                                actual_data = data
                        else:
                            actual_data = data
                            
                        # Now we have the event type (from previous line) and data (from this line)
                        if current_event_type:
                            event_type = current_event_type
                            event_data = actual_data
                            
                            if event_type == "message":
                                delta = event_data.get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    print(content, end="", flush=True)
                            elif event_type == "tool_call_result":
                                tool_name = event_data.get("tool_name")
                                result = str(event_data.get("tool_result", ""))
                                print(f"\n[Tool Result: {tool_name}] {result[:500]}...")
                                if "http" in result and ("storage.googleapis.com" in result or ".png" in result):
                                    print(f"\n!!! FOUND IMAGE URL: {result} !!!\n")
                            elif event_type == "start_of_agent":
                                agent_name = event_data.get("agent_name")
                                print(f"\n[Agent Start] {agent_name}")
                            elif event_type == "end_of_workflow":
                                print(f"\n[End of Workflow]")
                            elif event_type == "error":
                                print(f"\n[Error] {event_data}")
                            else:
                                # Log other interesting events
                                pass
                        else:
                            # Fallback if no event line preceded (should not happen with regular SSE)
                            print(f"\n[Raw Data No Event] {str(actual_data)[:100]}...")
                            pass

                        # Reset event type for next message
                        current_event_type = None

                    except json.JSONDecodeError:
                        print(f"[Raw] {content_str[:100]}...")
            
    except aiohttp.ClientConnectorError as e:
        print(f"Connection Error: {e}")
        print(f"Ensure the server is running at {SERVICE_URL}")
        return None

    print(f"\n{step_name} Completed.")
    return thread_id

async def run_e2e_test():
    # Random Thread ID
    thread_id = str(uuid.uuid4())
    print(f"Generated Thread ID: {thread_id}")
    print(f"Connect to: {SERVICE_URL}")

    connector = aiohttp.TCPConnector(ssl=False)
    # Increase timeout for long-running image generation (Gemini 3.0 batch)
    timeout = aiohttp.ClientTimeout(total=1200) 
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:

        # Step 1: Initial Request    
        messages = [{"role": "user", "content": INITIAL_PROMPT}]
        await stream_chat(session, messages, thread_id=thread_id, step_name="Step 1: Initial Generation")

        # Wait a bit
        print("\nWaiting 5 seconds before next step...")
        await asyncio.sleep(5)

        # Step 2: Deep Edit Request
        deep_edit_messages = [{"role": "user", "content": DEEP_EDIT_PROMPT}]
        await stream_chat(session, deep_edit_messages, thread_id=thread_id, step_name="Step 2: Deep Edit")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())

