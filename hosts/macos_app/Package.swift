// swift-tools-version:5.7
import PackageDescription

let package = Package(
    name: "MusicAdvisorMacApp",
    platforms: [.macOS(.v12)],
    products: [
        .executable(name: "MusicAdvisorMacApp", targets: ["MusicAdvisorMacApp"])
    ],
    dependencies: [
        .package(path: "../../shared/design_system")
    ],
    targets: [
        .executableTarget(
            name: "MusicAdvisorMacApp",
            dependencies: [
                .product(name: "MAStyle", package: "design_system")
            ],
            path: "Sources"
        )
    ]
)
