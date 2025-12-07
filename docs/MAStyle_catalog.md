# MAStyle Catalog (SwiftUI design system)

Purpose

- Single-source tokens + utilities for macOS SwiftUI surfaces.
- Utility-first (Tailwind-inspired) with themes, density, reduce-motion, and a live showcase.

Core tokens

- Colors, spacing, radius, typography, shadows, borders (via `MAStyle.theme`).
- Presets: dark (default), high-contrast; density scaler (`applyDensity(scale:)`); `reduceMotionEnabled`.

Key modifiers/components

- Surfaces: `.maCard()` / `.maCardInteractive()`, `.maAppBackground()`, `.maGlass()`, `.maGradientBorder()`, `.maSectionHeader()`, `.maSectionTitle()`.
- Inputs: `.maInput(state:)`, `.maTextArea(state:)`, `.maPickerStyle()`, `.maPickerHover()`, `.maProgressStyle()`.
- Lists/Tables: `.maListRowStyle(isSelected:isDisabled:)`, `.maStripedRowStyle(index:isSelected:isDisabled:)`, `MATableRow` (striped/selectable/badge/action), `MABreadcrumbs`.
- Buttons/Chips: `maButton(variant:isBusy:)` (primary/secondary/ghost/busy), `maChip`, `MACloseableChip`, `maTag`, `MABadgeCount`.
- Feedback: `MAAlertBanner`, `MAToastBanner`, `MAToastHost` (queue), `SkeletonView`.
- Modals: `MAModal` (dialog/sheet/toast/popup), `MAModalAction`.
- Charts: `MALineChart`, `MABarChart`, `MARadarChart`; optional Swift Charts adapter (`MASwiftLineChart` macOS 13+, check `MAChartsAvailability.swiftChartsAvailable`).
- Form rows: `MAFormFieldRow` (title + helper/error), `MAFilePickerRow`.
- Segmented/Picker helpers: `.maSegmentedStyle()`, `.maPickerHover()`.
- Motion/Focus: `.maAnimated(_:value:)` respects `reduceMotionEnabled`; `.maFocusRing(_:)`.

Themes & density

- Dark: default (`useDarkTheme()`).
- High contrast: `useHighContrastTheme()`.
- Density: `applyDensity(scale: 0.85)` for compact, `1.0` for regular.
- Reduce motion: set `MAStyle.reduceMotionEnabled = true` (showcase toggle does this).

Usage snippets

```swift
// Buttons
Button("Save") { /*...*/ }.maButton(.primary)
Button("Busy") { }.maButton(.busy, isBusy: true)

// Inputs with states
TextField("Email", text: $email).maInput()
TextField("Bad", text: $bad).maInput(state: .error)

// Form rows
MAFormFieldRow(title: "Audio", helper: "Pick a file") {
    MAFilePickerRow(title: "File", value: audioPath, onPick: browse, onClear: { audioPath = "" })
}

// Table rows / breadcrumbs
MABreadcrumbs([MABreadcrumb("Home", action: goHome), MABreadcrumb("Detail")])
MATableRow(index: idx, isSelected: selected == idx, badgeCount: 2, actionTitle: "Open", action: open) {
    Text(items[idx].name)
}

// Modals
MAModal(isPresented: $showDialog, style: .dialog, title: "Confirm", actions: [MAModalAction("OK", action: save)]) {
    Text("Proceed?")
}

// Toast queue
@State var toasts: [MAToastMessage] = []
MAToastHost(queue: $toasts)
toasts.append(MAToastMessage(title: "Saved", tone: .success))

// Charts
MALineChart(series: [.init(points: data, label: "Energy")]).frame(height: 140)
if MAChartsAvailability.swiftChartsAvailable {
    if #available(macOS 13.0, *) { MASwiftLineChart(values: data) }
}
```

Showcase

- Run the macOS app and select the “MAStyle” tab to see all components, states, themes, density, reduce-motion, modals, alerts, toasts, tables, form rows, and charts.

Tests

```bash
cd shared/design_system
LOCAL=$PWD/.build/local && mkdir -p "$LOCAL/ModuleCache" "$LOCAL/home"
HOME="$LOCAL/home" SWIFT_MODULE_CACHE_PATH="$LOCAL/ModuleCache" LLVM_MODULE_CACHE_PATH="$LOCAL/ModuleCache" SWIFTPM_DISABLE_SANDBOX=1 swift test --disable-sandbox
```
