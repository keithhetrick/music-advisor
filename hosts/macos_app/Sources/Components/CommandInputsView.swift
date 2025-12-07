import SwiftUI
import MAStyle

struct CommandInputsView: View {
    var profiles: [AppConfig.Profile]
    @Binding var selectedProfile: String
    var onApplyProfile: () -> Void
    var onReloadConfig: () -> Void
    @Binding var showAdvanced: Bool

    @Binding var commandText: String
    @Binding var workingDirectory: String
    @Binding var envText: String
    var onPickAudio: () -> Void
    var onBrowseDir: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            if !profiles.isEmpty {
                HStack(spacing: MAStyle.Spacing.sm) {
                    Text("Profile").maText(.headline)
                    Picker("Profile", selection: $selectedProfile) {
                        ForEach(profiles.map { $0.name }, id: \.self) { name in
                            Text(name).tag(name)
                        }
                    }
                    .labelsHidden()
                    .ifAvailable { $0.maPickerStyle() }
                    Button("Apply profile") {
                        onApplyProfile()
                    }
                    .maButton(.secondary)
                    .disabled(selectedProfile.isEmpty)
                    Button("Reload config") {
                        onReloadConfig()
                    }
                    .maButton(.ghost)
                    Spacer()
                }
            }

            HStack {
                Text("Inputs").maText(.headline)
                Spacer()
                Button(showAdvanced ? "Hide advanced" : "Show advanced") {
                    showAdvanced.toggle()
                }
                .maButton(.ghost)
            }

            if showAdvanced {
                Text("Command").maText(.headline)
                HStack(spacing: MAStyle.Spacing.sm) {
                    TextField("/usr/bin/python3 tools/cli/ma_audio_features.py --audio /path/to/audio.wav --out /tmp/out.json", text: $commandText)
                        .maInput()
                    Button("Pick audio…") {
                        onPickAudio()
                    }
                    .maButton(.ghost)
                }

                Text("Working directory (optional)").maText(.headline)
                HStack(spacing: MAStyle.Spacing.sm) {
                    TextField("e.g. /Users/you/music-advisor", text: $workingDirectory)
                        .maInput()
                    Button("Browse…") {
                        onBrowseDir()
                    }
                    .maButton(.ghost)
                }

                Text("Extra env (KEY=VALUE per line)").maText(.headline)
                TextEditor(text: $envText)
                    .maTextArea()
                    .frame(minHeight: 80)
            }
        }
    }
}
