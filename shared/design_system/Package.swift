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
    dependencies: [],
    targets: [
        .target(
            name: "MAStyle",
            dependencies: []),
        .testTarget(
            name: "MAStyleTests",
            dependencies: ["MAStyle"]),
    ]
)
