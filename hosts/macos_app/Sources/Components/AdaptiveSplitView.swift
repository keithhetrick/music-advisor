import SwiftUI
import MAStyle

struct AdaptiveSplitView<Left: View, Right: View>: View {
    @ViewBuilder var left: Left
    @ViewBuilder var right: Right
    var breakpoint: CGFloat = 1200

    var body: some View {
        GeometryReader { geo in
            if geo.size.width >= breakpoint {
                HStack(alignment: .top, spacing: MAStyle.Spacing.md) {
                    left
                        .frame(maxWidth: geo.size.width * 0.38, alignment: .leading)
                        .maGlass()
                    right
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .maGlass()
                }
            } else {
                VStack(alignment: .leading, spacing: MAStyle.Spacing.md) {
                    left.maGlass()
                    right.maGlass()
                }
            }
        }
        .padding(.vertical, MAStyle.Spacing.sm)
    }
}
