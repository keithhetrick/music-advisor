// Kept for compatibility; currently unused after adding explicit availability checks.
import SwiftUI

extension View {
    @ViewBuilder
    func ifAvailable<T: View>(_ transform: (Self) -> T) -> some View {
        if #available(macOS 13.0, *) {
            transform(self)
        } else {
            self
        }
    }
}
