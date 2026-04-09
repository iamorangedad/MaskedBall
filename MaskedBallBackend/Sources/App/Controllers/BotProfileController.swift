import Vapor
import Fluent

struct BotProfileController: RouteCollection {
    func boot(routes: RoutesBuilder) throws {
        routes.get("bots", use: getAllBots)
        routes.get("bots", ":id", use: getBot)
        routes.post("bots", use: createBot)
        routes.put("bots", ":id", use: updateBot)
        routes.delete("bots", ":id", use: deleteBot)
        routes.get("bots", "search", use: searchBots)
    }
    
    func getAllBots(req: Request) async throws -> [BotProfileResponse] {
        let bots = try await BotProfile.query(on: req.db)
            .sort(\.$viewCount, .descending)
            .all()
        
        return bots.map { BotProfileResponse(from: $0) }
    }
    
    func getBot(req: Request) async throws -> BotProfileResponse {
        guard let bot = try await BotProfile.find(req.parameters.get("id"), on: req.db) else {
            throw Abort(.notFound, reason: "Bot not found")
        }
        
        bot.viewCount += 1
        try await bot.update(on: req.db)
        
        return BotProfileResponse(from: bot)
    }
    
    func createBot(req: Request) async throws -> BotProfileResponse {
        let create = try req.content.decode(CreateBotProfile.self)
        
        guard let userId = req.auth.get(User.self)?.id else {
            throw Abort(.unauthorized, reason: "Not authenticated")
        }
        
        let bot = BotProfile(
            name: create.name,
            personality: create.personality,
            languageStyle: create.languageStyle,
            bio: create.bio,
            keywords: create.keywords,
            greeting: create.greeting
        )
        
        bot.$user.id = userId
        
        try await bot.save(on: req.db)
        
        return BotProfileResponse(from: bot)
    }
    
    func updateBot(req: Request) async throws -> BotProfileResponse {
        guard let bot = try await BotProfile.find(req.parameters.get("id"), on: req.db) else {
            throw Abort(.notFound, reason: "Bot not found")
        }
        
        guard let userId = req.auth.get(User.self)?.id, bot.$user.id == userId else {
            throw Abort(.forbidden, reason: "Not authorized")
        }
        
        let update = try req.content.decode(CreateBotProfile.self)
        
        bot.name = update.name
        bot.personality = update.personality
        bot.languageStyle = update.languageStyle
        bot.bio = update.bio
        bot.keywords = update.keywords
        bot.greeting = update.greeting
        
        try await bot.update(on: req.db)
        
        return BotProfileResponse(from: bot)
    }
    
    func deleteBot(req: Request) async throws -> HTTPStatus {
        guard let bot = try await BotProfile.find(req.parameters.get("id"), on: req.db) else {
            throw Abort(.notFound, reason: "Bot not found")
        }
        
        guard let userId = req.auth.get(User.self)?.id, bot.$user.id == userId else {
            throw Abort(.forbidden, reason: "Not authorized")
        }
        
        try await bot.delete(on: req.db)
        
        return .noContent
    }
    
    func searchBots(req: Request) async throws -> [BotProfileResponse] {
        guard let query = req.query[String.self, at: "q"] else {
            throw Abort(.badRequest, reason: "Search query required")
        }
        
        let lowercasedQuery = query.lowercased()
        
        let bots = try await BotProfile.query(on: req.db).all()
        
        let filtered = bots.filter { bot in
            bot.name.lowercased().contains(lowercasedQuery) ||
            bot.bio.lowercased().contains(lowercasedQuery) ||
            bot.personality.lowercased().contains(lowercasedQuery) ||
            bot.keywords.contains { $0.lowercased().contains(lowercasedQuery) }
        }
        
        return filtered.map { BotProfileResponse(from: $0) }
    }
}