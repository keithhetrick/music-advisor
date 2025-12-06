// swift-tools-version:5.7
import PackageDescription

let package = Package(
    name: "MusicAdvisorMacApp",
    platforms: [.macOS(.v12)],
    products: [
        .executable(name: "MusicAdvisorMacApp", targets: ["MusicAdvisorMacApp"])
    ],
    targets: [
        .executableTarget(
            name: "MusicAdvisorMacApp",
            path: "Sources"
        )
    ]
)
