# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from flask import Flask, request, jsonify, render_template_string
from google.adk.agents import Agent
from dotenv import load_dotenv

# Import the refactored tool and the enhanced prompt for BigQuery
import tools
import prompt

# Load environment variables from the .env file
load_dotenv()

# --- Agent Definition ---

# The name of the model to be used by the root agent.
# This should be a powerful model capable of reasoning and function calling.
ROOT_AGENT_MODEL = os.environ.get("ROOT_AGENT_MODEL", "gemini-2.5-flash")

# This is the main agent for interacting with the BigQuery database.
# Its instruction is the comprehensive prompt we've built, which contains all the
# database context and reasoning logic. The agent's tool is the SQL query executor.
root_agent = Agent(
    name="bigquery_agent",
    model=ROOT_AGENT_MODEL,
    description="An agent that understands questions about a BigQuery database, generates SQL, executes it, and provides answers.", # Updated description
    instruction=prompt.BIGQUERY_PROMPT,
    tools=[
        tools.query_bigquery,
    ],
)

# --- Web Server Definition ---
# Create a Flask web server object that Gunicorn will use.
app = Flask(__name__)

# This is the HTML for the chat UI.
# It is now a part of the Python file for single-file deployment.
CHAT_UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dixie Agent</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex items-center justify-center min-h-screen">
    <div class="w-full max-w-2xl bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 m-4">
        <h1 class="text-2xl font-bold text-center mb-6">Dixie Agent</h1>
        
        <!-- Chat History -->
        <div id="chat-history" class="h-96 overflow-y-auto mb-4 p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-700">
            <div class="flex items-start mb-4">
                <div class="bg-blue-500 text-white rounded-xl p-3 shadow-md">
                    Hello! I am Dixie, an AI recruiting assistant. How can I help you find talent today?
                </div>
            </div>
        </div>

        <!-- Input Form -->
        <div class="flex items-center space-x-2">
            <input type="text" id="user-input" placeholder="Type your message..." class="flex-grow p-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-900">
            <button id="send-button" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-3 px-6 rounded-lg transition duration-200 ease-in-out">
                Send
            </button>
        </div>
        
    </div>

    <script>
        const chatHistory = document.getElementById('chat-history');
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');
        
        // This is a more robust way to handle a root URL
        const backendUrl = window.location.origin;

        // Function to create a message bubble
        function addMessage(text, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `flex mb-4 ${isUser ? 'justify-end' : 'justify-start'}`;
            
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = `max-w-md p-3 rounded-xl shadow-md ${isUser ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-600 text-gray-900 dark:text-white'}`;
            bubbleDiv.textContent = text;
            
            messageDiv.appendChild(bubbleDiv);
            chatHistory.appendChild(messageDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll to the bottom
        }

        async function sendMessage() {
            const query = userInput.value.trim();
            if (!query) return;

            addMessage(query, true); // Add user's message to chat
            userInput.value = ''; // Clear input field

            // Show a loading indicator
            addMessage("Thinking...", false);
            const thinkingMessage = chatHistory.lastChild.querySelector('div');
            
            try {
                const apiPath = '/agent';

                const response = await fetch(backendUrl + apiPath, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ query: query })
                });

                const data = await response.json();

                // Remove loading indicator and display actual response
                chatHistory.removeChild(chatHistory.lastChild);
                if (response.ok) {
                    addMessage(data.response, false);
                } else {
                    addMessage(`Error: ${data.error}`, false);
                }

            } catch (error) {
                chatHistory.removeChild(chatHistory.lastChild);
                addMessage(`An error occurred: ${error.message}`, false);
            }
        }

        sendButton.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

# Route to serve the HTML page for the UI
@app.route("/", methods=["GET"])
def serve_ui():
    """Serves the main chat UI for the web application."""
    return render_template_string(CHAT_UI_HTML)

# Route for the agent's API endpoint
@app.route("/agent", methods=["POST"])
def agent_handler():
    """Handles POST requests to the agent endpoint."""
    try:
        data = request.json
        user_query = data.get('query')

        if not user_query:
            return jsonify({"error": "Missing 'query' field in request"}), 400

        # Pass the query to the root agent and get a response.
        response_data = root_agent.generate_response(user_query)
        response_text = response_data.text

        return jsonify({"response": response_text, "status": "ok"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
