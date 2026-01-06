import SwiftUI
import MAStyle

struct CommandPalette: View {
    struct Entry: Identifiable {
        let id = UUID()
        let title: String
        let subtitle: String
        let action: () -> Void
    }

    @Binding var isPresented: Bool
    @Binding var query: String
    var entries: [Entry]

    private var filtered: [Entry] {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return entries }
        return entries.filter { $0.title.localizedCaseInsensitiveContains(trimmed) || $0.subtitle.localizedCaseInsensitiveContains(trimmed) }
    }

    var body: some View {
        ZStack {
            Color.black.opacity(0.35)
                .ignoresSafeArea()
                .onTapGesture { isPresented = false }

            VStack(spacing: MAStyle.Spacing.sm) {
                HStack {
                    Image(systemName: "command")
                    Text("K")
                    Text("Command Palette")
                }
                .font(MAStyle.Typography.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)

                TextField("Type a command…", text: $query)
                    .maInput()
                    .textFieldStyle(.plain)
                    .padding(.horizontal, MAStyle.Spacing.sm)
                    .padding(.vertical, MAStyle.Spacing.xs)
                    .background(MAStyle.ColorToken.panel.opacity(0.7))
                    .cornerRadius(MAStyle.Radius.sm)

                if filtered.isEmpty {
                    Text("No matches")
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                        .frame(maxWidth: .infinity, alignment: .leading)
                } else {
                    VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                        ForEach(filtered) { entry in
                            Button {
                                entry.action()
                                isPresented = false
                                query = ""
                            } label: {
                                VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                                    Text(entry.title).maText(.body)
                                    Text(entry.subtitle).maText(.caption).foregroundStyle(MAStyle.ColorToken.muted)
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.horizontal, MAStyle.Spacing.sm)
                                .padding(.vertical, MAStyle.Spacing.xs)
                                .background(MAStyle.ColorToken.panel.opacity(0.6))
                                .cornerRadius(MAStyle.Radius.sm)
                            }
                            .buttonStyle(.plain)
                            .maHoverLift()
                        }
                    }
                }
            }
            .padding(MAStyle.Spacing.md)
            .frame(maxWidth: 520)
            .background(MAStyle.ColorToken.background.opacity(0.85))
            .cornerRadius(MAStyle.Radius.lg)
            .overlay(
                RoundedRectangle(cornerRadius: MAStyle.Radius.lg)
                    .stroke(MAStyle.ColorToken.border.opacity(0.7), lineWidth: 1)
            )
        }
        .transition(.opacity)
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
                NSApp.keyWindow?.makeFirstResponder(nil)
            }
        }
    }
}
