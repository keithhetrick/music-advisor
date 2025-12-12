// swift-tools-version: 5.7
import PackageDescription

let package = Package(
    name: "ContentAddressedBroker",
    platforms: [
        .macOS(.v12),
        .iOS(.v15)
    ],
    products: [
        .library(
            name: "ContentAddressedBroker",
            targets: ["ContentAddressedBroker"]
        ),
    ],
    targets: [
        .target(
            name: "ContentAddressedBroker"
        ),
        .testTarget(
            name: "ContentAddressedBrokerTests",
            dependencies: ["ContentAddressedBroker"]
        ),
    ]
)
