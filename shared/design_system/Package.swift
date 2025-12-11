// swift-tools-version: 5.7
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "MAStyle",
    platforms: [.macOS(.v12)],
    products: [
        .library(
            name: "MAStyle",
            targets: ["MAStyle"]),
    ],
    dependencies: [
        .package(url: "https://github.com/nalexn/ViewInspector", from: "0.9.4")
    ],
    targets: [
        .target(
            name: "MAStyle",
            dependencies: []),
        .testTarget(
            name: "MAStyleTests",
            dependencies: ["MAStyle", .product(name: "ViewInspector", package: "ViewInspector")]),
    ]
)
