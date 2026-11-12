use std::{env, fs, io};
use tower_http::{
    classify::{ServerErrorsAsFailures, SharedClassifier},
    trace::{DefaultMakeSpan, DefaultOnResponse, TraceLayer},
};
use tracing::Level;
use tracing_appender::non_blocking::WorkerGuard;
use tracing_subscriber::{field::MakeExt, layer::SubscriberExt, util::SubscriberInitExt};

pub fn init_tracing() -> io::Result<WorkerGuard> {
    let log_dir = env::var("LOG_DIR").unwrap_or_else(|_| "logs".to_string());
    let log_file = env::var("LOG_FILE").unwrap_or_else(|_| "app.log".to_string());

    let default_filter = "rust_backend=info,axum=info,tower_http=info";

    fs::create_dir_all(&log_dir)?;

    let file_appender = tracing_appender::rolling::daily(&log_dir, &log_file);
    let (non_blocking_file, guard) = tracing_appender::non_blocking(file_appender);

    let env_filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| default_filter.into());

    let stdout_layer = tracing_subscriber::fmt::layer().with_target(true);

    let file_layer = tracing_subscriber::fmt::layer()
        .with_writer(non_blocking_file)
        .with_ansi(false)
        .with_target(true)
        .fmt_fields(
            tracing_subscriber::fmt::format::debug_fn(|writer, field, value| {
                write!(writer, "{}={:?}", field, value)
            })
            .delimited(" "),
        );

    tracing_subscriber::registry()
        .with(env_filter)
        .with(stdout_layer)
        .with(file_layer)
        .init();

    std::panic::set_hook(Box::new(|panic_info| {
        tracing::error!(%panic_info, "Application panicked");
    }));

    Ok(guard)
}

pub fn http_trace_layer(
) -> TraceLayer<SharedClassifier<ServerErrorsAsFailures>, DefaultMakeSpan, (), DefaultOnResponse> {
    TraceLayer::new_for_http()
        // Логируем начало запроса на уровне INFO
        .make_span_with(DefaultMakeSpan::new().level(Level::INFO))
        // Отключаем лишний лог при получении запроса (достаточно спана и ответа)
        .on_request(())
        // Логируем ответ со статусом и временем выполнения на уровне INFO
        .on_response(DefaultOnResponse::new().level(Level::INFO))
}
