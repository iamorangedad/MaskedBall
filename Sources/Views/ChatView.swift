import SwiftUI

struct ChatView: View {
    let bot: BotProfile
    @State private var messages: [ChatMessage] = []
    @State private var inputText = ""
    @State private var isLoading = false
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(messages) { message in
                            ChatBubbleView(message: message)
                                .id(message.id)
                        }
                        
                        if isLoading {
                            HStack(spacing: 8) {
                                ProgressView()
                                Text("Thinking...")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(.horizontal)
                        }
                    }
                    .padding()
                }
                .onChange(of: messages.count) { _, _ in
                    if let last = messages.last {
                        withAnimation {
                            proxy.scrollTo(last.id, anchor: .bottom)
                        }
                    }
                }
            }
            
            Divider()
            
            ChatInputView(text: $inputText, isLoading: isLoading) {
                sendMessage()
            }
        }
        .navigationTitle(bot.name)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button(action: { showBotInfo() }) {
                    Image(systemName: "info.circle")
                }
            }
        }
        .onAppear {
            loadGreeting()
        }
    }
    
    private func loadGreeting() {
        messages.append(ChatMessage(
            content: bot.greeting,
            sender: .bot(bot.id),
            timestamp: Date()
        ))
    }
    
    private func sendMessage() {
        guard !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        
        let userMessage = ChatMessage(
            content: inputText,
            sender: .user,
            timestamp: Date()
        )
        messages.append(userMessage)
        
        inputText = ""
        isLoading = true
        
        Task {
            try? await Task.sleep(nanoseconds: 1_500_000_000)
            
            let response = generateBotResponse(to: userMessage.content)
            
            await MainActor.run {
                messages.append(ChatMessage(
                    content: response,
                    sender: .bot(bot.id),
                    timestamp: Date()
                ))
                isLoading = false
            }
        }
    }
    
    private func generateBotResponse(to input: String) -> String {
        let lowercaseInput = input.lowercased()
        
        switch bot.personality {
        case .friendly:
            if lowercaseInput.contains("help") {
                return "Of course! I'm happy to help you with anything I can. What do you need?"
            }
            return "That's interesting! Tell me more about that. I'm always eager to learn and chat!"
            
        case .humorous:
            return "Ha! That's a good one! 😄 You really know how to keep things fun!"
            
        case .mysterious:
            return "The shadows whisper of your curiosity... But perhaps some things are better left unsaid."
            
        case .academic:
            return "That's a fascinating topic. Let me share some insights based on my knowledge..."
            
        case .creative:
            return "Your words paint such interesting pictures! Let me create something in response..."
            
        case .supportive:
            return "I hear you. It's okay to feel that way. I'm here for you. 💙"
        }
    }
    
    private func showBotInfo() {
        // Show bot profile info sheet
    }
}

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

struct ChatBubbleView: View {
    let message: ChatMessage
    
    var body: some View {
        HStack {
            if message.isFromBot {
                Circle()
                    .fill(Color.purple.opacity(0.3))
                    .frame(width: 32, height: 32)
                    .overlay(
                        Image(systemName: "robot")
                            .font(.caption)
                    )
            }
            
            VStack(alignment: message.isFromBot ? .leading : .trailing, spacing: 4) {
                Text(message.content)
                    .padding(12)
                    .background(
                        message.isFromBot ? Color.gray.opacity(0.1) : Color.purple.opacity(0.2)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                
                Text(message.timestamp, style: .time)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            
            if !message.isFromBot {
                Circle()
                    .fill(Color.blue.opacity(0.3))
                    .frame(width: 32, height: 32)
                    .overlay(
                        Image(systemName: "person.fill")
                            .font(.caption)
                    )
            }
        }
        .frame(maxWidth: .infinity, alignment: message.isFromBot ? .leading : .trailing)
    }
}

struct ChatInputView: View {
    @Binding var text: String
    let isLoading: Bool
    let onSend: () -> Void
    
    var body: some View {
        HStack(spacing: 12) {
            TextField("Type a message...", text: $text)
                .textFieldStyle(.roundedBorder)
                .disabled(isLoading)
                .onSubmit {
                    if !isLoading { onSend() }
                }
            
            Button(action: onSend) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.title2)
                    .foregroundStyle(text.isEmpty || isLoading ? .gray : .purple)
            }
            .disabled(text.isEmpty || isLoading)
        }
        .padding()
    }
}

#Preview {
    NavigationStack {
        ChatView(bot: BotProfile(
            name: "Test Bot",
            personality: .friendly,
            bio: "A friendly test bot"
        ))
    }
}