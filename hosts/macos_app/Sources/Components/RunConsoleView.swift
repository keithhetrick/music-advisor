import SwiftUI
import MAStyle

struct RunConsoleView: View {
    var stdout: String
    var stderr: String
    @State private var follow: Bool = true
    @State private var selected: ConsoleTab = .stdout
    @State private var filterText: String = ""
    @State private var filteredLinesCount: Int = 0

    enum ConsoleTab: String, CaseIterable, Identifiable {
        case stdout
        case stderr

        var id: String { rawValue }
        var title: String { rawValue.uppercased() }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            HStack {
                Text("Log")
                    .maText(.headline)
                Spacer()
                Toggle("Follow", isOn: $follow)
                    .maToggleStyle()
                    .labelsHidden()
                    .accessibilityLabel("Follow log")
            }
            Picker("Log", selection: $selected) {
                ForEach(ConsoleTab.allCases) { tab in
                    Text(tab.title).tag(tab)
                }
            }
            .pickerStyle(.segmented)

            HStack(spacing: MAStyle.Spacing.xs) {
                TextField("Filter log…", text: $filterText)
                    .maInput()
                Button("Clear") { filterText = "" }
                    .maButton(.ghost)
                Text(summaryText)
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
            }

            ScrollViewReader { proxy in
                ScrollView {
                    Text(selected == .stdout ? filteredStdout : filteredStderr)
                        .font(MAStyle.Typography.bodyMono)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(MAStyle.Spacing.sm)
                        .maCardInteractive()
                        .id("log-bottom")
                }
                .onChange(of: filteredStdout) { _ in
                    if follow && selected == .stdout {
                        withAnimation { proxy.scrollTo("log-bottom", anchor: .bottom) }
                    }
                }
                .onChange(of: filteredStderr) { _ in
                    if follow && selected == .stderr {
                        withAnimation { proxy.scrollTo("log-bottom", anchor: .bottom) }
                    }
                }
            }
            HStack {
                Spacer()
                Button("Copy filtered") {
                    let text = selected == .stdout ? filteredStdout : filteredStderr
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(text, forType: .string)
                }
                .maButton(.ghost)
            }
        }
        .maCardInteractive()
    }

    private var stdoutOutput: String {
        stdout.isEmpty ? "(stdout empty)" : stdout
    }

    private var stderrOutput: String {
        stderr.isEmpty ? "(stderr empty)" : stderr
    }

    private var filteredStdout: String {
        guard !filterText.isEmpty else {
            filteredLinesCount = stdoutOutput.split(separator: "\n").count
            return stdoutOutput
        }
        let lines = stdoutOutput.split(separator: "\n")
        let filtered = lines.filter { $0.localizedCaseInsensitiveContains(filterText) }
        filteredLinesCount = filtered.count
        return filtered.joined(separator: "\n")
    }

    private var filteredStderr: String {
        guard !filterText.isEmpty else {
            filteredLinesCount = stderrOutput.split(separator: "\n").count
            return stderrOutput
        }
        let lines = stderrOutput.split(separator: "\n")
        let filtered = lines.filter { $0.localizedCaseInsensitiveContains(filterText) }
        filteredLinesCount = filtered.count
        return filtered.joined(separator: "\n")
    }

    private var summaryText: String {
        if filterText.isEmpty {
            return "Lines: \(filteredLinesCount)"
        } else {
            return "Filtered: \(filteredLinesCount)"
        }
    }
}
