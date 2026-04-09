import Vapor

final class ChatWebSocketController: WebSocketController {
    var app: Application?
    
    func configure(_ app: Application) {
        self.app = app
        
        app.webSocket("chat") { req, ws in
            self.handleConnection(req: req, ws: ws)
        }
    }
    
    private func handleConnection(req: Request, ws: WebSocket) {
        var authenticatedUserId: String?
        
        ws.on { [weak self] event in
            switch event {
            case .text(let text):
                self?.handleMessage(text: text, ws: ws, userId: authenticatedUserId)
                
            case .binary(let data):
                if let text = String(data: data, encoding: .utf8) {
                    self?.handleMessage(text: text, ws: ws, userId: authenticatedUserId)
                }
                
            case .ping:
                ws.pong()
                
            case .close:
                self?.handleDisconnect(ws: ws)
                
            case .viabilityChanged(let viable):
                if !viable {
                    ws.close(code: .goingAway)
                }
                
            case .textCompressed, .binaryCompressed:
                break
                
            case .cancelled:
                self?.handleDisconnect(ws: ws)
            }
        }
    }
    
    private func handleMessage(text: String, ws: WebSocket, userId: String?) {
        guard let data = text.data(using: .utf8),
              let message = try? JSONDecoder().decode(WebSocketMessage.self, from: data) else {
            return
        }
        
        switch message.type {
        case .auth:
            authenticatedUserId = message.payload
            
        case .chat:
            handleChatMessage(message: message, ws: ws)
            
        case .typing:
            handleTypingIndicator(message: message, ws: ws)
            
        case .read:
            handleReadReceipt(message: message)
        }
    }
    
    private func handleChatMessage(message: WebSocketMessage, ws: WebSocket) {
        guard let content = message.content,
              let senderId = message.senderId,
              let receiverId = message.receiverId else {
            return
        }
        
        let response = WebSocketMessage(
            type: .chat,
            senderId: senderId,
            receiverId: receiverId,
            content: content,
            timestamp: Date()
        )
        
        if let data = try? JSONEncoder().encode(response),
           let text = String(data: data, encoding: .utf8) {
            ws.send(text)
        }
    }
    
    private func handleTypingIndicator(message: WebSocketMessage, ws: WebSocket) {
    }
    
    private func handleReadReceipt(message: WebSocketMessage) {
    }
    
    private func handleDisconnect(ws: WebSocket) {
    }
}

struct WebSocketMessage: Codable {
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

extension WebSocketController: RouteCollecting {
    func collectRoutes(_ routes: RoutesBuilder) {
        routes.get("chat", use: { req, ws in
            // WebSocket upgrade handled by WebSocketController
        })
    }
}