import SwiftUI
import MAStyle

struct CollapsibleSection<Header: View, Content: View>: View {
    @State private var isExpanded: Bool = true
    var header: () -> Header
    var content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: MAStyle.Spacing.xs) {
            HStack {
                Button(isExpanded ? "Hide" : "Show") {
                    isExpanded.toggle()
                }
                .maButton(.ghost)
                header()
                Spacer()
            }
            if isExpanded {
                content()
            }
        }
    }
}
