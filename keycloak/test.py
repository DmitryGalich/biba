import json
import urllib.parse
import urllib.request
import sys

KEYCLOAK_URL = "http://localhost/auth" 
ADMIN_USER = "admin"
ADMIN_PASS = "admin_password"

# Цвета для консоли
GREEN, RED, RESET = "\033[92m", "\033[91m", "\033[0m"

def api_request(url, method="GET", data=None):
    req_data = None
    headers = {}
    
    if data:
        req_data = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
            
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try: return e.code, json.loads(body)
        except: return e.code, body
    except Exception as e:
        return 0, str(e)

def check_http():
    print("1. Проверка доступности Keycloak HTTP... ", end="", flush=True)
    url = f"{KEYCLOAK_URL}/realms/master"
    status, _ = api_request(url)
    if status == 200:
        print(f"{GREEN}OK (Status {status}){RESET}")
    else:
        print(f"{RED}FAIL (Status {status}).{RESET}")
        sys.exit(1)

def get_admin_token():
    print(f"2. Авторизация администратора ({ADMIN_USER})... ", end="", flush=True)
    url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    
    data = {
        "client_id": "admin-cli",
        "username": ADMIN_USER,
        "password": ADMIN_PASS,
        "grant_type": "password"
    }
    
    status, res = api_request(url, method="POST", data=data)
    
    if status == 200 and isinstance(res, dict) and "access_token" in res:
        print(f"{GREEN}OK (Токен получен){RESET}")
        return res["access_token"]
    else:
        print(f"{RED}FAIL.{RESET}")
        print(f"   HTTP Статус: {status}")
        print(f"   Ответ сервера: {res}")
        sys.exit(1)

def main():
    check_http()
    admin_token = get_admin_token()

if __name__ == "__main__":
    main()
