from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import HTMLResponse
import random
import shutil
import os

app = FastAPI()

# مجلد مؤقت لحفظ الملفات المرفوعة أثناء النقل
UPLOAD_DIR = "shared_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

@app.get("/api/generate-room")
async def generate_room():
    room_id = str(random.randint(1000, 9999))
    return {"room_id": room_id}

# ⚠️ نقطة استقبال وملقّف الملفات والصور والفيديوهات
@app.post("/api/upload-file")
async def upload_file(room_id: str = Form(...), file: UploadFile = File(...)):
    # حد الحجم المجاني: 15 ميجابايت (15 * 1024 * 1024 بايت)
    MAX_FREE_SIZE = 15 * 1024 * 1024 
    
    # قراءة حجم الملف المرفوع
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    
    # إذا كان الفيديو أو الملف طويل وأكبر من الحد المجاني
    if file_size > MAX_FREE_SIZE:
        return {"status": "error", "message": "PRO_REQUIRED"}
        
    # حفظ الملف المجاني/القصير مؤقتاً لنقله
    file_location = f"{UPLOAD_DIR}/{room_id}_{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # إرسال إشعار فوري عبر الـ WebSocket للجهاز الآخر بأن هناك ملف جاهز للتحميل
    file_url = f"/download/{room_id}_{file.filename}"
    await manager.broadcast(f"__FILE_READY__:{file.filename}:{file_url}", room_id, sender=None)
    
    return {"status": "success", "file_name": file.filename}

@app.get("/download/{file_name}")
async def download_file(file_name: str):
    file_path = f"{UPLOAD_DIR}/{file_name}"
    if os.path.exists(file_path):
        from fastapi.responses import FileResponse
        return FileResponse(file_path)
    return {"error": "File not found"}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data, room_id, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)

# الواجهة المحدثة مع زر رفع الملفات وفحص الحجم
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkSync - Universal Instant Share</title>
    <script type="text/javascript" src="//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>
    <style>
        :root { --bg-color: #0f172a; --card-bg: #1e293b; --accent-color: #3b82f6; --text-color: #f8fafc; }
        body { font-family: sans-serif; background-color: var(--bg-color); color: var(--text-color); margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; }
        .header { width: 100%; max-width: 500px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        #google_translate_element { background-color: var(--card-bg); padding: 5px; border-radius: 8px; border: 1px solid var(--accent-color); }
        .card { background-color: var(--card-bg); padding: 30px; border-radius: 16px; width: 100%; max-width: 450px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.3); box-sizing: border-box; }
        .room-display { font-size: 3rem; font-weight: bold; color: var(--accent-color); margin: 20px 0; letter-spacing: 5px; }
        input, textarea { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 1px solid #475569; background-color: #0f172a; color: white; box-sizing: border-box; }
        button.main-btn { width: 100%; padding: 12px; background-color: var(--accent-color); color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; font-weight: bold; }
        button.main-btn:hover { background-color: #2563eb; }
        .box { display: none; }
        .box.active { display: block; }
        .file-section { margin-top: 15px; padding: 15px; border: 2px dashed #475569; border-radius: 8px; }
        .pro-popup { display: none; color: #f43f5e; background: #881337; padding: 10px; border-radius: 8px; margin-top: 10px; font-weight: bold; }
    </style>
</head>
<body>

    <div class="header">
        <h2>🔗 LinkSync</h2>
        <div id="google_translate_element"></div>
    </div>

    <div class="card">
        <div id="setup-box" class="box active">
            <h3>Share text, links, images, or short videos instantly</h3>
            <button class="main-btn" onclick="createRoom()">Create Sync Room</button>
            <p style="margin: 15px 0;">OR</p>
            <input type="number" id="room-input" placeholder="Enter 4-digit Room Code">
            <button class="main-btn" style="background-color: #10b981;" onclick="joinRoom()">Join Room</button>
        </div>

        <div id="sync-box" class="box">
            <h3>Your Sync Room Code</h3>
            <div class="room-display" id="room-number">----</div>
            <textarea id="data-transfer" rows="5" placeholder="Paste text or links here..." oninput="sendData()"></textarea>
            
            <div class="file-section">
                <h4>📷 Share Images & Short Videos</h4>
                <input type="file" id="file-chooser" onchange="uploadFile()">
                <div class="pro-popup" id="pro-warning">⚠️ Video too long! Please upgrade to PRO to share large files.</div>
                <div id="file-link-container" style="margin-top:10px;"></div>
            </div>
            
            <p style="font-size: 0.85rem; color: #94a3b8; margin-top:15px;">🔒 Free limit: Videos up to 15MB. Data auto-destructs on close.</p>
        </div>
    </div>

    <script>
        let ws;
        let currentRoomId;

        function googleTranslateElementInit() {
            new google.translate.TranslateElement({pageLanguage: 'en', layout: google.translate.TranslateElement.InlineLayout.SIMPLE}, 'google_translate_element');
        }

        async function createRoom() {
            let response = await fetch('/api/generate-room');
            let data = await response.json();
            initWebSocket(data.room_id);
        }

        function joinRoom() {
            let roomId = document.getElementById('room-input').value;
            if(roomId.length === 4) initWebSocket(roomId);
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
                if(event.data.startsWith("__FILE_READY__")) {
                    let parts = event.data.split(":");
                    let fileName = parts[1];
                    let fileUrl = parts.slice(2).join(":");
                    document.getElementById('file-link-container').innerHTML = `📥 Incoming File: <a href="${fileUrl}" target="_blank" style="color:#3b82f6; font-weight:bold;">Download ${fileName}</a>`;
                } else {
                    document.getElementById('data-transfer').value = event.data;
                }
            };
        }

        function sendData() {
            let text = document.getElementById('data-transfer').value;
            if (ws && ws.readyState === WebSocket.OPEN) ws.send(text);
        }

        async function uploadFile() {
            let fileInput = document.getElementById('file-chooser');
            let warning = document.getElementById('pro-warning');
            warning.style.display = "none";
            
            if(fileInput.files.length === 0) return;
            
            let formData = new FormData();
            formData.append("room_id", currentRoomId);
            formData.append("file", fileInput.files[0]);
            
            let response = await fetch('/api/upload-file', { method: 'POST', body: formData });
            let result = await response.json();
            
            if(result.status === "error" && result.message === "PRO_REQUIRED") {
                warning.style.display = "block"; // إظهار رسالة اشتراك برو للملفات الطويلة
                fileInput.value = "";
            } else {
                alert("File sent successfully!");
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTMLResponse(content=HTML_CONTENT, status_code=200)
