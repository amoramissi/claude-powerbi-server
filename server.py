from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

# --- Claude Client Setup ---
client = anthropic.Anthropic(api_key="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")

def query_power_bi_with_claude(natural_language_query):
    """
    This is where the magic happens.
    For now, we'll just pretend to query Power BI.
    In a real scenario, this function would generate a DAX query,
    run it against Power BI, and return the result.
    """
    print(f"--> Pretending to query Power BI with: '{natural_language_query}'")

    # We'll have Claude generate a mock answer for our simulation
    system_prompt = "You are a Power BI data model. A user has asked a question. Respond with a simple, direct data answer. For example, if asked 'Total sales?', respond '$550,000'."

    message = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=100,
        system=system_prompt,
        messages=[{"role": "user", "content": natural_language_query}]
    )

    mock_data_answer = message.content[0].text
    print(f"<-- Mock Power BI Response: {mock_data_answer}")
    return mock_data_answer

# --- Endpoint 1: Tell Claude what tools exist ---
@app.route("/tools", methods=['GET'])
def get_tools():
    tools = {
        "tools": [
            {
                "name": "ask_powerbi",
                "description": "Get data from the Power BI model. Use it to answer questions",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The user's question in plain English."
                        }
                    },
                    "required": ["question"]
                }
            }
        ]
    }
    return jsonify(tools)

# --- Endpoint 2: Execute a tool when asked ---
@app.route("/execute_tool", methods=['POST'])
def execute_tool():
    data = request.json
    tool_name = data.get('name')
    tool_input = data.get('input')

    if tool_name == "ask_powerbi":
        question = tool_input.get('question')
        result = query_power_bi_with_claude(question)
        return jsonify({"result": result})
    else:
        return jsonify({"error": "Tool not found"}), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)