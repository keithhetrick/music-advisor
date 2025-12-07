# MAStyle Toolkit Style Guide (SwiftUI, Tailwind-style)

Use this as the single reference for every MAStyle token, modifier, and component. All examples assume:

```swift
import MAStyle
```

## Tokens & Themes

- `MAStyle.theme` drives colors/spacing/radius/typography/shadows/borders.
- Presets: `useDarkTheme()`, `useHighContrastTheme()`.
- Density: `applyDensity(scale: 0.85)` for compact, `1.0` for regular.
- Motion: set `MAStyle.reduceMotionEnabled = true` to disable animations in helpers that respect it.
- Typography: `Typography.body`, `headline`, `title`, `caption`, `bodyMono`.
- Colors: `ColorToken.background`, `panel`, `border`, `primary`, `success`, `warning`, `danger`, `info`, `muted`, `metricBG`.
- Spacing/Radius/Borders: `Spacing.*`, `Radius.*`, `Borders.*`.

## Surfaces & Layout

- Cards: `.maCard()`, `.maCardInteractive(isDisabled:)`.
- Background: `.maAppBackground()`, `.maGlass()`, `.maGradientBorder()`.
- Sections: `.maSectionHeader()`, `.maSectionTitle()`, `.maPaddedSection()`, `.maBordered()`.
- Focus ring helper: `.maFocusRing(_:)` for custom overlays.
- Animations: `.maAnimated(_:value:)` (respects reduce motion).

Example (surface combo):

```swift
VStack { ... }
  .maCardInteractive()
  .maGradientBorder()
  .maAnimated(.easeOut(duration: 0.15), value: state)
```

## Text & Icons

- Text styles: `.maText(.title|.headline|.body|.mono|.caption)`.
- Icons: `MAIcon("bolt.fill", size: 14)`, or `maIcon("bolt.fill")`.
- Tags: `maTag("Live", icon: "waveform.path.ecg", tone: .success)`.

## Buttons

- `.maButton(.primary|.secondary|.ghost|.busy, isBusy: Bool = false)` — hover/press, busy shows spinner.

## Chips & Badges

- Chips: `.maChip(style: .solid|.outline, color:, isDisabled:)`.
- Closeable chip: `MACloseableChip("Tag", color: ..., onClose: {})`.
- Badges: `.maBadge(.info|.success|.warning|.danger|.neutral)`, `.maMetric()` (metric pill), `MABadgeCount(5, tone: .info)`.

## Inputs & Forms

- Inputs: `.maInput(state: .normal|.error|.disabled)`, `.maTextArea(state:)`.
- Form rows: `MAFormFieldRow(title:helper:error:) { TextField(...).maInput() }`.
- File picker row: `MAFilePickerRow(title: "File", value: path, onPick: {}, onClear: {})`.
- Progress: `.maProgressStyle()`.
- Focus helper: `.maFocusable($isFocused)` (adds focus outline).

## Pickers / Segmented / Toggles / Sliders

- Picker style: `.maPickerStyle()`; hover: `.maPickerHover()`; focus overlay: `.maPickerFocus($isFocused)`.
- Segmented: `.maSegmentedStyle()` (use with `.pickerStyle(.segmented)`).
- Toggles: `.maToggleStyle()` (switch + tint).
- Sliders: `.maSliderStyle()`.

## Lists / Tables

- Rows: `.maListRowStyle(isSelected:isDisabled:isFocused:)`.
- Striped rows: `.maStripedRowStyle(index:isSelected:isDisabled:isFocused:)`.
- Table rows with badges/actions: `MATableRow(index:..., badgeCount:, actionTitle:, action:) { ... }`.
- Focusable table row: `MAFocusableTableRow(...) { ... }` (adds focus outline).
- Breadcrumbs: `MABreadcrumbs([MABreadcrumb("Home", action: {}), MABreadcrumb("Detail")])`.

## Feedback: Alerts, Toasts, Skeleton

- Alert banner: `MAAlertBanner(title:, message:, tone:, dismissible:, onDismiss:)`.
- Toast banner: `MAToastBanner(title:, tone:)`.
- Toast host/queue: `@State var toasts: [MAToastMessage] = []; MAToastHost(queue: $toasts); toasts.append(MAToastMessage(title:"Saved", tone:.success))`.
- Skeleton loader: `SkeletonView(height: 12)`.

## Modals

- `MAModal(isPresented:, style: .dialog|.sheet|.toast|.popup, title:, actions:, content:)`.
- Actions: `MAModalAction("OK", action: {})`.

## Charts

- Vector charts: `MALineChart(series:)`, `MABarChart(entries:/values+labels)`, `MARadarChart(axes:/values+labels)`.
- Swift Charts (macOS 13+): `MASwiftLineChart(values:)` guarded by `if MAChartsAvailability.swiftChartsAvailable`.

## Motion, Density, Themes (chaining)

```swift
MAStyle.useHighContrastTheme()
MAStyle.applyDensity(scale: 0.9)
MAStyle.reduceMotionEnabled = true
```

## Composition Examples

- Card with list rows and actions:

```swift
VStack {
  ForEach(items.indices, id: \.self) { i in
    MAFocusableTableRow(index: i,
                        isSelected: selected == i,
                        badgeCount: items[i].count,
                        actionTitle: "Open",
                        action: { open(items[i]) }) {
      Text(items[i].title)
    }
  }
}
.maCardInteractive()
```

- Form section:

```swift
MAFormFieldRow(title: "Audio", helper: "Select a source") {
  MAFilePickerRow(title: "File",
                  value: audioPath,
                  onPick: pickAudio,
                  onClear: { audioPath = "" })
}
MAFormFieldRow(title: "Notes", error: hasError ? "Required" : nil) {
  TextEditor(text: $notes).maTextArea(state: hasError ? .error : .normal)
}
```

- Controls with focus + motion aware:

```swift
@State var sliderFocus = false
Slider(value: $value)
  .maSliderStyle()
  .maFocusable($sliderFocus)
  .maAnimated(.spring(), value: value)
```

## Everything-on-one (kitchen sink)

```swift
struct Dashboard: View {
    @State var toasts: [MAToastMessage] = []
    @State var audioPath = "/tmp/audio.wav"
    @State var sliderVal = 0.4
    @State var rowFocus = false

    var body: some View {
        VStack(spacing: MAStyle.Spacing.lg) {
            HStack {
                Text("Session A").maText(.title)
                Spacer()
                MABreadcrumbs([
                    MABreadcrumb("Home", action: {}),
                    MABreadcrumb("Projects", action: {}),
                    MABreadcrumb("Session A")
                ])
            }
            .maCardInteractive()

            HStack(spacing: MAStyle.Spacing.md) {
                VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                    MAFormFieldRow(title: "Audio", helper: "Select a source") {
                        MAFilePickerRow(title: "File", value: audioPath, onPick: {}, onClear: { audioPath = "" })
                    }
                    MAFormFieldRow(title: "Notes") {
                        TextEditor(text: .constant("")).maTextArea()
                    }
                }
                .frame(maxWidth: 360)
                VStack(spacing: MAStyle.Spacing.sm) {
                    Text("LUFS -10.1").maMetric()
                    Text("Peak -0.8").maBadge(.warning)
                    Text("Norms OK").maBadge(.success)
                }
                .maCard()
            }
            .maCard()

            VStack(spacing: MAStyle.Spacing.xs) {
                ForEach(0..<3) { i in
                    MAFocusableTableRow(
                        index: i,
                        isSelected: i == 1,
                        badgeCount: i == 2 ? 3 : nil,
                        actionTitle: "Open",
                        action: { toasts.append(.init(title: "Opened \(i)", tone: .info)) }
                    ) {
                        Text("Item \(i + 1)")
                    }
                }
            }
            .maCardInteractive()

            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                Picker("Mode", selection: .constant(0)) {
                    Text("Energy").tag(0)
                    Text("Dyn").tag(1)
                }
                .pickerStyle(.segmented)
                .maSegmentedStyle()

                MALineChart(series: [.init(points: [0.2,0.6,0.4,0.7], label: "Energy")])
                    .frame(height: 140)
                    .maCard()
            }
            .maCard()

            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                HStack(spacing: MAStyle.Spacing.sm) {
                    Button("Run") { toasts.append(.init(title: "Run started", tone: .success)) }.maButton(.primary)
                    Button("Busy") {}.maButton(.busy, isBusy: true)
                    Button("Ghost") {}.maButton(.ghost)
                }
                Slider(value: $sliderVal).maSliderStyle().maFocusable($rowFocus)
                Toggle("Enable", isOn: .constant(true)).maToggleStyle()
            }
            .maCard()
        }
        .padding()
        .maAppBackground()
        .overlay(MAToastHost(queue: $toasts))
    }
}
```

## Chains / combos (quick reference)

- Card + gradient + hover: `.maCardInteractive().maGradientBorder()`
- Error input with helper: `MAFormFieldRow(title:"Name", error:"Required") { TextField("", text:$t).maInput(state:.error) }`
- Striped selectable row with focus: `.maStripedRowStyle(index:i, isSelected: sel==i, isFocused: focus==i)`
- Segmented styled + picker hover: `.pickerStyle(.segmented).maSegmentedStyle().maPickerHover()`
- Toast queue trigger: `toasts.append(MAToastMessage(title:"Saved", tone:.success))`
- Reduce motion: `MAStyle.reduceMotionEnabled = true`
- Density: `MAStyle.applyDensity(scale:0.9)`
- High contrast: `MAStyle.useHighContrastTheme()`

## Showcase

- Run the macOS app and select the “MAStyle” tab to see every element, with toggles for theme/density/reduce-motion, plus modals, alerts, toasts, tables, form rows, charts, and state playground.

## Tests

```bash
cd shared/design_system
LOCAL=$PWD/.build/local && mkdir -p "$LOCAL/ModuleCache" "$LOCAL/home"
HOME="$LOCAL/home" SWIFT_MODULE_CACHE_PATH="$LOCAL/ModuleCache" LLVM_MODULE_CACHE_PATH="$LOCAL/ModuleCache" SWIFTPM_DISABLE_SANDBOX=1 swift test --disable-sandbox
```

## Quick run (macOS app with MAStyle tab)

```bash
cd hosts/macos_app
HOME=$PWD/build/home SWIFTPM_DISABLE_SANDBOX=1 swift run --scratch-path $PWD/build/.swiftpm --disable-sandbox
```

## Tokens for other stacks

- Export to JSON: `cd shared/design_system && ./scripts/export_tokens.swift > /tmp/ma_theme.json`
- C++/JUCE stub: see `shared/design_system/export/ma_tokens.hpp` (placeholder values; feed from exported JSON).

## Keyboard navigation

- Focus helpers: `.maFocusable(_:)`, `.maPickerFocus(_:)`, row focus params on `maListRowStyle` / `maStripedRowStyle` / `MAFocusableTableRow`.
- Showcase includes a keyboard demo section (Tab through buttons/rows to see focus outlines).
