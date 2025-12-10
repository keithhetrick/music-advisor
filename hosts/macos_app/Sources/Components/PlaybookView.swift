import SwiftUI
import MAStyle

struct PlaybookView: View {
    var references: [String]
    var onAnalyze: (PlaybookCard, String?) -> PlaybookResult?
    var onAskChat: (PlaybookCard, String?, String) -> Void

    @State private var selections: [UUID: String] = [:]
    @State private var results: [UUID: PlaybookResult] = [:]

    private let cards: [PlaybookCard] = [
        PlaybookCard(title: "Radio-ready loudness",
                     description: "Target streaming-safe LUFS with clean crest and balanced peak.",
                     hint: "Use recent run metrics as the source.",
                     requiresReference: false),
        PlaybookCard(title: "Match reference track",
                     description: "Align tempo/key/loudness to a chosen reference from history.",
                     hint: "Pick a reference from your saved runs.",
                     requiresReference: true),
        PlaybookCard(title: "Streaming-safe master",
                     description: "Ensure headroom and dynamics are within service norms.",
                     hint: "Good for batch compliance checks.",
                     requiresReference: false)
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
            Text("Guided analyses with structured outputs. Use chat for follow-ups.")
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)

            LazyVStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
                ForEach(cards) { card in
                    cardView(card)
                }
            }
        }
        .maCard()
    }

    @ViewBuilder
    private func cardView(_ card: PlaybookCard) -> some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.sm) {
            HStack {
                VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
                    Text(card.title)
                        .maText(.body)
                    Text(card.description)
                        .maText(.caption)
                        .foregroundStyle(MAStyle.ColorToken.muted)
                }
                Spacer()
            }
            HStack(spacing: MAStyle.Spacing.xs) {
                if card.requiresReference {
                    Menu {
                        ForEach(references, id: \.self) { ref in
                            Button(ref) { selections[card.id] = ref }
                        }
                    } label: {
                        Text(selections[card.id] ?? "Select reference")
                            .maText(.caption)
                    }
                }
                Button("Analyze") {
                    guard !card.requiresReference || selections[card.id] != nil else { return }
                    let result = onAnalyze(card, selections[card.id])
                    if let result { results[card.id] = result }
                }
                .maButton(.primary)
                .disabled(card.requiresReference && selections[card.id] == nil)
                Button("Ask Chat") {
                    guard !card.requiresReference || selections[card.id] != nil else { return }
                    let context = results[card.id]?.contextSummary ?? "Use latest run context."
                    onAskChat(card, selections[card.id], context)
                }
                .maButton(.ghost)
                .disabled(card.requiresReference && selections[card.id] == nil)
            }
            Text(card.hint)
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
            Divider()
            if card.requiresReference && selections[card.id] == nil {
                Text("Select a reference to run this playbook.")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.warning)
            }
            if let result = results[card.id] {
                PlaybookResultView(result: result)
            }
        }
        .maCard()
    }
}

struct PlaybookCard: Identifiable, Hashable {
    let id = UUID()
    let title: String
    let description: String
    let hint: String
    let requiresReference: Bool
}

struct PlaybookResult: Hashable {
    let issues: [String]
    let fixes: [String]
    let impact: [String]
    let contextSummary: String
}

private struct PlaybookResultView: View {
    let result: PlaybookResult

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            if !result.issues.isEmpty {
                Text("Issues")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
                ForEach(result.issues, id: \.self) { Text("• \($0)").maText(.caption) }
            }
            if !result.fixes.isEmpty {
                Text("Fixes")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
                ForEach(result.fixes, id: \.self) { Text("• \($0)").maText(.caption) }
            }
            if !result.impact.isEmpty {
                Text("Impact")
                    .maText(.caption)
                    .foregroundStyle(MAStyle.ColorToken.muted)
                ForEach(result.impact, id: \.self) { Text("• \($0)").maText(.caption) }
            }
            Text(result.contextSummary)
                .maText(.caption)
                .foregroundStyle(MAStyle.ColorToken.muted)
        }
        .padding(MAStyle.Spacing.sm)
        .maCardInteractive()
    }
}
