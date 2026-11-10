# Cookbook

```
docker compose up --build -d
docker compose down
```

Reload nginx config (run in nginx container):
```
nginx -s realod
```

Credentials:
```
keycloak:    admin / admin_password

keycloak_db: keycloak_db_user / keycloak_db_password

realm:       biba_realm
client:      biba_client
user:        biba_user / biba_user_password
email:       biba_user@example.com
first name:  biba_first_name
second name: biba_second_name
```