import json
import urllib.parse
import urllib.request
import sys
import base64
import time

# --- CONFIGURATION ---
GATEWAY_URL = "http://localhost"
KEYCLOAK_URL = f"{GATEWAY_URL}/auth" 

ADMIN_USER = "admin"
ADMIN_PASS = "admin_password"

REALM = "biba_realm"
CLIENT = "biba_client"
TEST_USER = "biba_user"
TEST_PASS = "biba_user_password"
TEST_EMAIL = "biba_user@example.com"
TEST_FIRST = "biba_first_name"
TEST_LAST = "biba_second_name"

# Console Colors
GREEN, RED, YELLOW, Cyan, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[0m"

def api_request(url, method="GET", data=None, headers=None, is_json=False):
    req_data = None
    headers = headers or {}
    
    if data:
        if is_json:
            req_data = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        else:
            req_data = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read().decode("utf-8")
            try: return response.status, json.loads(body) if body else None
            except: return response.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try: return e.code, json.loads(body)
        except: return e.code, body
    except Exception as e:
        return 0, str(e)

def check_gateway():
    print("1. Checking Nginx Gateway availability (/gateway_test)... ", end="", flush=True)
    status, res = api_request(f"{GATEWAY_URL}/gateway_test")
    if status == 200 and "gateway_test" in str(res):
        print(f"{GREEN}OK (Status {status}){RESET}")
    else:
        print(f"{RED}FAIL (Status {status}). Please check the 'gateway' container.{RESET}")
        sys.exit(1)

def check_http():
    print("2. Checking Keycloak proxy routing (/auth/realms/master)... ", end="", flush=True)
    url = f"{KEYCLOAK_URL}/realms/master"
    status, _ = api_request(url)
    if status == 200:
        print(f"{GREEN}OK (Status {status}){RESET}")
    else:
        print(f"{RED}FAIL (Status {status}). Please check the 'keycloak' container.{RESET}")
        sys.exit(1)

def get_admin_token():
    print(f"3. Authenticating administrator ({ADMIN_USER})... ", end="", flush=True)
    url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    data = {"client_id": "admin-cli", "username": ADMIN_USER, "password": ADMIN_PASS, "grant_type": "password"}
    status, res = api_request(url, method="POST", data=data)
    
    if status == 200 and isinstance(res, dict) and "access_token" in res:
        print(f"{GREEN}OK (Token received){RESET}")
        return res["access_token"]
    else:
        print(f"{RED}FAIL (Status {status}).{RESET}")
        sys.exit(1)

def check_realm(headers):
    print(f"4. Verifying existence of realm '{REALM}'... ", end="", flush=True)
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}"
    status, res = api_request(url, method="GET", headers=headers)
    if status == 200:
        print(f"{GREEN}OK{RESET}")
    else:
        print(f"{RED}FAIL. Realm not found (Status {status}).{RESET}")
        sys.exit(1)

def check_client(headers):
    print(f"5. Verifying existence of client '{CLIENT}'... ", end="", flush=True)
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients?clientId={CLIENT}"
    status, res = api_request(url, method="GET", headers=headers)
    
    if status == 200 and isinstance(res, list) and len(res) > 0 and res[0].get("clientId") == CLIENT:
        print(f"{GREEN}OK{RESET}")
    else:
        print(f"{RED}FAIL. Client not found.{RESET}")
        sys.exit(1)

def manage_user(headers):
    print(f"6. Checking for test user '{TEST_USER}'... ", end="", flush=True)
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users?username={TEST_USER}"
    status, res = api_request(url, method="GET", headers=headers)
    
    if status == 200 and isinstance(res, list) and len(res) > 0:
        print(f"{GREEN}OK (Exists){RESET}")
        return res[0].get("id"), False
        
    print(f"{YELLOW}Not found. Creating user...{RESET} ", end="", flush=True)
    user_data = {"username": TEST_USER, "enabled": True, "email": TEST_EMAIL, "firstName": TEST_FIRST, "lastName": TEST_LAST}
    status, _ = api_request(f"{KEYCLOAK_URL}/admin/realms/{REALM}/users", method="POST", data=user_data, headers=headers, is_json=True)
    
    if status == 201:
        _, search_res = api_request(url, headers=headers)
        user_id = search_res[0].get("id")
        
        pass_url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}/reset-password"
        pass_data = {"type": "password", "value": TEST_PASS, "temporary": False}
        pass_status, _ = api_request(pass_url, method="PUT", data=pass_data, headers=headers, is_json=True)
        
        if pass_status == 204:
            print(f"{GREEN}User successfully created.{RESET}")
            return user_id, True
            
    print(f"{RED}FAIL. User creation failed (Status {status}).{RESET}")
    sys.exit(1)

def test_user_auth():
    print(f"7. Testing End-to-End user authentication ({TEST_USER})... ", end="", flush=True)
    url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    data = {"client_id": CLIENT, "username": TEST_USER, "password": TEST_PASS, "grant_type": "password"}
    status, res = api_request(url, method="POST", data=data)
    
    if status == 200 and res and "access_token" in res:
        print(f"{GREEN}SUCCESS! Access Token obtained.{RESET}")
        return res["access_token"]
    else:
        print(f"{RED}FAIL. Make sure 'Direct Access Grants' is enabled for client '{CLIENT}' (Status {status}).{RESET}")
        sys.exit(1)

def decode_and_print_token(token):
    print(f"8. Decoding JWT Token payload... ", end="", flush=True)
    try:
        payload_b64 = token.split('.')[1]
        payload_b64 += '=' * (-len(payload_b64) % 4) # Fix padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode('utf-8'))
        print(f"{GREEN}OK{RESET}")
        
        exp_time = payload.get("exp", 0) - int(time.time())
        roles = payload.get("realm_access", {}).get("roles", [])
        
        print(f"   -> {Cyan}Token Expires In:{RESET} {exp_time} seconds")
        print(f"   -> {Cyan}Authorized Roles:{RESET} {roles}")
    except Exception as e:
        print(f"{RED}FAIL. Could not parse token payload: {e}{RESET}")

def check_database_status(headers):
    print("9. Inspecting database status from Keycloak... ", end="", flush=True)
    url = f"{KEYCLOAK_URL}/admin/serverinfo"
    status, res = api_request(url, method="GET", headers=headers)
    
    if status == 200 and isinstance(res, dict) and "profileInfo" in res:
        db_name = res.get("systemInfo", {}).get("databaseName", "PostgreSQL")
        print(f"{GREEN}OK (Keycloak is connected to {db_name} inside the Docker network){RESET}")
    else:
        print(f"{YELLOW}WARNING (Could not fetch database server info, status {status}){RESET}")

def cleanup_user(user_id, headers):
    print(f"10. Cleaning up: Removing test user ID '{user_id}'... ", end="", flush=True)
    url = f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}"
    status, _ = api_request(url, method="DELETE", headers=headers)
    if status == 204:
        print(f"{GREEN}SUCCESS (Workspace clean){RESET}")
    else:
        print(f"{YELLOW}WARNING (Failed to remove user, status {status}){RESET}")

def main():
    print("=== Starting Full Docker / Keycloak Infrastructure Health Check ===")
    check_gateway()
    check_http()
    
    admin_token = get_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    check_realm(headers)
    check_client(headers)
    
    created_user_id = None
    was_created_by_script = False
    
    try:
        created_user_id, was_created_by_script = manage_user(headers)
        user_token = test_user_auth()
        decode_and_print_token(user_token)
        check_database_status(headers)
    finally:
        if created_user_id and was_created_by_script:
            cleanup_user(created_user_id, headers)
            
    print("=== All configuration health checks completed successfully! ===")

if __name__ == "__main__":
    main()
