import Foundation

actor RecommendationService {
    static let shared = RecommendationService()
    
    private init() {}
    
    struct RecommendationResult {
        let bots: [BotProfile]
        let score: Double
    }
    
    func getRecommendations(
        for userInterests: [String],
        from bots: [BotProfile],
        limit: Int = 10
    ) -> [BotProfile] {
        let scored = bots.map { bot -> (BotProfile, Double) in
            let score = calculateScore(bot: bot, userInterests: userInterests)
            return (bot, score)
        }
        
        let sorted = scored
            .sorted { $0.1 > $1.1 }
            .prefix(limit)
        
        return sorted.map { $0.0 }
    }
    
    private func calculateScore(bot: BotProfile, userInterests: [String]) -> Double {
        var score: Double = 0
        
        let lowercasedInterests = userInterests.map { $0.lowercased() }
        
        for keyword in bot.keywords {
            let lowercasedKeyword = keyword.lowercased()
            
            if lowercasedInterests.contains(where: { lowercasedKeyword.contains($0) || $0.contains(lowercasedKeyword) }) {
                score += 2.0
            }
        }
        
        score += Double(bot.viewCount) * 0.001
        score += Double(bot.chatCount) * 0.002
        
        if let firstKeyword = bot.keywords.first {
            if lowercasedInterests.contains(firstKeyword.lowercased()) {
                score += 1.0
            }
        }
        
        let daysSinceCreated = Date().timeIntervalSince(bot.createdAt) / 86400
        if daysSinceCreated < 30 {
            score += 0.5
        }
        
        return score
    }
    
    func getSimilarBots(
        targetBot: BotProfile,
        from bots: [BotProfile],
        limit: Int = 5
    ) -> [BotProfile] {
        let targetKeywords = Set(targetBot.keywords.map { $0.lowercased() })
        let targetPersonality = targetBot.personality
        
        let scored = bots
            .filter { $0.id != targetBot.id }
            .map { bot -> (BotProfile, Double) in
                var score: Double = 0
                
                if bot.personality == targetPersonality {
                    score += 1.5
                }
                
                let botKeywords = Set(bot.keywords.map { $0.lowercased() })
                let commonKeywords = targetKeywords.intersection(botKeywords)
                score += Double(commonKeywords.count) * 1.0
                
                return (bot, score)
            }
        
        return scored
            .sorted { $0.1 > $1.1 }
            .prefix(limit)
            .map { $0.0 }
    }
    
    func getPopularBots(from bots: [BotProfile], limit: Int = 10) -> [BotProfile] {
        bots
            .sorted { $0.viewCount > $1.viewCount }
            .prefix(limit)
            .map { $0 }
    }
    
    func getRecentBots(from bots: [BotProfile], limit: Int = 10) -> [BotProfile] {
        bots
            .sorted { $0.createdAt > $1.createdAt }
            .prefix(limit)
            .map { $0 }
    }
    
    func getBotsByPersonality(
        _ personality: BotPersonality,
        from bots: [BotProfile]
    ) -> [BotProfile] {
        bots
            .filter { $0.personality == personality }
            .sorted { $0.viewCount > $1.viewCount }
    }
}

struct RecommendationEngine {
    private let recommendationService = RecommendationService.shared
    
    func getRecommendedBots(
        for userInterests: [String],
        availableBots: [BotProfile],
        userChatHistory: Set<UUID>
    ) async -> [BotProfile] {
        let candidates = availableBots.filter { !userChatHistory.contains($0.id) }
        
        return await recommendationService.getRecommendations(
            for: userInterests,
            from: candidates
        )
    }
    
    func getExploreBots(availableBots: [BotProfile]) async -> [BotProfile] {
        await recommendationService.getPopularBots(from: availableBots)
    }
}