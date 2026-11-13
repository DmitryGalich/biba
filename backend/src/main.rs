use server::ServerConfig;
use std::env;

mod server;
mod telemetry;

impl ServerConfig {
    fn from_env() -> Self {
        let listen_address =
            env::var("LISTEN_ADDRESS").expect("Critical: LISTEN_ADDRESS should be in .env");
        let keycloak_url =
            env::var("KEYCLOAK_URL").expect("Critical: KEYCLOAK_URL should be in .env");
        let keycloak_realm =
            env::var("KEYCLOAK_REALM").expect("Critical: KEYCLOAK_REALM should be in .env");
        let keycloak_audience =
            env::var("KEYCLOAK_AUDIENCE").unwrap_or_else(|_| "account".to_string());

        ServerConfig {
            listen_address,
            keycloak_url,
            keycloak_realm,
            keycloak_audience,
        }
    }
}

#[tokio::main]
async fn main() {
    let _ = dotenvy::dotenv();

    let _log_guard = telemetry::init_tracing().expect("Failed to initialize logging");

    tracing::info!("Config loading...");

    let config = ServerConfig::from_env();

    tracing::info!(?config, "Config loaded");

    server::run_server(config).await;
}
