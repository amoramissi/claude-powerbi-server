# Import Flask and also the 'request' object to handle incoming data
from flask import Flask, request
import anthropic

# --- From main.py: Create our Claude client ---
client = anthropic.Anthropic(
    api_key="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", # Make sure your key is still here
)

# --- Create our Flask app ---
app = Flask(__name__)

# --- From main.py: Our reusable function ---
def ask_claude(prompt):
    """Takes a prompt string and returns Claude's response string."""
    print(f"--> Received prompt: {prompt}")
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return message.content[0].text

# --- This is our new API endpoint ---
@app.route("/ask", methods=['POST'])
def handle_ask():
    """Receives a question and returns Claude's answer."""
    data = request.json
    question = data.get('question')

    if not question:
        return {"error": "No question provided"}, 400

    # Use our function to get the answer
    answer = ask_claude(question)

    # Return the answer in a JSON format
    return {"answer": answer}

# --- Start the server ---
if __name__ == "__main__":
    app.run(port=5000, debug=True)