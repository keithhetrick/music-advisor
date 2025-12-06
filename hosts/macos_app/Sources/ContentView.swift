import SwiftUI
import AppKit

struct ContentView: View {
    @StateObject private var viewModel = CommandViewModel()
    @State private var selectedPane: ResultPane = .json

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            header
            Divider()
            commandInputs
            runButtons
            Divider()
            results
            Spacer()
        }
        .padding(20)
        .frame(minWidth: 580, minHeight: 400)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Music Advisor macOS host")
                .font(.title.bold())
            Text("SwiftUI shell; external engines stay decoupled. Configure any local CLI (Python pipeline, mock, etc.) below.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }

    private var commandInputs: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Command").font(.headline)
            HStack(spacing: 8) {
                TextField("/usr/bin/python3 tools/cli/ma_audio_features.py --audio /path/to/audio.wav --out /tmp/out.json", text: $viewModel.commandText)
                    .textFieldStyle(.roundedBorder)
                Button("Pick audio…") {
                    if let url = pickFile() {
                        viewModel.insertAudioPath(url.path)
                    }
                }
            }

            Text("Working directory (optional)").font(.headline)
            HStack(spacing: 8) {
                TextField("e.g. /Users/you/music-advisor", text: $viewModel.workingDirectory)
                    .textFieldStyle(.roundedBorder)
                Button("Browse…") {
                    if let url = pickDirectory() {
                        viewModel.setWorkingDirectory(url.path)
                    }
                }
            }

            Text("Extra env (KEY=VALUE per line)").font(.headline)
            TextEditor(text: $viewModel.envText)
                .font(.system(.body, design: .monospaced))
                .frame(minHeight: 80)
                .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.secondary.opacity(0.2)))
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

            if !viewModel.status.isEmpty {
                Text(viewModel.status)
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
    }

    private var results: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Result").font(.headline)
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
                        VStack(alignment: .leading, spacing: 2) {
                            Text(metric.label).font(.caption).foregroundStyle(.secondary)
                            Text(metric.value).font(.body)
                        }
                        .padding(8)
                        .background(Color.secondary.opacity(0.08))
                        .cornerRadius(6)
                    }
                    if let path = viewModel.sidecarPath {
                        Button("Reveal sidecar") {
                            revealSidecar(path: path)
                        }
                    }
                    Spacer()
                }
            }

            resultBlock(title: selectedPane.title,
                        text: paneText(selectedPane),
                        color: selectedPane.color)

            Text("Exit code: \(viewModel.exitCode)")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private func resultBlock(title: String, text: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.subheadline.bold())
            ScrollView {
                Text(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "(empty)" : text.trimmingCharacters(in: .whitespacesAndNewlines))
                    .font(.system(.body, design: .monospaced))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(8)
                    .background(color.opacity(0.05))
                    .cornerRadius(6)
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
}
