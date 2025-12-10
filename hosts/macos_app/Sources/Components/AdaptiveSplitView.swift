import SwiftUI
import MAStyle

struct AdaptiveSplitView<Left: View, Right: View>: View {
    @ViewBuilder var left: Left
    @ViewBuilder var right: Right
    var breakpoint: CGFloat = 1200
    @State private var containerWidth: CGFloat = 0

    var body: some View {
        let isWide = containerWidth >= breakpoint && containerWidth > 0

        Group {
            if isWide {
                HStack(alignment: .top, spacing: MAStyle.Spacing.md) {
                    left
                        .frame(maxWidth: containerWidth * 0.38, alignment: .leading)
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
        // Measure width without constraining height so content can drive scrollable height.
        .background(
            GeometryReader { proxy in
                Color.clear.preference(key: AdaptiveSplitWidthKey.self, value: proxy.size.width)
            }
        )
        .onPreferenceChange(AdaptiveSplitWidthKey.self) { width in
            containerWidth = width
        }
    }
}

private struct AdaptiveSplitWidthKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}
