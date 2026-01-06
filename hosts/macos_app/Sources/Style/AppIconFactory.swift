import AppKit
import SwiftUI

enum AppIconFactory {
    static func applyIfNeeded() {
        guard NSApplication.shared.applicationIconImage?.size.width ?? 0 < 128 else { return }
        NSApplication.shared.applicationIconImage = generate()
    }

    private static func generate() -> NSImage {
        let size: CGFloat = 512
        let img = NSImage(size: NSSize(width: size, height: size))
        img.lockFocus()
        let rect = NSRect(x: 0, y: 0, width: size, height: size)

        // Background gradient.
        let bg = NSGradient(colors: [
            NSColor(calibratedRed: 0.09, green: 0.12, blue: 0.22, alpha: 1.0),
            NSColor(calibratedRed: 0.05, green: 0.08, blue: 0.16, alpha: 1.0)
        ])!
        let rounded = NSBezierPath(roundedRect: rect, xRadius: size * 0.12, yRadius: size * 0.12)
        bg.draw(in: rounded, angle: 90)

        // Accent ring.
        let ring = NSBezierPath(roundedRect: rect.insetBy(dx: size * 0.05, dy: size * 0.05),
                                xRadius: size * 0.1,
                                yRadius: size * 0.1)
        NSColor(calibratedRed: 0.12, green: 0.62, blue: 0.98, alpha: 0.35).setStroke()
        ring.lineWidth = size * 0.025
        ring.stroke()

        // Central glass pill.
        let pillRect = NSRect(x: size * 0.2, y: size * 0.42, width: size * 0.6, height: size * 0.16)
        let pillPath = NSBezierPath(roundedRect: pillRect, xRadius: pillRect.height / 2, yRadius: pillRect.height / 2)
        NSColor.white.withAlphaComponent(0.08).setFill()
        pillPath.fill()
        NSColor.white.withAlphaComponent(0.18).setStroke()
        pillPath.lineWidth = size * 0.008
        pillPath.stroke()

        // Waveform line.
        let wave = NSBezierPath()
        let start = NSPoint(x: pillRect.minX + pillRect.width * 0.06, y: pillRect.midY)
        wave.move(to: start)
        let cp1 = NSPoint(x: pillRect.minX + pillRect.width * 0.2, y: pillRect.midY + pillRect.height * 0.6)
        let cp2 = NSPoint(x: pillRect.minX + pillRect.width * 0.3, y: pillRect.midY - pillRect.height * 0.6)
        let mid = NSPoint(x: pillRect.minX + pillRect.width * 0.45, y: pillRect.midY)
        wave.curve(to: mid, controlPoint1: cp1, controlPoint2: cp2)
        let cp3 = NSPoint(x: pillRect.minX + pillRect.width * 0.6, y: pillRect.midY + pillRect.height * 0.6)
        let cp4 = NSPoint(x: pillRect.minX + pillRect.width * 0.7, y: pillRect.midY - pillRect.height * 0.6)
        let end = NSPoint(x: pillRect.maxX - pillRect.width * 0.06, y: pillRect.midY)
        wave.curve(to: end, controlPoint1: cp3, controlPoint2: cp4)
        wave.lineCapStyle = .round
        wave.lineWidth = size * 0.02
        NSColor(calibratedRed: 0.2, green: 0.8, blue: 1.0, alpha: 0.9).setStroke()
        wave.stroke()

        // Glow overlay.
        let glow = NSBezierPath(roundedRect: rect, xRadius: size * 0.12, yRadius: size * 0.12)
        NSColor.white.withAlphaComponent(0.05).setStroke()
        glow.lineWidth = size * 0.01
        glow.stroke()

        img.unlockFocus()
        return img
    }
}
