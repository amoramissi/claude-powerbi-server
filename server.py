from flask import Flask, request, jsonify
import msal
import requests

# --- Your Credentials from Task 1 ---
CLIENT_ID = "2236da00-601f-47f6-8798-46193e15e8b6"
CLIENT_SECRET = "2698Q~DStlV4AezuYUqLxgQjruJeR~5NnoMcvasZ"
TENANT_ID = "894178aa-91e4-4154-a111-7ef891564a3d"

app = Flask(__name__)

def get_powerbi_token():
    """Gets an access token from Azure AD."""
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    scope = ["https://analysis.windows.net/powerbi/api/.default"]

    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=authority,
        client_credential=CLIENT_SECRET,
    )

    result = app.acquire_token_for_client(scopes=scope)

    if "access_token" not in result:
        print("Failed to get token:", result.get("error_description"))
        return None

    return result['access_token']


def list_powerbi_datasets(token):
    """Uses a token to get a list of datasets from Power BI."""
    datasets_url = "https://api.powerbi.com/v1.0/myorg/datasets"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(datasets_url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching datasets: {response.status_code}")
        print(response.text)
        return None

# --- Main function that our server will now use ---
def query_power_bi(natural_language_query):
    """
    Takes a dataset name as a query, finds it, and returns its details.
    """
    print("--> Getting Power BI access token...")
    token = get_powerbi_token()
    
    if not token:
        return "Error: Could not authenticate with Power BI."
    
    print(f"--> Authenticated. Searching for dataset named: '{natural_language_query}'...")
    datasets = list_powerbi_datasets(token)
    
    if not datasets:
        return "Could not retrieve datasets from Power BI."

    # Loop through all datasets to find a match
    for dataset in datasets['value']:
        if dataset['name'].lower() == natural_language_query.lower():
            # Found it! Return some useful info.
            found_dataset_info = f"Success! Found dataset '{dataset['name']}' with ID: {dataset['id']}"
            print(f"<-- {found_dataset_info}")
            return found_dataset_info
    
    # If the loop finishes without finding a match
    not_found_message = f"Dataset '{natural_language_query}' not found."
    print(f"<-- {not_found_message}")
    return not_found_message

# --- Endpoints for Claude to use (No changes here) ---
@app.route("/tools", methods=['GET'])
def get_tools():
    tools = {
        "tools": [
            {
                "name": "ask_powerbi",
                "description": "Get data from the Power BI model. Use it to answer questions.",
                "input_schema": {
                    "type": "object",
                    "properties": { "question": { "type": "string", "description": "The user's question in plain English."}},
                    "required": ["question"]
                }
            }
        ]
    }
    return jsonify(tools)

@app.route("/execute_tool", methods=['POST'])
def execute_tool():
    data = request.json
    tool_name = data.get('name')
    tool_input = data.get('input')

    if tool_name == "ask_powerbi":
        question = tool_input.get('question')
        # --- IMPORTANT: We now call our REAL function ---
        result = query_power_bi(question) 
        return jsonify({"result": result})
    else:
        return jsonify({"error": "Tool not found"}), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)