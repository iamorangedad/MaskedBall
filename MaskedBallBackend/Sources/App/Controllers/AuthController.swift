import Vapor
import JWT

struct AuthController: RouteCollection {
    func boot(routes: RoutesBuilder) throws {
        routes.post("register", use: register)
        routes.post("login", use: login)
    }
    
    func register(req: Request) async throws -> UserResponse {
        let create = try req.content.decode(CreateUser.self)
        
        guard create.username.count >= 3 else {
            throw Abort(.badRequest, reason: "Username must be at least 3 characters")
        }
        
        guard create.password.count >= 6 else {
            throw Abort(.badRequest, reason: "Password must be at least 6 characters")
        }
        
        let existingUser = try await User.query(on: req.db)
            .filter(\.$email == create.email)
            .first()
        
        if existingUser != nil {
            throw Abort(.badRequest, reason: "Email already registered")
        }
        
        let passwordHash = try await req.password.hash(create.password)
        
        let user = User(from: create, passwordHash: passwordHash)
        try await user.save(on: req.db)
        
        return UserResponse(
            id: user.id!,
            username: user.username,
            email: user.email,
            createdAt: user.createdAt
        )
    }
    
    func login(req: Request) async throws -> TokenResponse {
        let loginData = try req.content.decode(LoginRequest.self)
        
        guard let user = try await User.query(on: req.db)
            .filter(\.$email == loginData.email)
            .first() else {
            throw Abort(.unauthorized, reason: "Invalid credentials")
        }
        
        let verified = try await req.password.verify(loginData.password, hash: user.passwordHash)
        
        guard verified else {
            throw Abort(.unauthorized, reason: "Invalid credentials")
        }
        
        let token = try await generateToken(for: user, on: req)
        
        return TokenResponse(
            token: token,
            user: UserResponse(
                id: user.id!,
                username: user.username,
                email: user.email,
                createdAt: user.createdAt
            )
        )
    }
    
    private func generateToken(for user: User, on req: Request) async throws -> String {
        let payload = TokenPayload(
            subject: user.id!.uuidString,
            username: user.username,
            expires: Date().addingTimeInterval(86400 * 7)
        )
        
        return try await req.jwt.sign(payload)
    }
}

struct LoginRequest: Content {
    let email: String
    let password: String
}

struct TokenResponse: Content {
    let token: String
    let user: UserResponse
}

struct TokenPayload: JWTPayload {
    var subject: StringClaim
    var username: StringClaim
    var expires: ExpirationClaim
    
    func verify(using signer: JWTSigner) throws {
        try expires.verify()
    }
}