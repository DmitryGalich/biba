# Cookbook

```bash
docker compose up --build -d
docker compose down
```

If error while compiling container for developing in VSCode:
```PowerShell
[Environment]::SetEnvironmentVariable(
    "BUILDX_BAKE_ENTITLEMENTS_FS",
    "0",
    "User"
)
```

Reload nginx config (run in nginx container):
```bash
nginx -s realod
```

API:

```
http://127.0.0.1:80/gateway_test

http://127.0.0.1:80/api/health
```