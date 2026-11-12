use server::ServerConfig;
use std::env;

mod server;
mod telemetry;

impl ServerConfig {
    fn from_env() -> Self {
        let listen_address =
            env::var("LISTEN_ADDRESS").expect("Critical: LISTEN_ADDRESS should be in .env");

        ServerConfig { listen_address }
    }
}

#[tokio::main]
async fn main() {
    let _ = dotenvy::dotenv();

    let _log_guard = telemetry::init_tracing().expect("Failed to initialize logging");

    tracing::info!("Config loading...");

    let config = ServerConfig::from_env();

    tracing::info!("Config loaded");

    server::run_server(config).await;
}
