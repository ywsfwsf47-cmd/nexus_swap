from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import random

app = FastAPI()

# 1️⃣ نظام إدارة غرف المزامنة والاتصال لايف عبر الـ WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: str, room_id: str, sender: WebSocket):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                if connection != sender:
                    await connection.send_text(message)

manager = ConnectionManager()

# 2️⃣ توليد رقم الغرفة المؤقت (4 أرقام)
@app.get("/api/generate-room")
async def generate_room():
    room_id = str(random.randint(1000, 9999))
    return {"room_id": room_id}

# 3️⃣ نقطة اتصال الـ WebSocket لنقل البيانات بلمح البصر
@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data, room_id, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)

# 4️⃣ واجهة المستخدم العالمية المدمجة (HTML + CSS + JS مع مترجم لغات العالم)
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkSync - Universal Instant Share</title>
    <script type="text/javascript" src="//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --accent-color: #3b82f6;
            --text-color: #f8fafc;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .header {
            width: 100%;
            max-width: 500px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        /* تصميم مخصص لقائمة لغات العالم */
        #google_translate_element {
            background-color: var(--card-bg);
            padding: 5px;
            border-radius: 8px;
            border: 1px solid var(--accent-color);
        }
        .card {
            background-color: var(--card-bg);
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 450px;
            text-align: center;
        }
        .room-display {
            font-size: 3rem;
            font-weight: bold;
            color: var(--accent-color);
            margin: 20px 0;
            letter-spacing: 5px;
        }
        input, textarea {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border-radius: 8px;
            border: 1px solid #475569;
            background-color: #0f172a;
            color: white;
            box-sizing: border-box;
            font-size: 1rem;
        }
        button.main-btn {
            width: 100%;
            padding: 12px;
            background-color: var(--accent-color);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            font-weight: bold;
            transition: 0.3s;
        }
        button.main-btn:hover { background-color: #2563eb; }
        .box { display: none; }
        .box.active { display: block; }
        /* إخفاء شريط جوجل العلوي المزعج للحفاظ على جمالية الموقع */
        .goog-te-banner-frame.skiptranslate { display: none !important; }
        body { top: 0px !important; }
    </style>
</head>
<body>

    <div class="header">
        <h2>🔗 LinkSync</h2>
        <div id="google_translate_element"></div>
    </div>

    <div class="card">
        <div id="setup-box" class="box active">
            <h3>Share text, links, or code across devices instantly</h3>
            <button class="main-btn" onclick="createRoom()">Create Sync Room</button>
            <p style="margin: 15px 0;">OR</p>
            <input type="number" id="room-input" placeholder="Enter 4-digit Room Code">
            <button class="main-btn" style="background-color: #10b981;" onclick="joinRoom()">Join Room</button>
        </div>

        <div id="sync-box" class="box">
            <h3>Your Sync Room Code</h3>
            <div class="room-display" id="room-number">----</div>
            <textarea id="data-transfer" rows="8" placeholder="Paste your text, links, or code here... Everything syncs to the other device live!" oninput="sendData()"></textarea>
            <p style="font-size: 0.85rem; color: #94a3b8;">🔒 Data auto-destructs instantly when connection closes.</p>
        </div>
    </div>

    <script>
        let ws;
        let currentRoomId;

        // تشغيل أداة الترجمة لجميع اللغات تلقائياً
        function googleTranslateElementInit() {
            new google.translate.TranslateElement({
                pageLanguage: 'en',
                layout: google.translate.TranslateElement.InlineLayout.SIMPLE
            }, 'google_translate_element');
        }

        async function createRoom() {
            let response = await fetch('/api/generate-room');
            let data = await response.json();
            initWebSocket(data.room_id);
        }

        function joinRoom() {
            let roomId = document.getElementById('room-input').value;
            if(roomId.length === 4) {
                initWebSocket(roomId);
            } else {
                alert('Please enter a valid 4-digit code');
            }
        }

        function initWebSocket(roomId) {
            currentRoomId = roomId;
            let protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            ws = new WebSocket(`${protocol}${window.location.host}/ws/${roomId}`);

            ws.onopen = () => {
                document.getElementById('setup-box').classList.remove('active');
                document.getElementById('sync-box').classList.add('active');
                document.getElementById('room-number').innerText = roomId;
            };

            ws.onmessage = (event) => {
                document.getElementById('data-transfer').value = event.data;
            };
        }

        function sendData() {
            let text = document.getElementById('data-transfer').value;
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(text);
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTMLResponse(content=HTML_CONTENT, status_code=200)
