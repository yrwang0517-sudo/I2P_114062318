import websockets
import asyncio

async def connect_to_server():
    uri = "ws://localhost:8989"  # 替換為伺服器的地址和埠號
    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello Server!")
        response = await websocket.recv()
        print(f"Server response: {response}")

asyncio.run(connect_to_server())