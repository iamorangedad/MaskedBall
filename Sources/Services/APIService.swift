import Foundation

actor APIService {
    static let shared = APIService()
    
    private let baseURL: String
    private var authToken: String?
    
    private init() {
        self.baseURL = "http://localhost:8080"
    }
    
    func setAuthToken(_ token: String) {
        self.authToken = token
    }
    
    func clearAuthToken() {
        self.authToken = nil
    }
    
    enum APIError: Error, LocalizedError {
        case invalidURL
        case invalidResponse
        case httpError(Int)
        case decodingError(Error)
        case networkError(Error)
        
        var errorDescription: String? {
            switch self {
            case .invalidURL:
                return "Invalid URL"
            case .invalidResponse:
                return "Invalid response from server"
            case .httpError(let code):
                return "HTTP error: \(code)"
            case .decodingError(let error):
                return "Decoding error: \(error.localizedDescription)"
            case .networkError(let error):
                return "Network error: \(error.localizedDescription)"
            }
        }
    }
    
    func register(username: String, email: String, password: String) async throws -> UserResponse {
        let endpoint = "\(baseURL)/register"
        guard let url = URL(string: endpoint) else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = ["username": username, "email": email, "password": password]
        request.httpBody = try JSONEncoder().encode(body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(UserResponse.self, from: data)
    }
    
    func login(email: String, password: String) async throws -> TokenResponse {
        let endpoint = "\(baseURL)/login"
        guard let url = URL(string: endpoint) else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = ["email": email, "password": password]
        request.httpBody = try JSONEncoder().encode(body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        let tokenResponse = try JSONDecoder().decode(TokenResponse.self, from: data)
        authToken = tokenResponse.token
        
        return tokenResponse
    }
    
    func getAllBots() async throws -> [BotProfileResponse] {
        let endpoint = "\(baseURL)/bots"
        guard let url = URL(string: endpoint) else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode([BotProfileResponse].self, from: data)
    }
    
    func getBot(id: UUID) async throws -> BotProfileResponse {
        let endpoint = "\(baseURL)/bots/\(id.uuidString)"
        guard let url = URL(string: endpoint) else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(BotProfileResponse.self, from: data)
    }
    
    func createBot(_ bot: CreateBotProfile) async throws -> BotProfileResponse {
        let endpoint = "\(baseURL)/bots"
        guard let url = URL(string: endpoint) else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        request.httpBody = try JSONEncoder().encode(bot)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(BotProfileResponse.self, from: data)
    }
    
    func updateBot(id: UUID, _ bot: CreateBotProfile) async throws -> BotProfileResponse {
        let endpoint = "\(baseURL)/bots/\(id.uuidString)"
        guard let url = URL(string: endpoint) else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        request.httpBody = try JSONEncoder().encode(bot)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(BotProfileResponse.self, from: data)
    }
    
    func searchBots(query: String) async throws -> [BotProfileResponse] {
        let endpoint = "\(baseURL)/bots/search?q=\(query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query)"
        guard let url = URL(string: endpoint) else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode([BotProfileResponse].self, from: data)
    }
}

struct UserResponse: Codable {
    let id: UUID
    let username: String
    let email: String
    let createdAt: Date
}

struct TokenResponse: Codable {
    let token: String
    let user: UserResponse
}

struct BotProfileResponse: Codable {
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
    
    func toBotProfile() -> BotProfile {
        BotProfile(
            id: id,
            name: name,
            personality: BotPersonality(rawValue: personality) ?? .friendly,
            languageStyle: BotLanguageStyle(rawValue: languageStyle) ?? .casual,
            bio: bio,
            keywords: keywords,
            greeting: greeting,
            viewCount: viewCount,
            chatCount: chatCount,
            createdAt: createdAt
        )
    }
}

struct CreateBotProfile: Codable {
    let name: String
    let personality: String
    let languageStyle: String
    let bio: String
    let keywords: [String]
    let greeting: String
}