import Foundation
import MLX
import MLXLLM
import MLXLMCommon

@MainActor
class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private var botProfile: BotProfile?
    private var modelContainer: ModelContainer?
    private var isModelLoaded = false
    
    func configure(with bot: BotProfile) {
        self.botProfile = bot
    }
    
    func loadGreeting() {
        guard let bot = botProfile else { return }
        
        messages.append(ChatMessage(
            content: bot.greeting,
            sender: .bot(bot.id),
            timestamp: Date()
        ))
    }
    
    func sendMessage(_ content: String) {
        guard let bot = botProfile else { return }
        
        let userMessage = ChatMessage(
            content: content,
            sender: .user,
            timestamp: Date()
        )
        messages.append(userMessage)
        
        isLoading = true
        
        Task {
            do {
                try await loadModelIfNeeded()
                
                guard let botConfig = createBotConfiguration(from: bot) else {
                    throw ChatError.configurationMissing
                }
                
                let response = await generateResponse(userMessage: content, botConfig: botConfig)
                
                messages.append(ChatMessage(
                    content: response,
                    sender: .bot(bot.id),
                    timestamp: Date()
                ))
            } catch {
                let fallbackResponse = generateFallbackResponse(to: content, personality: bot.personality)
                messages.append(ChatMessage(
                    content: fallbackResponse,
                    sender: .bot(bot.id),
                    timestamp: Date()
                ))
            }
            
            isLoading = false
        }
    }
    
    private func loadModelIfNeeded() async throws {
        guard !isModelLoaded else { return }
        
        let modelId = "mlx-community/gemma-2b-it-4bit"
        
        do {
            modelContainer = try await LLMModelFactory.shared.loadContainer(
                from: HubClient.default,
                configuration: .configuration(id: modelId)
            )
            isModelLoaded = true
        } catch {
            throw ChatError.modelLoadFailed(error.localizedDescription)
        }
    }
    
    private func createBotConfiguration(from bot: BotProfile) -> BotConfiguration? {
        BotConfiguration(
            name: bot.name,
            personality: bot.personality,
            languageStyle: bot.languageStyle,
            bio: bot.bio,
            keywords: bot.keywords,
            greeting: bot.greeting
        )
    }
    
    private func generateResponse(userMessage: String, botConfig: BotConfiguration) async -> String {
        guard let modelContainer = modelContainer else {
            return generateFallbackResponse(to: userMessage, personality: botConfig.personality)
        }
        
        do {
            let systemPrompt = botConfig.generateSystemPrompt()
            let input = "<start_of_turn>model\n\(systemPrompt)<end_of_turn><start_of_turn>user\n\(userMessage)<end_of_turn><start_of_turn>model\n"
            
            let parameters = GenerateParameters(
                temperature: 0.7,
                maxTokens: 128,
                repetitionPenalty: 1.1
            )
            
            let tokenizer = try await TokenizersLoader().load(for: modelContainer)
            let model = try await LLMModel(modelContainer: modelContainer)
            
            var fullResponse = ""
            
            for try await token in try await model.generate(input: input, parameters: parameters) {
                let output = tokenizer.decode(tokenIds: [token])
                fullResponse += output
                
                if output.contains("<end_of_turn>") {
                    break
                }
            }
            
            return fullResponse.trimmingCharacters(in: .whitespacesAndNewlines)
                .replacingOccurrences(of: "<end_of_turn>", with: "")
                .replacingOccurrences(of: "<start_of_turn>", with: "")
        } catch {
            return generateFallbackResponse(to: userMessage, personality: botConfig.personality)
        }
    }
    
    private func generateFallbackResponse(to input: String, personality: BotPersonality) -> String {
        let lowercaseInput = input.lowercased()
        
        switch personality {
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
    
    enum ChatError: Error, LocalizedError {
        case modelLoadFailed(String)
        case configurationMissing
        
        var errorDescription: String? {
            switch self {
            case .modelLoadFailed(let message):
                return "Model load failed: \(message)"
            case .configurationMissing:
                return "Bot configuration is missing"
            }
        }
    }
}