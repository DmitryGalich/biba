import json
from pathlib import Path
import requests
import base64

# Базовые URL вашего окружения
BASE_URL = "http://localhost"
CONFIG_PATH = Path(__file__).parent / "credentials.json"


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Файл конфигурации не найден: {path}")
    
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_access_token(config: dict) -> str:
    realm = config["realm"]
    token_url = f"{BASE_URL}/auth/realms/{realm}/protocol/openid-connect/token"

    payload = {
        "grant_type": "password",
        "client_id": config["client"],
        "username": config["user"]["username"],
        "password": config["user"]["password"],
    }

    # Если в будущем добавите "client_secret" в JSON, он подхватится автоматически
    if config.get("client_secret"):
        payload["client_secret"] = config["client_secret"]

    response = requests.post(token_url, data=payload)

    if response.status_code != 200:
        raise RuntimeError(
            f"Ошибка получения токена ({response.status_code}): {response.text}"
        )

    return response.json()["access_token"]


def call_protected_profile(token: str):
    profile_url = f"{BASE_URL}/api/profile"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(profile_url, headers=headers)
    print(f"Статус ответа от /api/profile: {response.status_code}")
    print(f"Тело ответа: {response.text}")

def debug_token(token: str):
    payload_b64 = token.split(".")[1]
    # Добавляем выравнивание base64
    payload_b64 += "=" * (-len(payload_b64) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload_b64))
    print("Содержимое токена (iss и aud):")
    print("  iss:", claims.get("iss"))
    print("  aud:", claims.get("aud"))

if __name__ == "__main__":
    cfg = load_config(CONFIG_PATH)

    print(f"1. Запрашиваем токен для пользователя '{cfg['user']['username']}' в реалме '{cfg['realm']}'...")
    access_token = get_access_token(cfg)
    print(f"Токен успешно получен (первые 30 символов): {access_token[:30]}...\n")

    debug_token(access_token)

    print("2. Делаем запрос в защищенный роут /api/profile...")
    call_protected_profile(access_token)
