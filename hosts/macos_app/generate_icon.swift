import AppKit
import Foundation

func generate(size: CGFloat) -> NSImage {
    let img = NSImage(size: NSSize(width: size, height: size))
    img.lockFocus()
    let rect = NSRect(x: 0, y: 0, width: size, height: size)
    let rounded = NSBezierPath(roundedRect: rect, xRadius: size * 0.12, yRadius: size * 0.12)
    let bg = NSGradient(colors: [
        NSColor(calibratedRed: 23/255, green: 31/255, blue: 56/255, alpha: 1),
        NSColor(calibratedRed: 13/255, green: 20/255, blue: 40/255, alpha: 1)
    ])!
    bg.draw(in: rounded, angle: 90)
    // Anchor point for ripples
    let anchorY = size * 0.14
    let anchor = NSPoint(x: size/2, y: anchorY)
    let rippleRadii: [CGFloat] = [size * 0.17, size * 0.28, size * 0.38]
    for (i, r) in rippleRadii.enumerated() {
        let center = NSPoint(x: anchor.x, y: anchor.y + r)
        let arc = NSBezierPath()
        arc.appendArc(withCenter: center, radius: r, startAngle: 215, endAngle: -35, clockwise: true)
        arc.lineCapStyle = .round
        let strokeWidth = max(0.9, size * 0.0155)
        arc.lineWidth = strokeWidth
        let alpha = 0.88 - CGFloat(i) * 0.08
        let light = NSColor(calibratedWhite: 0.97, alpha: alpha)
        let mid = NSColor(calibratedWhite: 0.93, alpha: alpha)
        let dark = NSColor(calibratedWhite: 0.80, alpha: alpha * 0.45)

        // Subtle shadow stroke (adds depth)
        let shadowPath = arc.copy() as! NSBezierPath
        shadowPath.lineWidth = strokeWidth + max(0.15, size * 0.0015)
        NSGraphicsContext.saveGraphicsState()
        NSColor.clear.setFill()
        dark.setStroke()
        let shadow = NSShadow()
        shadow.shadowBlurRadius = max(0.4, size * 0.003)
        shadow.shadowOffset = NSSize(width: 0, height: -size * 0.003)
        shadow.shadowColor = dark.withAlphaComponent(alpha * 0.35)
        shadow.set()
        shadowPath.stroke()
        NSGraphicsContext.restoreGraphicsState()

        // Main stroke
        mid.setStroke()
        arc.stroke()

        // Top highlight
        let highlight = arc.copy() as! NSBezierPath
        highlight.lineWidth = strokeWidth * 0.55
        NSGraphicsContext.saveGraphicsState()
        light.setStroke()
        let hShadow = NSShadow()
        hShadow.shadowBlurRadius = max(0.3, size * 0.0025)
        hShadow.shadowOffset = NSSize(width: 0, height: size * 0.0015)
        hShadow.shadowColor = light.withAlphaComponent(alpha * 0.30)
        hShadow.set()
        highlight.stroke()
        NSGraphicsContext.restoreGraphicsState()

        // Specular gloss toward top-left for a liquid-glass cue
        let specular = arc.copy() as! NSBezierPath
        specular.lineWidth = strokeWidth * 0.35
        NSGraphicsContext.saveGraphicsState()
        let specColor = NSColor.white.withAlphaComponent(alpha * 0.22)
        specColor.setStroke()
        let specShadow = NSShadow()
        specShadow.shadowBlurRadius = max(0.25, size * 0.002)
        specShadow.shadowOffset = NSSize(width: size * 0.0015, height: size * 0.002)
        specShadow.shadowColor = NSColor.white.withAlphaComponent(alpha * 0.18)
        specShadow.set()
        specular.stroke()
        NSGraphicsContext.restoreGraphicsState()
    }
    // Base shelf tying the ripples together
    let shelfHeight = max(1, size * 0.006)
    let shelfWidth = size * 0.34
    let shelfRect = NSRect(x: anchor.x - shelfWidth/2, y: anchor.y - shelfHeight/2, width: shelfWidth, height: shelfHeight)
    let shelf = NSBezierPath(roundedRect: shelfRect, xRadius: shelfHeight/2, yRadius: shelfHeight/2)
    let shelfFill = NSColor(calibratedWhite: 0.93, alpha: 0.62)
    shelfFill.setFill()
    shelf.fill()
    // Shelf top highlight and bottom shade
    let shelfHighlight = NSBezierPath(roundedRect: shelfRect.insetBy(dx: size * 0.002, dy: size * 0.001), xRadius: shelfHeight/2, yRadius: shelfHeight/2)
    NSGraphicsContext.saveGraphicsState()
    NSColor(calibratedWhite: 0.98, alpha: 0.26).setStroke()
    shelfHighlight.lineWidth = max(0.35, size * 0.001)
    shelfHighlight.stroke()
    NSGraphicsContext.restoreGraphicsState()
    let shelfShadow = NSBezierPath(roundedRect: shelfRect, xRadius: shelfHeight/2, yRadius: shelfHeight/2)
    NSGraphicsContext.saveGraphicsState()
    NSColor(calibratedWhite: 0.65, alpha: 0.22).setStroke()
    shelfShadow.lineWidth = max(0.55, size * 0.0018)
    let sShadow = NSShadow()
    sShadow.shadowBlurRadius = max(0.35, size * 0.0025)
    sShadow.shadowOffset = NSSize(width: 0, height: -size * 0.0018)
    sShadow.shadowColor = NSColor.black.withAlphaComponent(0.18)
    sShadow.set()
    shelfShadow.stroke()
    NSGraphicsContext.restoreGraphicsState()
    // Lift shadow anchored at base circle
    let liftWidth = size * 0.9
    let liftHeight = size * 0.26
    let liftRect = NSRect(x: anchor.x - liftWidth/2, y: anchor.y - liftHeight*0.35, width: liftWidth, height: liftHeight)
    let liftShadow = NSBezierPath(ovalIn: liftRect)
    NSGraphicsContext.saveGraphicsState()
    NSColor.black.withAlphaComponent(0.20).setFill()
    let lift = NSShadow()
    lift.shadowBlurRadius = max(10, size * 0.06)
    lift.shadowOffset = NSSize(width: 0, height: -size * 0.014)
    lift.shadowColor = NSColor.black.withAlphaComponent(0.26)
    lift.set()
    liftShadow.fill()
    NSGraphicsContext.restoreGraphicsState()
    // Core glow at anchor
    let dotSize = size * 0.12
    let dotRect = NSRect(x: anchor.x - dotSize/2, y: anchor.y - dotSize/2, width: dotSize, height: dotSize)
    let dot = NSBezierPath(ovalIn: dotRect)
    let core = NSGradient(colors: [
        NSColor(calibratedWhite: 0.985, alpha: 1.0),
        NSColor(calibratedWhite: 0.88, alpha: 0.78)
    ])!
    core.draw(in: dot, relativeCenterPosition: NSPoint(x: 0, y: 0))
    dot.lineWidth = max(1, size * 0.009)
    NSColor.white.withAlphaComponent(0.24).setStroke()
    dot.stroke()
    let glow = NSBezierPath(roundedRect: rect, xRadius: size * 0.18, yRadius: size * 0.18)
    NSColor.white.withAlphaComponent(0.02).setStroke()
    glow.lineWidth = max(1, size * 0.0065)
    glow.stroke()
    img.unlockFocus()
    return img
}

let sizes: [CGFloat] = [16,32,64,128,256,512,1024]
let outDir = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    .appendingPathComponent("AppIcon.appiconset", isDirectory: true)
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
for size in sizes {
    let img = NSImage(size: NSSize(width: size, height: size))
    img.lockFocus()
    let rect = NSRect(x: 0, y: 0, width: size, height: size)
    let rounded = NSBezierPath(roundedRect: rect, xRadius: size * 0.18, yRadius: size * 0.18)
    // Deep backdrop with subtle horizon
    let bg = NSGradient(colors: [
        NSColor(calibratedRed: 0.04, green: 0.07, blue: 0.14, alpha: 1),
        NSColor(calibratedRed: 0.02, green: 0.05, blue: 0.11, alpha: 1)
    ])!
    bg.draw(in: rounded, angle: 90)
    let horizon = NSGradient(colors: [
        NSColor(calibratedRed: 0.12, green: 0.18, blue: 0.32, alpha: 0.22),
        NSColor(calibratedRed: 0.04, green: 0.07, blue: 0.14, alpha: 0)
    ])!
    horizon.draw(from: NSPoint(x: 0, y: size * 0.58),
                 to: NSPoint(x: 0, y: size * 0.9),
                 options: .drawsBeforeStartingLocation)
    // Ripple arcs anchored at bottom
    let anchorY = size * 0.14
    let anchor = NSPoint(x: size/2, y: anchorY)
    let arcs: [CGFloat] = [0.17, 0.28, 0.38]
    for (i, frac) in arcs.enumerated() {
        let r = size * frac
        let center = NSPoint(x: anchor.x, y: anchor.y + r)
        let arc = NSBezierPath()
        arc.appendArc(withCenter: center, radius: r, startAngle: 215, endAngle: -35, clockwise: true)
        arc.lineCapStyle = .round
        let strokeWidth = max(1.0, size * 0.0165)
        arc.lineWidth = strokeWidth
        let alpha = 0.88 - CGFloat(i) * 0.10
        let light = NSColor(calibratedWhite: 0.97, alpha: alpha)
        let mid = NSColor(calibratedWhite: 0.93, alpha: alpha)
        let dark = NSColor(calibratedWhite: 0.78, alpha: alpha * 0.55)

        let shadowPath = arc.copy() as! NSBezierPath
        shadowPath.lineWidth = strokeWidth + max(0.2, size * 0.002)
        NSGraphicsContext.saveGraphicsState()
        dark.setStroke()
        let shadow = NSShadow()
        shadow.shadowBlurRadius = max(0.6, size * 0.004)
        shadow.shadowOffset = NSSize(width: 0, height: -size * 0.004)
        shadow.shadowColor = dark.withAlphaComponent(alpha * 0.4)
        shadow.set()
        shadowPath.stroke()
        NSGraphicsContext.restoreGraphicsState()

        mid.setStroke()
        arc.stroke()

        let highlight = arc.copy() as! NSBezierPath
        highlight.lineWidth = strokeWidth * 0.65
        NSGraphicsContext.saveGraphicsState()
        light.setStroke()
        let hShadow = NSShadow()
        hShadow.shadowBlurRadius = max(0.4, size * 0.003)
        hShadow.shadowOffset = NSSize(width: 0, height: size * 0.002)
        hShadow.shadowColor = light.withAlphaComponent(alpha * 0.35)
        hShadow.set()
        highlight.stroke()
        NSGraphicsContext.restoreGraphicsState()
    }
    // Base shelf
    let shelfHeight = max(1, size * 0.0065)
    let shelfWidth = size * 0.36
    let shelfRect = NSRect(x: anchor.x - shelfWidth/2, y: anchor.y - shelfHeight/2, width: shelfWidth, height: shelfHeight)
    let shelf = NSBezierPath(roundedRect: shelfRect, xRadius: shelfHeight/2, yRadius: shelfHeight/2)
    let shelfFill = NSColor(calibratedWhite: 0.92, alpha: 0.68)
    shelfFill.setFill()
    shelf.fill()
    let shelfHighlight = NSBezierPath(roundedRect: shelfRect.insetBy(dx: size * 0.002, dy: size * 0.001), xRadius: shelfHeight/2, yRadius: shelfHeight/2)
    NSGraphicsContext.saveGraphicsState()
    NSColor(calibratedWhite: 0.98, alpha: 0.28).setStroke()
    shelfHighlight.lineWidth = max(0.5, size * 0.0015)
    shelfHighlight.stroke()
    NSGraphicsContext.restoreGraphicsState()
    let shelfShadow = NSBezierPath(roundedRect: shelfRect, xRadius: shelfHeight/2, yRadius: shelfHeight/2)
    NSGraphicsContext.saveGraphicsState()
    NSColor(calibratedWhite: 0.65, alpha: 0.25).setStroke()
    shelfShadow.lineWidth = max(0.8, size * 0.0025)
    let sShadow = NSShadow()
    sShadow.shadowBlurRadius = max(0.4, size * 0.003)
    sShadow.shadowOffset = NSSize(width: 0, height: -size * 0.002)
    sShadow.shadowColor = NSColor.black.withAlphaComponent(0.18)
    sShadow.set()
    shelfShadow.stroke()
    NSGraphicsContext.restoreGraphicsState()
    // Central dot
    let dotSize = size * 0.12
    let dotRect = NSRect(x: anchor.x - dotSize/2, y: anchor.y - dotSize/2, width: dotSize, height: dotSize)
    let dot = NSBezierPath(ovalIn: dotRect)
    let dotGradient = NSGradient(colors: [
        NSColor(calibratedWhite: 0.985, alpha: 1.0),
        NSColor(calibratedWhite: 0.88, alpha: 0.78)
    ])!
    dotGradient.draw(in: dot, relativeCenterPosition: NSPoint(x: 0, y: 0))
    // Soft glow
    let glow = NSBezierPath(roundedRect: rect, xRadius: size * 0.18, yRadius: size * 0.18)
    NSColor.white.withAlphaComponent(0.025).setStroke()
    glow.lineWidth = max(1, size * 0.0075)
    glow.stroke()
    img.unlockFocus()

    guard let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff), let data = rep.representation(using: .png, properties: [:]) else { continue }
    let url = outDir.appendingPathComponent("icon_\(Int(size)).png")
    try data.write(to: url)
    print("wrote", url.path)
}
