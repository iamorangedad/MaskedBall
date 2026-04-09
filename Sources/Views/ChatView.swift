import SwiftUI

struct ChatView: View {
    let bot: BotProfile
    @StateObject private var viewModel = ChatViewModel()
    @State private var inputText = ""
    
    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(viewModel.messages) { message in
                            ChatBubbleView(message: message)
                                .id(message.id)
                        }
                        
                        if viewModel.isLoading {
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
                .onChange(of: viewModel.messages.count) { _, _ in
                    if let last = viewModel.messages.last {
                        withAnimation {
                            proxy.scrollTo(last.id, anchor: .bottom)
                        }
                    }
                }
            }
            
            Divider()
            
            ChatInputView(text: $inputText, isLoading: viewModel.isLoading) {
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
            viewModel.configure(with: bot)
            viewModel.loadGreeting()
        }
    }
    
    private func sendMessage() {
        guard !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        
        viewModel.sendMessage(inputText)
        inputText = ""
    }
    
    private func showBotInfo() {
    }
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