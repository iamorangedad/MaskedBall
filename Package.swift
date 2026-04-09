// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "MaskedBall",
    platforms: [
        .iOS(.v17)
    ],
    products: [
        .library(
            name: "MaskedBall",
            targets: ["MaskedBall"]
        )
    ],
    dependencies: [
        .package(url: "https://github.com/ml-explore/mlx-swift", from: "0.25.0"),
        .package(url: "https://github.com/ml-explore/mlx-swift-examples", from: "0.25.0),
        .package(url: "https://github.com/daltoniam/Starscream", from: "4.0.0")
    ],
    targets: [
        .target(
            name: "MaskedBall",
            dependencies: [
                .product(name: "MLX", package: "mlx-swift"),
                .product(name: "MLXLLM", package: "mlx-swift-examples"),
                .product(name: "Starscream", package: "Starscream")
            ],
            path: "Sources"
        )
    ]
)