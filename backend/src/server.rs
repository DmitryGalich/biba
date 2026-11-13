use axum::{routing::get, Extension, Router};
use axum_keycloak_auth::{
    instance::{KeycloakAuthInstance, KeycloakConfig},
    layer::KeycloakAuthLayer,
    token::KeycloakToken,
    Url,
};
use std::sync::Arc;

use crate::telemetry;

#[derive(Debug)]
pub struct ServerConfig {
    pub listen_address: String,
    pub keycloak_url: String,
    pub keycloak_realm: String,
    pub keycloak_audience: String,
}

pub struct AppState {
    config: ServerConfig,
}

pub async fn run_server(config: ServerConfig) {
    let keycloak_url = Url::parse(&config.keycloak_url).expect("Invalid KEYCLOAK_URL");

    let keycloak_auth_instance = KeycloakAuthInstance::new(
        KeycloakConfig::builder()
            .server(keycloak_url)
            .realm(config.keycloak_realm.clone())
            .build(),
    );

    let keycloak_layer = KeycloakAuthLayer::<String>::builder()
        .instance(keycloak_auth_instance)
        .expected_audiences(vec![config.keycloak_audience.clone()])
        .build();

    let shared_state = Arc::new(AppState { config });

    let protected_routes = Router::new()
        .route("/profile", get(profile_handler))
        .layer(keycloak_layer);

    let app = Router::new()
        .route("/health", get(health_handler))
        .merge(protected_routes)
        .layer(telemetry::http_trace_layer())
        .with_state(shared_state.clone());

    let listener = tokio::net::TcpListener::bind(&shared_state.config.listen_address)
        .await
        .unwrap();

    tracing::info!("Started on {}", shared_state.config.listen_address);
    axum::serve(listener, app).await.unwrap();
}

async fn health_handler() -> String {
    "backend health OK".to_string()
}

async fn profile_handler(Extension(token): Extension<KeycloakToken<String>>) -> String {
    tracing::info!(user_id = %token.subject, "Authorized user accessed /profile");
    format!(
        "Authenticated! User ID: {}, Roles: {:?}",
        token.subject, token.roles
    )
}
