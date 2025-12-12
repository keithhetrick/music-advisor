# MAStyle Toolkit (Music Advisor design system)

SwiftUI utility-first styling toolkit, inspired by Tailwind but native to macOS. Ships as a standalone Swift Package that any Music Advisor surface can import.

What’s included

- Tokens: colors/spacing/radius/typography/shadows/borders; density scaler; reduce-motion flag; high-contrast preset.
- Surface modifiers: `.maCard()` / `.maCardInteractive()`, `.maBadge()`, `.maMetricBadge()`, `.maSectionHeader()`, `.maInput(state:)`, `.maTextArea(state:)`, `.maPickerStyle()`, `.maPickerHover()`, `.maProgressStyle()`, `.maListRowStyle()`, `.maStripedRowStyle()`, `.maButton(variant:isBusy:)`, `.maAppBackground()`, `.maGlass()`, `.maGradientBorder()`, `.maSectionTitle()`, `.maFocusRing()`, `.maAnimated(_:value:)`, `.maSegmentedStyle()`.
- Utility views: `MAIcon` / `maIcon(_)`, `maTag(_)`, `maStackSpacing(_)`, closeable chip (`MACloseableChip`), badge counts (`MABadgeCount`), breadcrumbs (`MABreadcrumbs`), toast host (`MAToastHost`), skeleton loader (`SkeletonView`), toast/alert banners.
- Layout helpers: `.maPaddedSection()`, `.maBordered()`, `.maBackgroundGradient()`, `.maTagCloud()`.
- Components: modals (dialog/sheet/toast/popup), radar/line/bar charts (vector), optional Swift Charts adapter (macOS 13+), table rows with stripes/selection/actions, form rows (helper/error), file-picker row, segmented style, interactive buttons (hover/press/busy).
- Showcase: `MAStyleShowcase` demonstrates everything live (theme/density/reduce-motion toggles, modals, alerts, toasts, charts, table rows, form rows, breadcrumbs). Full catalog + kitchen sink examples: see `docs/MAStyle_styleguide.md` at repo root.
- Theme swap: `MAStyle.theme` can be reassigned (dark/light/high-contrast), `applyDensity(scale:)`, and `reduceMotionEnabled`.
- Tests: `swift test --disable-sandbox` (optional local cache vars: `LOCAL=$PWD/.build/local && mkdir -p "$LOCAL/ModuleCache" "$LOCAL/home"; HOME="$LOCAL/home" SWIFT_MODULE_CACHE_PATH="$LOCAL/ModuleCache" LLVM_MODULE_CACHE_PATH="$LOCAL/ModuleCache" SWIFTPM_DISABLE_SANDBOX=1 swift test --disable-sandbox`).

Dev quick commands

- MAStyle tests: `cd shared/design_system && LOCAL=$PWD/.build/local && mkdir -p "$LOCAL/ModuleCache" "$LOCAL/home" && HOME="$LOCAL/home" SWIFT_MODULE_CACHE_PATH="$LOCAL/ModuleCache" LLVM_MODULE_CACHE_PATH="$LOCAL/ModuleCache" SWIFTPM_DISABLE_SANDBOX=1 swift test --disable-sandbox`
- macOS app (showcase tab lives here): `cd hosts/macos_app && HOME=$PWD/build/home SWIFTPM_DISABLE_SANDBOX=1 swift run --scratch-path $PWD/build/.swiftpm --disable-sandbox`
- Export tokens to JSON: `cd shared/design_system && ./scripts/export_tokens.swift > /tmp/ma_theme.json`
- Keyboard/animations: open the app “MAStyle” tab to see focus outlines (Tab through controls) and animations (pulse/slide/float/shake/fade); reduce-motion toggle is in Toggles section.

Usage

```swift
import MAStyle

struct Example: View {
    var body: some View {
        VStack(spacing: MAStyle.Spacing.md) {
            Text("Metric 72.4")
                .font(MAStyle.Typography.headline)
                .maMetric()

            ProgressView(value: 0.4)
                .maProgressStyle()

            MALineChart(series: [.init(points: [0.2, 0.6, 0.4], label: "Energy")])
                .frame(height: 140)
                .maCard()

            MAFormFieldRow(title: "Audio path", helper: "Pick a file") {
                MAFilePickerRow(title: "File", value: "/tmp/audio.wav", onPick: {}, onClear: {})
            }

            MACloseableChip("Tag", color: MAStyle.ColorToken.info) {}
        }
        .padding()
        .maAppBackground()
    }
}
```

Targets

- Library: `MAStyle`
- Platform: macOS 12+
- Tools: Swift 5.7+

Release checklist (publish-ready)

- Tag a version (e.g., `v0.1.0`); SwiftPM resolves by git tags.
- Run tests before tagging:

  ```bash
  cd shared/design_system
  swift test --disable-sandbox
  ```

- If embedding via git URL, update dependent manifests to the new tag.

Example Package.swift entry (git tag):

```swift
.package(url: "https://<your-repo-url>/design_system.git", from: "0.1.0")
```

Extending

- Swap `MAStyle.theme` at runtime for app-wide reskin; use `useDarkTheme()`, `useHighContrastTheme()`, `applyDensity(scale:)`, and `reduceMotionEnabled`.
- Add your own tokens/modifiers in an extension without touching the core package.
- Charts are vector-only; optional Swift Charts adapter (`MASwiftLineChart`, macOS 13+), with `MAChartsAvailability.swiftChartsAvailable` as a guard.
