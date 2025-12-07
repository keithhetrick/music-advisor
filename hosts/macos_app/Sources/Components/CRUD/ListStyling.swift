import SwiftUI
import MAStyle

struct ListRowStyling: ViewModifier {
    func body(content: Content) -> some View {
        if #available(macOS 13.0, *) {
            content
                .listRowSeparator(.hidden)
                .maListRowStyle()
        } else {
            content
        }
    }
}

struct ListBackgroundStyling: ViewModifier {
    func body(content: Content) -> some View {
        if #available(macOS 13.0, *) {
            content.scrollContentBackground(.hidden)
        } else {
            content
        }
    }
}
