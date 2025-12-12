// swift-tools-version: 5.7
import PackageDescription

let package = Package(
    name: "TaskConductor",
    platforms: [
        .macOS(.v12)
    ],
products: [
    .library(
        name: "TaskConductor",
        targets: ["TaskConductor"]
    ),
    .executable(
        name: "TaskConductorDemo",
        targets: ["TaskConductorDemo"]
    )
],
targets: [
    .target(
        name: "TaskConductor"
    ),
    .executableTarget(
        name: "TaskConductorDemo",
        dependencies: ["TaskConductor"]
    ),
    .testTarget(
        name: "TaskConductorTests",
        dependencies: ["TaskConductor"]
    )
]
)
