import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://127.0.0.1:8000/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")
            
            # Wait for initial snapshot
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Received initial message type: {data.get('type')}")
            if data.get('type') == 'snapshot':
                print(f"Nodes in snapshot: {len(data.get('nodes', []))}")
                print(f"Alerts in snapshot: {len(data.get('alerts', []))}")
                
            # Send ping
            await websocket.send("ping")
            response = await websocket.recv()
            print(f"Received ping response: {response}")
            
    except Exception as e:
        print(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
