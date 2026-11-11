use server::ServerConfig;
use std::env;

mod server;

impl ServerConfig {
    fn from_env() -> Self {
        let listen_address = env::var("LISTEN_ADDRESS").expect("Critical: LISTEN_ADDRESS should be in .env");

        ServerConfig {
            listen_address,
        }
    }
}

#[tokio::main]
async fn main() {
    let _ = dotenvy::dotenv();

    tracing_subscriber::fmt()
        .with_env_filter(
            env::var("RUST_LOG").unwrap_or_else(|_| "rust_backend=info,axum=info".into()),
        )
        .init();

    tracing::info!("Config loading...");

    let config = ServerConfig::from_env();

    tracing::info!("Config loaded");

    server::run_server(config).await;
}
