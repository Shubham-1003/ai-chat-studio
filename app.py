```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Chat Studio</title>
    <style>
        /* Global Styles */
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f6;
            margin: 0;
            padding: 0;
            max-width: 52rem;
            margin: 0 auto;
        }
        header {
            visibility: hidden;
        }
        .sidebar {
            background-color: #202123;
            color: white;
            padding: 1rem;
            height: 100vh;
            position: fixed;
            left: 0;
            top: 0;
            width: 250px;
        }
        .main-content {
            margin-left: 250px;
            padding: 1rem;
        }
        .chat-input-area {
            position: fixed;
            bottom: 0;
            left: 250px;
            right: 0;
            padding: 0.8rem 1rem;
            background-color: white;
            z-index: 999;
            border-top: 1px solid #e5e5e5;
            max-width: calc(52rem - 250px);
        }
        .file-dropzone {
            border: 2px dashed #ddd;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            text-align: center;
            background-color: #f9f9f9;
            cursor: pointer;
        }
        .file-badge {
            display: inline-flex;
            align-items: center;
            background-color: #f0f0f0;
            padding: 5px 10px;
            border-radius: 15px;
            margin-right: 8px;
            margin-bottom: 8px;
            font-size: 0.8rem;
        }
        .file-badge .remove-btn {
            margin-left: 5px;
            cursor: pointer;
            color: #888;
        }
        .file-badge .remove-btn:hover {
            color: #ff4d4f;
        }
        .upload-icon {
            background-color: #f0f0f0;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            cursor: pointer;
            border: none;
        }
        .upload-icon:hover {
            background-color: #e6e6e6;
        }
        .chat-input-container {
            display: flex;
            align-items: flex-end;
        }
        .chat-input-box {
            flex-grow: 1;
            margin-right: 8px;
        }
        .chat-message {
            background-color: #f7f7f8;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .chat-message.user {
            background-color: #ececf1;
            align-self: flex-end;
        }
        .chat-message.bot {
            background-color: #f7f7f8;
            align-self: flex-start;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <h1>✨ AI Chat Studio</h1>
        <button onclick="newChat()">➕ New Chat</button>
        <hr>
        <h3>🤖 Model Selection</h3>
        <select id="modelSelector">
            <option value="Model1">Model 1</option>
            <option value="Model2">Model 2</option>
        </select>
        <p id="modelCapabilities">Capabilities: Capability1, Capability2</p>
        <hr>
        <h3>Chat Context Files</h3>
        <div id="uploadedFiles"></div>
        <button onclick="clearAllFiles()">Clear All Context Files</button>
    </div>
    <div class="main-content" id="chatArea">
        <div style="height: 80px;"></div>
        <div id="chatMessages"></div>
    </div>
    <div class="chat-input-area">
        <div class="file-dropzone" id="fileDropzone" style="display:none;">
            <input type="file" id="fileUploader" multiple style="display:none;" onchange="handleFileUpload()">
            <label for="fileUploader">Drag and drop files here</label>
        </div>
        <div id="stagedFiles"></div>
        <div class="chat-input-container">
            <button class="upload-icon" onclick="toggleDropzone()">📎</button>
            <input type="text" id="chatInput" placeholder="Ask Model anything..." onkeypress="handleKeyPress(event)">
        </div>
    </div>

    <script>
        let messages = [];
        const chatMessages = document.getElementById('chatMessages');
        const chatInput = document.getElementById('chatInput');
        const fileDropzone = document.getElementById('fileDropzone');
        const stagedFilesDiv = document.getElementById('stagedFiles');
        let stagedFiles = [];

        function newChat() {
            messages = [];
            chatMessages.innerHTML = '';
        }

        function toggleDropzone() {
            fileDropzone.style.display = fileDropzone.style.display === 'none' ? 'block' : 'none';
        }

        function handleFileUpload() {
            const files = document.getElementById('fileUploader').files;
            for (let i = 0; i < files.length; i++) {
                if (!stagedFiles.some(file => file.name === files[i].name)) {
                    stagedFiles.push(files[i]);
                }
            }
            updateStagedFiles();
        }

        function updateStagedFiles() {
            stagedFilesDiv.innerHTML = '';
            stagedFiles.forEach((file, index) => {
                const fileBadge = document.createElement('span');
                fileBadge.className = 'file-badge';
                fileBadge.textContent = file.name;
                const removeBtn = document.createElement('span');
                removeBtn.className = 'remove-btn';
                removeBtn.textContent = '×';
                removeBtn.onclick = () => removeStagedFile(index);
                fileBadge.appendChild(removeBtn);
                stagedFilesDiv.appendChild(fileBadge);
            });
        }

        function removeStagedFile(index) {
            stagedFiles.splice(index, 1);
            updateStagedFiles();
        }

        function sendMessage() {
            const messageText = chatInput.value.trim();
            if (messageText === '') return;

            addMessageToUI('user', messageText);

            setTimeout(() => simulateBotResponse(messageText), 500);

            chatInput.value = '';
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        function addMessageToUI(role, content) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `chat-message ${role}`;
            messageDiv.textContent = content;
            chatMessages.appendChild(messageDiv);
            scrollToBottom();
        }

        function simulateBotResponse(userMessage) {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'chat-message bot';
            typingDiv.textContent = '🧠 Thinking...';
            chatMessages.appendChild(typingDiv);
            scrollToBottom();

            setTimeout(() => {
                chatMessages.removeChild(typingDiv);
                const botResponse = getBotResponse(userMessage);
                addMessageToUI('bot', botResponse);
            }, 1500);
        }

        function getBotResponse(userMessage) {
            const responses = [
                "That's an interesting point!",
                "I see what you mean.",
                "Could you clarify that?",
                "Let me think about that...",
                "Here's some information on that topic."
            ];
            return responses[Math.floor(Math.random() * responses.length)];
        }

        function clearAllFiles() {
            stagedFiles = [];
            updateStagedFiles();
        }

        function scrollToBottom() {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    </script>
</body>
</html>
```
