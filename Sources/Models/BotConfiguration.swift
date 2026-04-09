import Foundation

enum BotPersonality: String, CaseIterable, Identifiable {
    case friendly = "Friendly"
    case humorous = "Humorous"
    case mysterious = "Mysterious"
    case academic = "Academic"
    case creative = "Creative"
    case supportive = "Supportive"
    
    var id: String { rawValue }
    
    var description: String {
        switch self {
        case .friendly: return "Warm and approachable, always ready to help"
        case .humorous: return "Playful and witty, loves to make people laugh"
        case .mysterious: return "Enigmatic and intriguing, keeps conversations interesting"
        case .academic: return "Knowledgeable and precise, loves deep discussions"
        case .creative: return "Imaginative and artistic, thinks outside the box"
        case .supportive: return "Empathetic and encouraging, a good listener"
        }
    }
}

enum BotLanguageStyle: String, CaseIterable, Identifiable {
    case formal = "Formal"
    case casual = "Casual"
    case internetSlang = "Internet Slang"
    case poetic = "Poetic"
    case technical = "Technical"
    
    var id: String { rawValue }
}

struct BotConfiguration: Codable {
    var name: String = "My Bot"
    var personality: BotPersonality = .friendly
    var languageStyle: BotLanguageStyle = .casual
    var bio: String = ""
    var keywords: [String] = []
    var greeting: String = "Hello! I'm here to chat with you."
    
    func generateSystemPrompt() -> String {
        var prompt = """
        You are a character in a chat application. Your personality and behavior are defined by the following traits:
        
        """
        
        prompt += "Personality: \(personality.rawValue). \(personality.description)\n"
        prompt += "Language Style: \(languageStyle.rawValue)\n"
        
        if !bio.isEmpty {
            prompt += "Background: \(bio)\n"
        }
        
        if !keywords.isEmpty {
            prompt += "Interests: \(keywords.joined(separator: ", "))\n"
        }
        
        prompt += """
        
        Guidelines:
        - Stay in character at all times
        - Use the specified language style naturally
        - Be engaging and interesting in conversations
        - Respond to messages as this character would
        - Keep responses concise and conversational
        - Never break the fourth wall or mention you are an AI
        """
        
        return prompt
    }
}