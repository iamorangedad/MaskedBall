import Foundation

struct ChatMessage: Identifiable {
    let id = UUID()
    let content: String
    let sender: MessageSender
    let timestamp: Date
    
    var isFromBot: Bool {
        if case .bot = sender { return true }
        return false
    }
}

enum MessageSender: Codable {
    case user
    case bot(UUID)
}