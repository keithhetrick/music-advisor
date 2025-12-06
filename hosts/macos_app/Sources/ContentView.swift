import SwiftUI

struct ContentView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Music Advisor macOS host")
                .font(.title.bold())
            Text("This SwiftUI shell is decoupled from JUCE. The Python engines stay external; we can add IPC/CLI hooks later.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Divider()
            VStack(alignment: .leading, spacing: 8) {
                Label("SwiftUI UI shell", systemImage: "rectangle.3.offgrid")
                Label("Audio/dsp remains in pipeline or future JUCE plug-ins", systemImage: "waveform")
                Label("Future: wire CLI/IPC to Python engine", systemImage: "externaldrive.connected.to.line.below")
            }
            .padding(10)
            .background(.quaternary.opacity(0.4))
            .cornerRadius(8)
            Spacer()
            HStack {
                Spacer()
                Text("macOS 12+, SwiftUI, SwiftPM")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(20)
        .frame(minWidth: 480, minHeight: 320)
    }
}

#Preview {
    ContentView()
}
