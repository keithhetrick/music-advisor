# macOS Host Architecture (MVVM + Clean)

This app is a thin host UI that drives the Music Advisor pipeline. It keeps UX responsive by isolating work on actors and routing all state through a single store.

## Layers

- **Views** (`Sources/Components`, `ContentView.swift`): SwiftUI + MAStyle only. No side effects; they receive bindings/state.
- **Store** (`Sources/Store/AppStore.swift`): single source of truth. Owns `AppState`, routes user intents to actions/services, and exposes bindings to views.
- **ViewModels** (`Sources/ViewModels`): small adapters for legacy views (e.g., `CommandViewModel`, `TrackListViewModel`, queue VM).
- **Services** (`Sources/Services`): actors/async services for IO and coordination (`ProcessingService`, `RecommendationService`, `HostCoordinator`, `RunnerService`, `TrackStore`).
- **Models** (`Sources/Models`): value types for tracks, artists, jobs, routes, snapshots.
- **Design system** (`shared/design_system`): MAStyle toolkit; theming, components, tokens.

## Navigation / Routes

- `AppRoute` (Models/Routes.swift) defines top-level navigation: `.run(ResultPane)`, `.history`, `.style`.
- Picker in `ContentView` binds to `route.tab`; run result pane binds to `route.runPane`. Changing route updates the single `AppState`.

## State flow

1. UI triggers intents (e.g., enqueue tracks, run batch, select tab/pane).
2. `AppStore.dispatch` routes into a small reducer (`reduce(_:action:)`) that mutates `AppState` in one place; side effects stay in services/actors.
3. Services publish `HostSnapshot` and progress snapshots; `AppStore` polls and updates state.
4. Views render derived slices; no service calls from views. Alerts surface via `AlertState` for structured error/info messages.

## Background isolation

- Processing, recommendation, and host coordination live on actors (`ProcessingService`, `RecommendationService`, `HostCoordinator`).
- UI updates are throttled (progress updates debounced in `CommandViewModel`).
- Heavy parsing stays off the main actor; only snapshots reach the UI.

## Queue & history

- Queue lives in `CommandViewModel.queueVM` (add/remove/clear).
- History/sidecar previews handled via store actions; previews cached in `AppState.previewCache`.
- Jobs flow: queued → processing → done/failed; history tab consumes the emitted artifacts.
- Queue snapshot is persisted to Application Support (`queue.json`) so pending jobs survive relaunch (best effort; errors are silent).
- Sidecar preview cache persists to Application Support (`preview_cache.json`) to avoid re-reading large sidecars on relaunch (best effort; limited to recent entries).

## Configuration

- `AppConfig` centralizes paths/commands/env flags. Inject for tests; avoid hard-coded paths in views.
- Feature flags and tokens live in MAStyle; theme set via `AppState.useDarkTheme`.

## Testing

- MAStyle package has unit tests (`shared/design_system` → `swift test --disable-sandbox`).
- Add store tests with fake services to validate route state, queue transitions, and error surfaces.
- Build smoke: `HOME=$PWD/build/home swift build --scratch-path $PWD/build/.swiftpm --disable-sandbox`.

## Adding features

- New tab: extend `AppTab` and `AppRoute`, add a view, and switch on `route` in `ContentView`.
- New panel: create a view component + view model if needed; wire intents through `AppStore.dispatch`.
- New service: implement as actor, expose async API, inject into the store or coordinator.

## Logging & UX notes

- Keep UI responsive: never block the main actor; throttle frequent updates.
- Surface errors via a small `AlertState`/toast (use MAStyle banners).
- Console messages are trimmed to the most recent 200 entries to reduce churn.
- Keep MAStyle the only source of styling; swap `MAStyle.theme` to reskin globally.
- Host polling backs off when idle to reduce wakeups (faster while processing).
- Logs: stdout/stderr buffered and capped (~10k chars) to avoid UI churn; preview search bounded to avoid deep walks.

## Packaging / distribution considerations (future)

- Keep the host a thin orchestrator: point the run command to the real pipeline entrypoint (`automator.sh`), preserve manual start, and let the pipeline own all heavy work.
- Favor a lean bundle: ship the app + minimal runner config; rely on an existing repo/venv where possible. For a self-contained build, bundle only the runtime and fetch large models/assets on first run into Application Support.
- Fetch assets on demand with checksums/versioning to avoid ballooning the app size; prune unused models/fixtures and avoid duplicating timestamped artifacts.
- Keep configuration overridable via env (e.g., `REPO`, data roots) so the same app can run in “lean” (external repo) or “self-contained” modes without code changes.
