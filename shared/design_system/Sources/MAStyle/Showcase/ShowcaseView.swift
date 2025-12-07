import SwiftUI

/// Lightweight showcase to visualize MAStyle tokens/components.
public struct MAStyleShowcase: View {
    public init() {}

    @State private var showDialog = false
    @State private var showSheet = false
    @State private var showToast = false
    @State private var showPopup = false
    @State private var showBanner = true
    @State private var useHighContrast = false
    @State private var useCompact = false
    @State private var reduceMotionToggle = false
    @State private var toastQueue: [MAToastMessage] = []
    @State private var toggleFocused: Bool = false
    @State private var sliderFocused: Bool = false
    @FocusState private var keyboardFocus: Int?

    public var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.lg) {
                header
                badges
                inputs
                progress
                charts
                tagsAndButtons
                modalsSection
                alertsSection
                skeletonSection
                Group {
                    togglesSection
                    segmentedSection
                    statesPlayground
                    keyboardSection
                }
            }
            .padding(MAStyle.Spacing.lg)
            .maAppBackground()
        }
        .overlay(modalOverlays)
        .overlay(
            MAToastHost(queue: $toastQueue)
        )
        .onChange(of: useHighContrast) { value in
            if value {
                MAStyle.useHighContrastTheme()
            } else {
                MAStyle.useDarkTheme()
            }
        }
        .onChange(of: useCompact) { value in
            MAStyle.applyDensity(scale: value ? 0.85 : 1.0)
        }
        .onChange(of: reduceMotionToggle) { value in
            MAStyle.reduceMotionEnabled = value
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("MAStyle Showcase")
                .font(MAStyle.Typography.title)
            Text("Tokens + components in one glance.")
                .foregroundColor(MAStyle.ColorToken.muted)
                .font(MAStyle.Typography.body)
        }
        .maCard()
    }

    private var badges: some View {
        HStack(spacing: MAStyle.Spacing.sm) {
            Text("Metric 72.4").maMetric()
            Text("Success").maBadge(.success)
            Text("Warning").maBadge(.warning)
            Text("Info").maBadge(.info)
        }
        .maCard()
    }

    private var inputs: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Inputs").font(MAStyle.Typography.headline)
            TextField("Placeholder", text: .constant(""))
                .maInput()
            TextEditor(text: .constant("Multiline text"))
                .frame(height: 80)
                .maTextArea()
            Picker("Picker", selection: .constant("A")) {
                Text("A").tag("A")
                Text("B").tag("B")
            }
            .pickerStyle(.menu)
            .maPickerStyle()
            TextField("Disabled input", text: .constant("Disabled"))
                .maInput(state: .disabled)
            TextField("Error input", text: .constant("Invalid value"))
                .maInput(state: .error)
            MAFormFieldRow(title: "Labeled input", helper: "Helper text here") {
                TextField("Enter value", text: .constant(""))
                    .maInput()
            }
            MAFormFieldRow(title: "Errored input", error: "This field is required") {
                TextField("Bad value", text: .constant(""))
                    .maInput(state: .error)
            }
            MAFilePickerRow(title: "Audio file", value: "/path/to/audio.wav", onPick: {}) {}
        }
        .maCard()
    }

    private var progress: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Progress").font(MAStyle.Typography.headline)
            ProgressView(value: 0.35)
                .maProgressStyle()
            ProgressView(value: 0.78)
                .maProgressStyle()
        }
        .maCard()
    }

    private var charts: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Charts").font(MAStyle.Typography.headline)
            MALineChart(series: [.init(points: [0.2, 0.6, 0.4, 0.8, 0.7], label: "Energy")])
                .frame(height: 140)
                .maCard()
            MABarChart(values: [0.3, 0.5, 0.9, 0.4], labels: ["HCI", "Axes", "Echo", "Plan"])
                .frame(height: 160)
                .maCard()
            MARadarChart(values: [0.6, 0.8, 0.7, 0.4, 0.9], labels: ["Loud", "Dyn", "Echo", "Plan", "Norms"])
                .frame(height: 220)
                .maCard()
            if MAChartsAvailability.swiftChartsAvailable {
                if #available(macOS 13.0, *) {
                    MASwiftLineChart(values: [0.1, 0.3, 0.6, 0.4]).frame(height: 140).maCard()
                }
            } else {
                Text("Swift Charts not available on this OS/toolchain.")
                    .font(MAStyle.Typography.caption)
                    .foregroundColor(MAStyle.ColorToken.muted)
            }
        }
        .maCard()
    }

    private var tagsAndButtons: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
            Text("Tags & Buttons").font(MAStyle.Typography.headline)
            HStack(spacing: MAStyle.Spacing.sm) {
                Text("New").maChip()
                Text("Draft").maChip(style: .outline)
                maTag("AI Assist", icon: "sparkles", tone: .info)
                maTag("Live", icon: "waveform.path.ecg", tone: .success)
                MACloseableChip("Closeable", color: MAStyle.ColorToken.warning) {}
            }
            HStack(spacing: MAStyle.Spacing.sm) {
                Button("Primary") {}.maButton(.primary)
                Button("Secondary") {}.maButton(.secondary)
                Button("Ghost") {}.maButton(.ghost)
                Button("Busy") {}.maButton(.busy, isBusy: true)
            }
        }
        .maCard()
    }

    private var modalsSection: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
            Text("Modals / Popups").font(MAStyle.Typography.headline)
            HStack(spacing: MAStyle.Spacing.sm) {
                Button("Dialog") { showDialog = true }.maButton(.primary)
                Button("Sheet") { showSheet = true }.maButton(.secondary)
                Button("Toast") {
                    toastQueue.append(MAToastMessage(title: "Background saved", tone: .success))
                }.maButton(.ghost)
                Button("Popup") { showPopup = true }.maButton(.primary)
            }
        }
        .maCard()
    }

    private var alertsSection: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Alerts / Toasts").font(MAStyle.Typography.headline)
            if showBanner {
                MAAlertBanner(title: "Pipeline warning",
                              message: "One track is missing LUFS; please reprocess.",
                              tone: .warning,
                              dismissible: true,
                              onDismiss: { showBanner = false })
            }
            HStack {
                MAToastBanner(title: "Saved settings", tone: .success)
                Spacer()
            }
        }
        .maCard()
    }

    private var skeletonSection: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Skeleton Loader").font(MAStyle.Typography.headline)
            ForEach(0..<3, id: \.self) { _ in
                SkeletonView(height: 12, cornerRadius: MAStyle.Radius.sm)
            }
        }
        .maCard()
    }

    private var togglesSection: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Toggles").font(MAStyle.Typography.headline)
            Toggle("High Contrast Theme", isOn: $useHighContrast)
                .maToggleStyle()
            Toggle("Compact Density", isOn: $useCompact)
                .maToggleStyle()
            Toggle("Reduce Motion (showcase only)", isOn: $reduceMotionToggle)
                .maToggleStyle()
        }
        .maCard()
    }

    private var segmentedSection: some View {
            VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                Text("Segmented & Badges").font(MAStyle.Typography.headline)
                Picker("Mode", selection: .constant(0)) {
                    Text("One").tag(0)
                    Text("Two").tag(1)
                Text("Three").tag(2)
            }
            .pickerStyle(.segmented)
            .maSegmentedStyle()
            HStack(spacing: MAStyle.Spacing.sm) {
                MABadgeCount(3, tone: .info)
                MABadgeCount(1, tone: .warning)
                MABadgeCount(9, tone: .danger)
            }
            MABreadcrumbs([
                MABreadcrumb("Home", action: {}),
                MABreadcrumb("Library", action: {}),
                MABreadcrumb("Detail")
            ])
            VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                ForEach(0..<3, id: \.self) { idx in
                    MAFocusableTableRow(index: idx, isSelected: idx == 1, badgeCount: idx == 2 ? 4 : nil, actionTitle: "Action", action: {}) {
                        Text("Row \(idx + 1)")
                    }
                }
            }
        }
        .maCard()
    }

    private var statesPlayground: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("State Playground").font(MAStyle.Typography.headline)
            HStack(spacing: MAStyle.Spacing.sm) {
                Button("Hover me") {}.maButton(.primary)
                Button("Disabled") {}.maButton(.secondary).disabled(true)
                Button("Busy") {}.maButton(.busy, isBusy: true)
            }
            VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                Text("Sliders / Toggles").maText(.caption)
                Slider(value: .constant(0.4)).maSliderStyle().maFocusable($sliderFocused)
                Toggle("Enabled", isOn: .constant(true)).maToggleStyle().maFocusable($toggleFocused)
                Toggle("Disabled", isOn: .constant(false)).maToggleStyle().disabled(true)
                Text("Focused toggle: \(toggleFocused ? "Yes" : "No") | Focused slider: \(sliderFocused ? "Yes" : "No")")
                    .maText(.caption)
                    .foregroundColor(MAStyle.ColorToken.muted)
            }
        }
        .maCard()
    }

    private var keyboardSection: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Keyboard Navigation").font(MAStyle.Typography.headline)
            Text("Tab through the controls; focus outline appears on segmented rows and toggles/sliders.")
                .maText(.caption)
                .foregroundColor(MAStyle.ColorToken.muted)
            HStack(spacing: MAStyle.Spacing.sm) {
                Button("Focus 1") {}.maButton(.secondary).focused($keyboardFocus, equals: 1)
                Button("Focus 2") {}.maButton(.secondary).focused($keyboardFocus, equals: 2)
                Button("Focus 3") {}.maButton(.secondary).focused($keyboardFocus, equals: 3)
            }
            .maCardInteractive()
            MATableRow(index: 0, isSelected: false, isDisabled: false, isFocused: keyboardFocus == 4) {
                Text("Focusable row (Tab to it)")
            }
            .maStripedRowStyle(index: 0, isSelected: false, isDisabled: false, isFocused: keyboardFocus == 4)
            .focused($keyboardFocus, equals: 4)
        }
        .maCard()
    }

    private var animationsSection: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Animations").font(MAStyle.Typography.headline)
            HStack(spacing: MAStyle.Spacing.sm) {
                Text("Pulsing metric").maMetric().maPulse()
                Text("Sliding card")
                    .maCard()
                    .maSlideIn(from: .trailing, distance: 32, delay: 0.05)
                Text("Floating tag")
                    .maChip(style: .solid, color: MAStyle.ColorToken.info)
                    .maFloat()
                    .maFadeIn(delay: 0.1)
                Text("Shake")
                    .maBadge(.warning)
                    .maShake(animatableData: 1.0, travel: 4, shakesPerUnit: 4)
            }
            Text("Reduce Motion respected (toggle in Toggles section).")
                .maText(.caption)
                .foregroundColor(MAStyle.ColorToken.muted)
        }
        .maCard()
    }

    @ViewBuilder
    private var modalOverlays: some View {
        MAModal(isPresented: $showDialog, style: .dialog, title: "Dialog Title", actions: [
            MAModalAction("Close") {},
            MAModalAction("Confirm", action: {})
        ]) {
            Text("This is a dialog-style modal using MAStyle tokens.")
        }
        MAModal(isPresented: $showSheet, style: .sheet, title: "Sheet") {
            Text("Slides from bottom; tap backdrop to dismiss.")
        }
        MAModal(isPresented: $showToast, style: .toast, title: nil) {
            Text("Toast message with minimal chrome.")
        }
        MAModal(isPresented: $showPopup, style: .popup, title: "Popup") {
            Text("Centered popup with slight offset/scale.")
        }
    }
}

struct MAStyleShowcase_Previews: PreviewProvider {
    static var previews: some View {
        MAStyleShowcase()
            .frame(width: 800, height: 1200)
    }
}
