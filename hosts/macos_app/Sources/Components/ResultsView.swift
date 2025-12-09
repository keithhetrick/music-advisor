import SwiftUI
import MAStyle

struct ResultsView: View {
    @Binding var selectedPane: ResultPane
    var parsedJSON: [String: AnyHashable]
    var stdout: String
    var stderr: String
    var exitCode: Int32
    var summaryMetrics: [Metric]
    var sidecarPath: String?
    var sidecarPreview: String
    var onRevealSidecar: () -> Void
    var onCopySidecarPath: () -> Void
    var onPreviewSidecar: () -> Void
    var onCopyJSON: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            HStack(spacing: MAStyle.Spacing.sm) {
                Text("Result").maText(.headline)
                Picker("", selection: $selectedPane) {
                    Text("JSON").tag(ResultPane.json)
                    Text("stdout").tag(ResultPane.stdout)
                    Text("stderr").tag(ResultPane.stderr)
                }
                .pickerStyle(.segmented)
                .onChange(of: parsedJSON, perform: { _ in
                    if selectedPane == .json && parsedJSON.isEmpty {
                        selectedPane = .stdout
                    }
                })
                .accessibilityLabel("Result pane")
                Spacer()
                Button {
                    let text = paneText(selectedPane)
                    guard !text.isEmpty else { return }
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(text, forType: .string)
                } label: {
                    Label("Copy pane", systemImage: "doc.on.doc")
                }
                .maButton(.ghost)
                .disabled(paneText(selectedPane).isEmpty)
                .accessibilityLabel("Copy current result pane")
            }

            if !summaryMetrics.isEmpty || sidecarPath != nil {
                HStack(spacing: MAStyle.Spacing.sm) {
                    ForEach(summaryMetrics) { metric in
                        MetricTile(label: metric.label, value: metric.value)
                    }
                    if sidecarPath != nil {
                        Button("Reveal sidecar", action: onRevealSidecar).maButton(.ghost).accessibilityLabel("Reveal sidecar")
                        Button("Copy path", action: onCopySidecarPath).maButton(.ghost).accessibilityLabel("Copy sidecar path")
                        Button("Preview sidecar", action: onPreviewSidecar).maButton(.ghost).accessibilityLabel("Preview sidecar")
                    }
                    Spacer()
                }
            }

            HStack(spacing: MAStyle.Spacing.sm) {
                Button("Copy JSON", action: onCopyJSON)
                    .maButton(.ghost)
                    .disabled(parsedJSON.isEmpty)
                    .accessibilityLabel("Copy JSON result")
                if sidecarPath != nil {
                    Button("Copy sidecar path", action: onCopySidecarPath)
                        .maButton(.ghost)
                        .accessibilityLabel("Copy sidecar path")
                }
                Spacer()
            }

            resultBlock(title: selectedPane.title,
                        text: paneText(selectedPane),
                        color: selectedPane.color)

            if !sidecarPreview.isEmpty {
                resultBlock(title: "sidecar preview",
                            text: sidecarPreview,
                            color: .purple)
            }

            Text("Exit code: \(exitCode)")
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
        }
        .maCard(padding: MAStyle.Spacing.md)
    }

    private func resultBlock(title: String, text: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text(title).maText(.headline)
            ScrollView {
                Text(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "(empty)" : text.trimmingCharacters(in: .whitespacesAndNewlines))
                    .maCardInteractive()
                    .font(MAStyle.Typography.bodyMono)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(MAStyle.Spacing.sm)
                    .background(color.opacity(0.05))
                    .cornerRadius(MAStyle.Radius.sm)
            }
            .frame(minHeight: 80)
        }
    }

    private func paneText(_ pane: ResultPane) -> String {
        switch pane {
        case .json:
            return prettyJSON(parsedJSON)
        case .stdout:
            return stdout
        case .stderr:
            return stderr
        }
    }

    private func prettyJSON(_ dict: [String: AnyHashable]) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: dict, options: [.prettyPrinted]),
              let str = String(data: data, encoding: .utf8) else {
            return dict.isEmpty ? "(no JSON parsed)" : dict.description
        }
        return str
    }
}
