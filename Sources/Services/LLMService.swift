import Foundation
import MLX
import MLXLLM
import MLXLMCommon

actor LLMService {
    static let shared = LLMService()
    
    private var modelContainer: ModelContainer?
    private var tokenizer: any Tokenizer
    private var isLoaded = false
    
    private init() {}
    
    enum LLMError: Error, LocalizedError {
        case notLoaded
        case modelLoadFailed(String)
        case generationFailed(String)
        
        var errorDescription: String? {
            switch self {
            case .notLoaded:
                return "LLM model not loaded"
            case .modelLoadFailed(let message):
                return "Failed to load model: \(message)"
            case .generationFailed(let message):
                return "Generation failed: \(message)"
            }
        }
    }
    
    func loadModel(
        from directory: URL? = nil,
        modelId: String = "mlx-community/gemma-2b-it-4bit"
    ) async throws {
        guard !isLoaded else { return }
        
        do {
            if let directory = directory {
                modelContainer = try await loadModelContainer(from: directory)
            } else {
                modelContainer = try await LLMModelFactory.shared.loadContainer(
                    from: HubClient.default,
                    configuration: .configuration(id: modelId)
                )
            }
            
            tokenizer = try await TokenizersLoader().load(for: modelContainer!)
            isLoaded = true
        } catch {
            throw LLMError.modelLoadFailed(error.localizedDescription)
        }
    }
    
    func unloadModel() {
        modelContainer = nil
        isLoaded = false
    }
    
    func generate(
        prompt: String,
        systemPrompt: String? = nil,
        maxTokens: Int = 256,
        temperature: Float = 0.7
    ) -> AsyncThrowingStream<String, Error> {
        AsyncThrowingStream { continuation in
            Task {
                guard let modelContainer = self.modelContainer else {
                    continuation.finish(throwing: LLMError.notLoaded)
                    return
                }
                
                do {
                    let input: String
                    if let systemPrompt = systemPrompt {
                        input = "<start_of_turn>model\n\(systemPrompt)<end_of_turn><start_of_turn>user\n\(prompt)<end_of_turn><start_of_turn>model\n"
                    } else {
                        input = "<start_of_turn>user\n\(prompt)<end_of_turn><start_of_turn>model\n"
                    }
                    
                    let parameters = GenerateParameters(
                        temperature: temperature,
                        maxTokens: maxTokens,
                        repetitionPenalty: 1.1
                    )
                    
                    let tokenizer = try await TokenizersLoader().load(for: modelContainer)
                    let mlxModel = try await LLMModel(modelContainer: modelContainer)
                    
                    var generatedTokens = [Int]()
                    
                    for try await token in try await mlxModel.generate(input: input, parameters: parameters) {
                        let output = tokenizer.decode(tokenIds: [token])
                        generatedTokens.append(token)
                        
                        if output.contains("<end_of_turn>") {
                            break
                        }
                        
                        continuation.yield(output)
                        
                        if generatedTokens.count >= maxTokens {
                            break
                        }
                    }
                    
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: LLMError.generationFailed(error.localizedDescription))
                }
            }
        }
    }
    
    func generateWithConfiguration(
        prompt: String,
        botConfig: BotConfiguration
    ) -> AsyncThrowingStream<String, Error> {
        let systemPrompt = botConfig.generateSystemPrompt()
        return generate(
            prompt: prompt,
            systemPrompt: systemPrompt
        )
    }
}

struct LLMGenerationOptions {
    var maxTokens: Int = 256
    var temperature: Float = 0.7
    var repetitionPenalty: Float = 1.1
}

@MainActor
class LLMServiceProxy: ObservableObject {
    @Published var isLoading = false
    @Published var isModelLoaded = false
    @Published var errorMessage: String?
    @Published var currentResponse = ""
    
    private var llmService = LLMService.shared
    
    func loadModel() async {
        isLoading = true
        errorMessage = nil
        
        do {
            try await llmService.loadModel()
            isModelLoaded = true
        } catch {
            errorMessage = error.localizedDescription
        }
        
        isLoading = false
    }
    
    func generateResponse(prompt: String, botConfig: BotConfiguration) -> AsyncThrowingStream<String, Error> {
        return llmService.generateWithConfiguration(prompt: prompt, botConfig: botConfig)
    }
}