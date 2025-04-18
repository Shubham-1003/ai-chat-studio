```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChatGPT/Claude Replica</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f6;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            max-width: 720px;
            margin: 0 auto;
            background-color: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        .chat-header {
            background-color: #0073b1;
            color: white;
            padding: 15px;
            text-align: center;
            font-size: 1.2em;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }
        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px 15px;
            border-radius: 8px;
            max-width: 80%;
            line-height: 1.4;
        }
        .message.user {
            background-color: #e1f1ff;
            align-self: flex-end;
        }
        .message.bot {
            background-color: #f1f1f1;
            align-self: flex-start;
        }
        .message.typing {
            background-color: #f1f1f1;
            align-self: flex-start;
            display: flex;
            align-items: center;
        }
        .typing-indicator {
            display: flex;
        }
        .dot {
            width: 8px;
            height: 8px;
            background-color: #555;
            border-radius: 50%;
            margin: 0 2px;
            animation: bounce 1.4s infinite ease-in-out;
        }
        .dot:nth-child(1) { animation-delay: -0.32s; }
        .dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce {
            0%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(-10px); }
        }
        .chat-input-area {
            display: flex;
            border-top: 1px solid #ddd;
            padding: 10px;
            background-color: #fafafa;
        }
        .chat-input-area input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 20px;
            outline: none;
            font-size: 1em;
        }
        .chat-input-area button {
            padding: 10px 20px;
            margin-left: 10px;
            border: none;
            background-color: #0073b1;
            color: white;
            border-radius: 20px;
            cursor: pointer;
            font-size: 1em;
        }
        .chat-input-area button:hover {
            background-color: #005f91;
        }
        .attachment-icon {
            margin-right: 10px;
            cursor: pointer;
            color: #0073b1;
            font-size: 1.2em;
        }
        .attachment-icon:hover {
            color: #005f91;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">AI Chat Interface</div>
        <div class="chat-messages" id="chatMessages">
            <!-- Messages will be dynamically inserted here -->
        </div>
        <div class="chat-input-area">
            <span class="attachment-icon" onclick="toggleFileUpload()">📎</span>
            <input type="text" id="chatInput" placeholder="Type your message here..." onkeypress="handleKeyPress(event)">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        let messages = [];
        const chatMessages = document.getElementById('chatMessages');
        const chatInput = document.getElementById('chatInput');

        function sendMessage() {
            const messageText = chatInput.value.trim();
            if (messageText === '') return;

            // Add user message to the UI
            addMessageToUI('user', messageText);

            // Simulate bot response with typing animation
            setTimeout(() => simulateBotResponse(messageText), 500);

            // Clear input field
            chatInput.value = '';
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        function addMessageToUI(role, content) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            messageDiv.textContent = content;
            chatMessages.appendChild(messageDiv);
            scrollToBottom();
        }

        function simulateBotResponse(userMessage) {
            // Show typing indicator
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot typing';
            const typingIndicator = document.createElement('div');
            typingIndicator.className = 'typing-indicator';
            for (let i = 0; i < 3; i++) {
                const dot = document.createElement('div');
                dot.className = 'dot';
                typingIndicator.appendChild(dot);
            }
            typingDiv.appendChild(typingIndicator);
            chatMessages.appendChild(typingDiv);
            scrollToBottom();

            // Simulate a delay and then show bot's response
            setTimeout(() => {
                chatMessages.removeChild(typingDiv);
                const botResponse = getBotResponse(userMessage);
                addMessageToUI('bot', botResponse);
            }, 1500);
        }

        function getBotResponse(userMessage) {
            // Simple mock response logic
            const responses = [
                "That's an interesting point!",
                "I see what you mean.",
                "Could you clarify that?",
                "Let me think about that...",
                "Here's some information on that topic."
            ];
            return responses[Math.floor(Math.random() * responses.length)];
        }

        function scrollToBottom() {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function toggleFileUpload() {
            alert("File upload functionality is not implemented in this demo.");
        }
    </script>
</body>
</html>
```
