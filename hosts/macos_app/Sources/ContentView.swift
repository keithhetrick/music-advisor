import SwiftUI
import AppKit

struct ContentView: View {
    @StateObject private var viewModel = CommandViewModel()
    @State private var selectedPane: ResultPane = .json

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
            header
            Divider()
            commandInputs
            runButtons
            Divider()
            results
            Spacer()
        }
        .padding(MAStyle.Spacing.lg)
        .frame(minWidth: 620, minHeight: 420)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text("Music Advisor macOS host")
                .font(MAStyle.Typography.title.bold())
            Text("SwiftUI shell; external engines stay decoupled. Configure any local CLI (Python pipeline, mock, etc.) below.")
                .font(.subheadline)
                .foregroundStyle(MAStyle.ColorToken.muted)
        }
    }

    private var commandInputs: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            if !viewModel.profiles.isEmpty {
                HStack(spacing: MAStyle.Spacing.sm) {
                    Text("Profile").font(MAStyle.Typography.headline)
                    Picker("Profile", selection: $viewModel.selectedProfile) {
                        ForEach(viewModel.profiles.map { $0.name }, id: \.self) { name in
                            Text(name).tag(name)
                        }
                    }
                    .labelsHidden()
                    Button("Apply profile") {
                        viewModel.applySelectedProfile()
                    }
                    .disabled(viewModel.selectedProfile.isEmpty)
                    Spacer()
                }
            }

            Text("Command").font(MAStyle.Typography.headline)
            HStack(spacing: 8) {
                TextField("/usr/bin/python3 tools/cli/ma_audio_features.py --audio /path/to/audio.wav --out /tmp/out.json", text: $viewModel.commandText)
                    .textFieldStyle(.roundedBorder)
                Button("Pick audio…") {
                    if let url = pickFile() {
                        viewModel.insertAudioPath(url.path)
                    }
                }
            }

            Text("Working directory (optional)").font(MAStyle.Typography.headline)
            HStack(spacing: 8) {
                TextField("e.g. /Users/you/music-advisor", text: $viewModel.workingDirectory)
                    .textFieldStyle(.roundedBorder)
                Button("Browse…") {
                    if let url = pickDirectory() {
                        viewModel.setWorkingDirectory(url.path)
                    }
                }
            }

            Text("Extra env (KEY=VALUE per line)").font(MAStyle.Typography.headline)
            TextEditor(text: $viewModel.envText)
                .font(.system(.body, design: .monospaced))
                .frame(minHeight: 80)
                .overlay(RoundedRectangle(cornerRadius: MAStyle.Radius.sm).stroke(MAStyle.ColorToken.border))
        }
    }

    private var runButtons: some View {
        HStack {
            Button(action: { viewModel.run() }) {
                if viewModel.isRunning {
                    ProgressView().progressViewStyle(.circular)
                } else {
                    Text("Run CLI")
                }
            }
            .disabled(viewModel.isRunning)

            Button("Run defaults") {
                viewModel.loadDefaults()
                viewModel.run()
            }
            .disabled(viewModel.isRunning)

            Button("Run smoke") {
                viewModel.runSmoke()
            }
            .disabled(viewModel.isRunning)

            if !viewModel.status.isEmpty {
                Text(viewModel.status)
                    .font(MAStyle.Typography.body)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }

            if let last = viewModel.lastRunTime {
                let durationText = viewModel.lastDuration.map { String(format: " (%.2fs)", $0) } ?? ""
                Text("Last run: \(last.formatted(date: .omitted, time: .standard))\(durationText)")
                    .font(MAStyle.Typography.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }
            Spacer()
        }
    }

    private var results: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            Text("Result").font(MAStyle.Typography.headline)
            Picker("", selection: $selectedPane) {
                Text("JSON").tag(ResultPane.json)
                Text("stdout").tag(ResultPane.stdout)
                Text("stderr").tag(ResultPane.stderr)
            }
            .pickerStyle(.segmented)
            .onChange(of: viewModel.parsedJSON, perform: { _ in
                if selectedPane == .json && viewModel.parsedJSON.isEmpty {
                    selectedPane = .stdout
                }
            })

            if !viewModel.summaryMetrics.isEmpty || viewModel.sidecarPath != nil {
                HStack(spacing: 12) {
                    ForEach(viewModel.summaryMetrics) { metric in
                        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                            Text(metric.label).font(MAStyle.Typography.caption).foregroundStyle(MAStyle.ColorToken.muted)
                            Text(metric.value).font(MAStyle.Typography.body)
                        }
                        .maMetric()
                    }
                    if let path = viewModel.sidecarPath {
                        Button("Reveal sidecar") {
                            revealSidecar(path: path)
                        }
                        Button("Copy path") {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(path, forType: .string)
                        }
                        Button("Preview sidecar") {
                            viewModel.loadSidecarPreview()
                        }
                    }
                    Spacer()
                }
            }

            HStack(spacing: 12) {
                Button("Copy JSON") {
                    copyJSON()
                }
                .disabled(viewModel.parsedJSON.isEmpty)
                if let path = viewModel.sidecarPath {
                    Button("Copy sidecar path") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(path, forType: .string)
                    }
                }
                Spacer()
            }

            resultBlock(title: selectedPane.title,
                        text: paneText(selectedPane),
                        color: selectedPane.color)

            if !viewModel.sidecarPreview.isEmpty {
                resultBlock(title: "sidecar preview",
                            text: viewModel.sidecarPreview,
                            color: .purple)
            }

            Text("Exit code: \(viewModel.exitCode)")
                .font(MAStyle.Typography.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
        }
        .maCard(padding: MAStyle.Spacing.md)
    }

    private func resultBlock(title: String, text: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            Text(title).font(MAStyle.Typography.headline)
            ScrollView {
                Text(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "(empty)" : text.trimmingCharacters(in: .whitespacesAndNewlines))
                    .font(MAStyle.Typography.bodyMono)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(MAStyle.Spacing.sm)
                    .background(color.opacity(0.05))
                    .cornerRadius(MAStyle.Radius.sm)
            }
            .frame(minHeight: 80)
        }
    }

    private func prettyJSON(_ dict: [String: AnyHashable]) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: dict, options: [.prettyPrinted]),
              let str = String(data: data, encoding: .utf8) else {
            return dict.description
        }
        return str
    }

    private func paneText(_ pane: ResultPane) -> String {
        switch pane {
        case .json:
            return viewModel.parsedJSON.isEmpty ? "(no JSON parsed)" : prettyJSON(viewModel.parsedJSON)
        case .stdout:
            return viewModel.stdout
        case .stderr:
            return viewModel.stderr
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}

enum ResultPane: Hashable {
    case json, stdout, stderr

    var title: String {
        switch self {
        case .json: return "parsed JSON"
        case .stdout: return "stdout"
        case .stderr: return "stderr"
        }
    }

    var color: Color {
        switch self {
        case .json: return .blue
        case .stdout: return .green
        case .stderr: return .red
        }
    }
}

// MARK: - Pickers
extension ContentView {
    private func pickFile() -> URL? {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        let response = panel.runModal()
        return response == .OK ? panel.urls.first : nil
    }

    private func pickDirectory() -> URL? {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        let response = panel.runModal()
        return response == .OK ? panel.urls.first : nil
    }

    private func revealSidecar(path: String) {
        let url = URL(fileURLWithPath: path)
        NSWorkspace.shared.activateFileViewerSelecting([url])
    }

    private func copyJSON() {
        let jsonString = viewModel.parsedJSON.isEmpty ? "" : prettyJSON(viewModel.parsedJSON)
        guard !jsonString.isEmpty else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(jsonString, forType: .string)
    }
}
