// swift-tools-version:5.7
import PackageDescription

let package = Package(
    name: "MusicAdvisorMacApp",
    platforms: [.macOS(.v12)],
    products: [
        .executable(name: "MusicAdvisorMacApp", targets: ["MusicAdvisorMacApp"]),
        .library(name: "MAQueue", targets: ["MAQueue"])
    ],
    dependencies: [
        .package(path: "../../shared/design_system"),
        .package(path: "../../shared/content_addressed_broker_swift"),
        .package(url: "https://github.com/nalexn/ViewInspector.git", exact: "0.9.6")
    ],
    targets: [
        .target(
            name: "MAQueue",
            dependencies: [],
            path: "Sources/MAQueue"
        ),
        .executableTarget(
            name: "MusicAdvisorMacApp",
            dependencies: [
                "MAQueue",
                .product(name: "MAStyle", package: "design_system"),
                .product(name: "ContentAddressedBroker", package: "content_addressed_broker_swift")
            ],
            path: "Sources",
            exclude: ["MAQueue"]
        ),
        .testTarget(
            name: "MusicAdvisorMacAppTests",
            dependencies: ["MusicAdvisorMacApp", "MAQueue", "ViewInspector", .product(name: "ContentAddressedBroker", package: "content_addressed_broker_swift")],
            path: "Tests",
            exclude: ["MusicAdvisorMacAppUITests"]
        )
    ]
)
