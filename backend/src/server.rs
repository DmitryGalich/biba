use axum::{routing::get, Router};
use std::sync::Arc;

use crate::telemetry;

pub struct ServerConfig {
    pub listen_address: String,
}

pub struct AppState {
    config: ServerConfig,
}

pub async fn run_server(config: ServerConfig) {
    tracing::info!("Initial loading keys from Keycloak...");

    let shared_state = Arc::new(AppState { config });

    let app = Router::new()
        .route("/health", get(health_handler))
        .layer(telemetry::http_trace_layer())
        .with_state(shared_state.clone());

    let listener = tokio::net::TcpListener::bind(shared_state.config.listen_address.clone())
        .await
        .unwrap();
    tracing::info!("Started on {}", shared_state.config.listen_address.clone());
    axum::serve(listener, app).await.unwrap();
}

async fn health_handler() -> String {
    "backend health OK".to_string()
}
