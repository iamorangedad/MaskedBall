import Foundation
import Starscream

protocol WebSocketServiceDelegate: AnyObject {
    func webSocketDidConnect()
    func webSocketDidDisconnect(error: Error?)
    func webSocketDidReceiveMessage(_ message: SocketMessage)
}

final class WebSocketService: NSObject {
    static let shared = WebSocketService()
    
    weak var delegate: WebSocketServiceDelegate?
    
    private var socket: WebSocket?
    private var isConnected = false
    private var reconnectAttempts = 0
    private let maxReconnectAttempts = 5
    
    private var currentUserId: String?
    private var currentBotId: String?
    
    private override init() {
        super.init()
    }
    
    func connect(to urlString: String, userId: String) {
        currentUserId = userId
        
        guard let url = URL(string: urlString) else {
            print("Invalid WebSocket URL")
            return
        }
        
        var request = URLRequest(url: url)
        request.timeoutInterval = 5
        
        socket = WebSocket(request: request)
        socket?.delegate = self
        socket?.connect()
    }
    
    func disconnect() {
        socket?.disconnect()
        socket = nil
        isConnected = false
    }
    
    func sendMessage(_ message: SocketMessage) {
        guard isConnected else {
            print("WebSocket not connected")
            return
        }
        
        if let data = try? JSONEncoder().encode(message),
           let jsonString = String(data: data, encoding: .utf8) {
            socket?.write(string: jsonString)
        }
    }
    
    func sendChatMessage(content: String, receiverId: String) {
        guard let senderId = currentUserId else { return }
        
        let message = SocketMessage(
            type: .chat,
            senderId: senderId,
            receiverId: receiverId,
            content: content,
            timestamp: Date()
        )
        
        sendMessage(message)
    }
    
    func sendTypingIndicator(receiverId: String, isTyping: Bool) {
        guard let senderId = currentUserId else { return }
        
        let message = SocketMessage(
            type: .typing,
            senderId: senderId,
            receiverId: receiverId,
            content: isTyping ? "true" : "false",
            timestamp: Date()
        )
        
        sendMessage(message)
    }
    
    func sendReadReceipt(messageId: String, senderId: String) {
        guard let userId = currentUserId else { return }
        
        let message = SocketMessage(
            type: .read,
            senderId: userId,
            receiverId: senderId,
            content: messageId,
            timestamp: Date()
        )
        
        sendMessage(message)
    }
    
    private func handleAuth() {
        guard let userId = currentUserId else { return }
        
        let authMessage = SocketMessage(
            type: .auth,
            senderId: userId,
            receiverId: nil,
            content: nil,
            timestamp: Date()
        )
        
        sendMessage(authMessage)
    }
    
    private func attemptReconnect() {
        guard reconnectAttempts < maxReconnectAttempts else {
            print("Max reconnect attempts reached")
            return
        }
        
        reconnectAttempts += 1
        let delay = Double(reconnectAttempts) * 2.0
        
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            self?.socket?.connect()
        }
    }
}

extension WebSocketService: WebSocketDelegate {
    func didReceive(event: WebSocketEvent, client: WebSocketClient) {
        switch event {
        case .connected:
            isConnected = true
            reconnectAttempts = 0
            handleAuth()
            delegate?.webSocketDidConnect()
            
        case .disconnected(let reason, let code):
            isConnected = false
            print("WebSocket disconnected: \(reason) with code: \(code)")
            delegate?.webSocketDidDisconnect(error: nil)
            attemptReconnect()
            
        case .text(let string):
            if let data = string.data(using: .utf8),
               let message = try? JSONDecoder().decode(SocketMessage.self, from: data) {
                delegate?.webSocketDidReceiveMessage(message)
            }
            
        case .binary(let data):
            if let message = try? JSONDecoder().decode(SocketMessage.self, from: data) {
                delegate?.webSocketDidReceiveMessage(message)
            }
            
        case .ping, .pong, .viabilityChanged, .reconnectSuggested, .cancelled, .peerClosed, .error:
            break
        }
    }
}

struct SocketMessage: Codable {
    let type: MessageType
    var senderId: String?
    var receiverId: String?
    var content: String?
    var timestamp: Date?
    
    enum MessageType: String, Codable {
        case auth
        case chat
        case typing
        case read
    }
}