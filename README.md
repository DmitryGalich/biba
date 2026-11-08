# Biba


## API

```
http://127.0.0.1:80/gateway_test/
```

Keycloak:
```
http://127.0.0.1:80/auth/
```

## Cookbook

```
docker compose up --build -d
docker compose down
```

Reload nginx confing (run in nginx container):
```
nginx -s realod
```

Credentials:
```
KC_DB_USERNAME: keycloak_db_user
KC_DB_PASSWORD: keycloak_db_password
KC_BOOTSTRAP_ADMIN_USERNAME: admin
KC_BOOTSTRAP_ADMIN_PASSWORD: admin_password
```