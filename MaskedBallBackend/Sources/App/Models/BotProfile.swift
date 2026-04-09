import Fluent
import Vapor

final class BotProfile: Model, Content {
    static let schema = "bot_profiles"
    
    @ID(key: .id)
    var id: UUID?
    
    @Field(key: "name")
    var name: String
    
    @Field(key: "personality")
    var personality: String
    
    @Field(key: "language_style")
    var languageStyle: String
    
    @Field(key: "bio")
    var bio: String
    
    @Field(key: "keywords")
    var keywords: [String]
    
    @Field(key: "greeting")
    var greeting: String
    
    @Field(key: "view_count")
    var viewCount: Int
    
    @Field(key: "chat_count")
    var chatCount: Int
    
    @Field(key: "created_at")
    var createdAt: Date
    
    @Parent(key: "user_id")
    var user: User
    
    init() {}
    
    init(
        id: UUID? = nil,
        name: String,
        personality: String,
        languageStyle: String,
        bio: String,
        keywords: [String],
        greeting: String,
        viewCount: Int = 0,
        chatCount: Int = 0
    ) {
        self.id = id
        self.name = name
        self.personality = personality
        self.languageStyle = languageStyle
        self.bio = bio
        self.keywords = keywords
        self.greeting = greeting
        self.viewCount = viewCount
        self.chatCount = chatCount
        self.createdAt = Date()
    }
}

struct BotProfileResponse: Content {
    let id: UUID
    let name: String
    let personality: String
    let languageStyle: String
    let bio: String
    let keywords: [String]
    let greeting: String
    let viewCount: Int
    let chatCount: Int
    let createdAt: Date
    
    init(from profile: BotProfile) {
        self.id = profile.id ?? UUID()
        self.name = profile.name
        self.personality = profile.personality
        self.languageStyle = profile.languageStyle
        self.bio = profile.bio
        self.keywords = profile.keywords
        self.greeting = profile.greeting
        self.viewCount = profile.viewCount
        self.chatCount = profile.chatCount
        self.createdAt = profile.createdAt
    }
}

struct CreateBotProfile: Content {
    let name: String
    let personality: String
    let languageStyle: String
    let bio: String
    let keywords: [String]
    let greeting: String
}