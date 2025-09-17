from flask import Flask, request, jsonify
import msal
import requests
import json

# --- Your Credentials ---
CLIENT_ID = "2236da00-601f-47f6-8798-46193e15e8b6"
CLIENT_SECRET = "2698Q~DStlV4AezuYUqLxgQjruJeR~5NnoMcvasZ"
TENANT_ID = "894178aa-91e4-4154-a111-7ef891564a3d"

app = Flask(__name__)

def get_powerbi_token():
    """Gets an access token from Azure AD with detailed error reporting."""
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    scope = ["https://analysis.windows.net/powerbi/api/.default"]
    
    msal_app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=authority,
        client_credential=CLIENT_SECRET,
    )
    
    result = msal_app.acquire_token_for_client(scopes=scope)
    
    if "access_token" not in result:
        error_msg = f"Token acquisition failed: {result.get('error_description', 'Unknown error')}"
        print(error_msg)
        print(f"Full error: {json.dumps(result, indent=2)}")
        return None
        
    print("✓ Successfully acquired Power BI token")
    return result['access_token']

def test_token_permissions(token):
    """Test if the token has basic Power BI API access."""
    # Try the basic (non-admin) workspaces endpoint first
    test_url = "https://api.powerbi.com/v1.0/myorg/groups"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(test_url, headers=headers)
    print(f"Basic API test - Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Basic API access works. Found {len(data.get('value', []))} accessible workspaces")
        return True, data
    else:
        print(f"✗ Basic API access failed: {response.text}")
        return False, None

def get_workspaces_basic(token):
    """Gets workspaces using basic API (non-admin) - only shows workspaces the service principal has access to."""
    workspaces_url = "https://api.powerbi.com/v1.0/myorg/groups"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(workspaces_url, headers=headers)
    
    print(f"Basic workspaces API - Status: {response.status_code}")
    
    if response.status_code == 200:
        return True, response.json()
    else:
        print(f"Error details: {response.text}")
        return False, None

def get_admin_workspaces(token):
    """Uses admin API to get ALL workspaces in tenant (requires admin permissions)."""
    workspaces_url = "https://api.powerbi.com/v1.0/myorg/admin/groups?$top=100"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(workspaces_url, headers=headers)
    
    print(f"Admin workspaces API - Status: {response.status_code}")
    
    if response.status_code == 200:
        return True, response.json()
    elif response.status_code == 403:
        print("✗ Admin API access denied. Service principal needs admin permissions.")
        return False, {"error": "Admin permissions required"}
    else:
        print(f"Error details: {response.text}")
        return False, None

def get_datasets_from_workspace(token, workspace_id, use_admin=False):
    """Gets datasets from a workspace using either basic or admin API."""
    if use_admin:
        datasets_url = f"https://api.powerbi.com/v1.0/myorg/admin/groups/{workspace_id}/datasets"
    else:
        datasets_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets"
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(datasets_url, headers=headers)
    
    if response.status_code == 200:
        return True, response.json()
    else:
        print(f"Error fetching datasets: {response.status_code} - {response.text}")
        return False, None

def diagnose_permissions(token):
    """Comprehensive permission diagnosis."""
    print("\n=== PERMISSION DIAGNOSIS ===")
    
    # Test 1: Basic API access
    print("\n1. Testing basic Power BI API access...")
    basic_works, basic_data = test_token_permissions(token)
    
    if not basic_works:
        return "CRITICAL: Basic Power BI API access failed. Check app registration and permissions."
    
    # Test 2: Try admin API
    print("\n2. Testing admin API access...")
    admin_works, admin_data = get_admin_workspaces(token)
    
    if admin_works:
        print("✓ Admin API access works!")
        workspace_count = len(admin_data.get('value', []))
        return f"SUCCESS: Admin access granted. Found {workspace_count} total workspaces in tenant."
    else:
        print("✗ Admin API access failed. Falling back to basic API...")
        
        # Test 3: Use basic API as fallback
        basic_works, workspaces = get_workspaces_basic(token)
        if basic_works:
            workspace_count = len(workspaces.get('value', []))
            return f"PARTIAL SUCCESS: Basic API works. Found {workspace_count} accessible workspaces. For full tenant access, admin permissions needed."
        else:
            return "FAILED: Neither admin nor basic API access works. Check permissions and app registration."

def query_power_bi(natural_language_query):
    """Main function with improved error handling and diagnostics."""
    print(f"\n=== PROCESSING QUERY: {natural_language_query} ===")
    
    # Step 1: Get token
    print("\n--> Getting Power BI access token...")
    token = get_powerbi_token()
    
    if not token:
        return "ERROR: Could not authenticate with Power BI. Check credentials and app registration."
    
    # Step 2: Diagnose permissions
    diagnosis = diagnose_permissions(token)
    print(f"\nDiagnosis result: {diagnosis}")
    
    # Step 3: Try to get workspaces and datasets
    print("\n--> Attempting to retrieve workspaces and datasets...")
    
    # Try admin API first, fall back to basic API
    admin_works, workspaces_data = get_admin_workspaces(token)
    use_admin = admin_works
    
    if not admin_works:
        print("--> Admin API failed, trying basic API...")
        basic_works, workspaces_data = get_workspaces_basic(token)
        if not basic_works:
            return f"ERROR: Cannot access workspaces. {diagnosis}"
    
    if not workspaces_data or not workspaces_data.get('value'):
        return "No workspaces found or accessible."
    
    # Process first available workspace
    first_workspace = workspaces_data['value'][0]
    workspace_name = first_workspace['name']
    workspace_id = first_workspace['id']
    
    print(f"--> Processing workspace: '{workspace_name}'")
    
    # Get datasets
    datasets_success, datasets_data = get_datasets_from_workspace(token, workspace_id, use_admin)
    
    if datasets_success and datasets_data.get('value'):
        dataset_names = [ds['name'] for ds in datasets_data['value']]
        result = f"SUCCESS! Connected to workspace '{workspace_name}'. Found datasets: {', '.join(dataset_names)}"
    else:
        result = f"Connected to workspace '{workspace_name}' but no datasets found or accessible."
    
    return f"{diagnosis}\n\n{result}"

# --- Flask Routes (unchanged) ---
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
