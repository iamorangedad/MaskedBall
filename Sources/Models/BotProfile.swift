import Foundation

struct BotProfile: Identifiable, Codable {
    let id: UUID
    var name: String
    var personality: BotPersonality
    var languageStyle: BotLanguageStyle
    var bio: String
    var keywords: [String]
    var greeting: String
    var viewCount: Int
    var chatCount: Int
    var createdAt: Date
    
    init(
        id: UUID = UUID(),
        name: String = "My Bot",
        personality: BotPersonality = .friendly,
        languageStyle: BotLanguageStyle = .casual,
        bio: String = "",
        keywords: [String] = [],
        greeting: String = "Hello!",
        viewCount: Int = 0,
        chatCount: Int = 0,
        createdAt: Date = Date()
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
        self.createdAt = createdAt
    }
    
    init(from config: BotConfiguration) {
        self.id = UUID()
        self.name = config.name
        self.personality = config.personality
        self.languageStyle = config.languageStyle
        self.bio = config.bio
        self.keywords = config.keywords
        self.greeting = config.greeting
        self.viewCount = 0
        self.chatCount = 0
        self.createdAt = Date()
    }
    
    var searchableText: String {
        [name, bio, personality.rawValue, languageStyle.rawValue]
            .joined(separator: " ")
            .lowercased()
    }
}

struct User: Identifiable, Codable {
    let id: UUID
    var username: String
    var email: String
    var createdAt: Date
    var botProfile: BotProfile?
    
    init(
        id: UUID = UUID(),
        username: String,
        email: String,
        createdAt: Date = Date(),
        botProfile: BotProfile? = nil
    ) {
        self.id = id
        self.username = username
        self.email = email
        self.createdAt = createdAt
        self.botProfile = botProfile
    }
}