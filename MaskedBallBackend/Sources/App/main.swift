import Vapor
import Fluent
import JWT

var env = try Environment.detect()
let app = Application(env)

defer {
    app.shutdown()
}

app.middleware.use(FileMiddleware.self)

app.middleware.use(JWTEncryptMiddleware())

app.databases.use(.sqlite(.file("maskedball.sqlite")), as: .sqlite)

app.migrations.add(CreateUser())
app.migrations.add(CreateBotProfile())

app.on(.boot) { app async in
    try await app.autoMigrate()
}

try app.register(collection: AuthController())
try app.register(collection: BotProfileController())

struct JWTEncryptMiddleware: Middleware {
    func respond(to request: Request, chainingTo next: PublicResponder) async throws -> Response {
        try await next.respond(to: request)
    }
}

func routes(_ app: Application) throws {
    app.get("hello") { req in
        return "Hello, MaskedBall API!"
    }
    
    app.get("version") { req in
        return ["version": "1.0.0", "name": "MaskedBall Backend"]
    }
}

routes(app)

try app.run()