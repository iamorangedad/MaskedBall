import Foundation

struct ChatHistory: Codable {
    let botId: UUID
    var messages: [ChatMessage]
    var lastUpdated: Date
    
    init(botId: UUID, messages: [ChatMessage] = [], lastUpdated: Date = Date()) {
        self.botId = botId
        self.messages = messages
        self.lastUpdated = lastUpdated
    }
}

final class ChatHistoryManager {
    static let shared = ChatHistoryManager()
    
    private let defaults = UserDefaults.standard
    private let historyKey = "chatHistory"
    
    private init() {}
    
    func saveMessage(_ message: ChatMessage, for botId: UUID) {
        var allHistory = loadAllHistory()
        
        if var history = allHistory[botId.uuidString] {
            history.messages.append(message)
            history.lastUpdated = Date()
            allHistory[botId.uuidString] = history
        } else {
            let newHistory = ChatHistory(botId: botId, messages: [message])
            allHistory[botId.uuidString] = newHistory
        }
        
        saveAllHistory(allHistory)
    }
    
    func loadHistory(for botId: UUID) -> [ChatMessage] {
        let allHistory = loadAllHistory()
        return allHistory[botId.uuidString]?.messages ?? []
    }
    
    func loadAllChats() -> [UUID: [ChatMessage]] {
        let allHistory = loadAllHistory()
        var result: [UUID: [ChatMessage]] = [:]
        
        for (key, history) in allHistory {
            if let uuid = UUID(uuidString: key) {
                result[uuid] = history.messages
            }
        }
        
        return result
    }
    
    func deleteHistory(for botId: UUID) {
        var allHistory = loadAllHistory()
        allHistory.removeValue(forKey: botId.uuidString)
        saveAllHistory(allHistory)
    }
    
    func clearAllHistory() {
        defaults.removeObject(forKey: historyKey)
    }
    
    private func loadAllHistory() -> [String: ChatHistory] {
        guard let data = defaults.data(forKey: historyKey),
              let history = try? JSONDecoder().decode([String: ChatHistory].self, from: data) else {
            return [:]
        }
        return history
    }
    
    private func saveAllHistory(_ history: [String: ChatHistory]) {
        if let data = try? JSONEncoder().encode(history) {
            defaults.set(data, forKey: historyKey)
        }
    }
    
    func getChatPartnerIds() -> Set<UUID> {
        let allHistory = loadAllHistory()
        var ids = Set<UUID>()
        for key in allHistory.keys {
            if let uuid = UUID(uuidString: key) {
                ids.insert(uuid)
            }
        }
        return ids
    }
}