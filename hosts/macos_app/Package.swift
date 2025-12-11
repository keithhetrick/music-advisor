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
                .product(name: "MAStyle", package: "design_system")
            ],
            path: "Sources",
            exclude: ["MAQueue"]
        ),
        .testTarget(
            name: "MusicAdvisorMacAppTests",
            dependencies: ["MusicAdvisorMacApp", "MAQueue", "ViewInspector"],
            path: "Tests",
            exclude: ["MusicAdvisorMacAppUITests"]
        )
    ]
)
