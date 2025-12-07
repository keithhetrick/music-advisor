import SwiftUI

public struct MAToastMessage: Identifiable, Equatable {
    public let id = UUID()
    public let title: String
    public let tone: MAAlertTone
    public let duration: TimeInterval
    public init(title: String, tone: MAAlertTone = .info, duration: TimeInterval = 2.4) {
        self.title = title
        self.tone = tone
        self.duration = duration
    }
}

public struct MAToastHost: View {
    @Binding var queue: [MAToastMessage]
    @State private var current: MAToastMessage?
    @State private var taskID: UUID?

    public init(queue: Binding<[MAToastMessage]>) {
        self._queue = queue
    }

    public var body: some View {
        VStack {
            Spacer()
            if let current {
                MAToastBanner(title: current.title, tone: current.tone)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                    .onAppear { scheduleDismiss(message: current) }
            }
        }
        .padding(.bottom, MAStyle.Spacing.lg)
        .padding(.horizontal, MAStyle.Spacing.lg)
        .animation(.easeOut(duration: 0.2), value: current)
        .onChange(of: queue) { _ in
            dequeueIfNeeded()
        }
        .onAppear {
            dequeueIfNeeded()
        }
    }

    private func dequeueIfNeeded() {
        guard current == nil, !queue.isEmpty else { return }
        current = queue.removeFirst()
    }

    private func scheduleDismiss(message: MAToastMessage) {
        let id = UUID()
        taskID = id
        DispatchQueue.main.asyncAfter(deadline: .now() + message.duration) {
            if taskID == id {
                current = nil
                dequeueIfNeeded()
            }
        }
    }
}
