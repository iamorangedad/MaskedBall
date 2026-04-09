// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MaskedBallBackend",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "MaskedBallBackend", targets: ["App"])
    ],
    dependencies: [
        .package(url: "https://github.com/vapor/vapor", from: "4.99.0"),
        .package(url: "https://github.com/vapor/jwt", from: "4.2.0"),
        .package(url: "https://github.com/vapor/fluent", from: "4.9.0"),
        .package(url: "https://github.com/vapor/fluent-sqlite-driver", from: "4.0.0")
    ],
    targets: [
        .executableTarget(
            name: "App",
            dependencies: [
                .product(name: "Vapor", package: "vapor"),
                .product(name: "JWT", package: "jwt"),
                .product(name: "Fluent", package: "fluent"),
                .product(name: "FluentSQLiteDriver", package: "fluent-sqlite-driver")
            ],
            path: "Sources/App"
        )
    ]
)