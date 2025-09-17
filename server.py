from flask import Flask, request, jsonify
import msal
import requests

# --- Your Credentials ---
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

# --- NEW Admin Function to Get Workspaces ---
def get_admin_workspaces(token):
    """Uses an admin token to get a list of all workspaces in the tenant."""
    # Note the new ADMIN URL
    workspaces_url = "https://api.powerbi.com/v1.0/myorg/admin/groups?$top=100"
    headers = { "Authorization": f"Bearer {token}" }
    response = requests.get(workspaces_url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching workspaces: {response.status_code}")
        print(response.text)
        return None

# --- NEW Admin Function to Get Datasets from a Workspace ---
def get_admin_datasets(token, workspace_id):
    """Gets a list of datasets from a specific workspace."""
    # Note the new ADMIN URL
    datasets_url = f"https://api.powerbi.com/v1.0/myorg/admin/groups/{workspace_id}/datasets"
    headers = { "Authorization": f"Bearer {token}" }
    response = requests.get(datasets_url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching datasets: {response.status_code}")
        print(response.text)
        return None

# --- Main function updated to use the new admin functions ---
def query_power_bi(natural_language_query):
    print("--> Getting Power BI access token...")
    token = get_powerbi_token()
    
    if not token:
        return "Error: Could not authenticate with Power BI."
    
    print("--> Authenticated. Now listing all workspaces...")
    workspaces = get_admin_workspaces(token)
    
    if not workspaces or not workspaces.get('value'):
        return "Could not retrieve any workspaces from Power BI."

    # For this example, let's just inspect the first workspace found
    first_workspace = workspaces['value'][0]
    workspace_name = first_workspace['name']
    workspace_id = first_workspace['id']
    
    print(f"--> Found workspace '{workspace_name}'. Now getting its datasets...")
    datasets = get_admin_datasets(token, workspace_id)

    if datasets and datasets.get('value'):
        dataset_names = [ds['name'] for ds in datasets['value']]
        return f"Success! In workspace '{workspace_name}', found datasets: {', '.join(dataset_names)}"
    else:
        return f"Successfully connected to workspace '{workspace_name}', but it contains no datasets."

# --- Endpoints for Claude to use (No changes) ---
@app.route("/")
def status_check():
    return "MCP Server is running and ready."

@app.route("/tools", methods=['GET'])
def get_tools():
    tools = {
        "tools": [
            {
                "name": "ask_powerbi",
                "description": "Get data from the Power BI model. Use it to answer questions about sales, revenue, products, and customers.",
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
        result = query_power_bi(question) 
        return jsonify({"result": result})
    else:
        return jsonify({"error": "Tool not found"}), 404
        
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
