import Fluent
import Vapor

final class User: Model, Content, ModelSessionable {
    static let schema = "users"
    
    @ID(key: .id)
    var id: UUID?
    
    @Field(key: "username")
    var username: String
    
    @Field(key: "email")
    var email: String
    
    @Field(key: "password_hash")
    var passwordHash: String
    
    @Field(key: "created_at")
    var createdAt: Date
    
    @Children(for: \.$user)
    var botProfile: BotProfile?
    
    init() {}
    
    init(id: UUID? = nil, username: String, email: String, passwordHash: String) {
        self.id = id
        self.username = username
        self.email = email
        self.passwordHash = passwordHash
        self.createdAt = Date()
    }
}

struct CreateUser: Content {
    let username: String
    let email: String
    let password: String
}

struct UserResponse: Content {
    let id: UUID
    let username: String
    let email: String
    let createdAt: Date
}

extension User: ModelInitializable {
    convenience init(from create: CreateUser, passwordHash: String) {
        self.init(
            username: create.username,
            email: create.email,
            passwordHash: passwordHash
        )
    }
}