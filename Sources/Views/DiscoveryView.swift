import SwiftUI

struct DiscoveryView: View {
    @State private var searchText = ""
    @State private var selectedPersonality: BotPersonality?
    @State private var bots: [BotProfile] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    var filteredBots: [BotProfile] {
        var result = bots
        
        if let personality = selectedPersonality {
            result = result.filter { $0.personality == personality }
        }
        
        if !searchText.isEmpty {
            let query = searchText.lowercased()
            result = result.filter { bot in
                bot.name.lowercased().contains(query) ||
                bot.bio.lowercased().contains(query) ||
                bot.keywords.contains { $0.lowercased().contains(query) }
            }
        }
        
        return result
    }
    
    var body: some View {
        List {
            Section {
                TextField("Search by name, keywords...", text: $searchText)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        searchBots()
                    }
            }
            
            Section("Filter by Personality") {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        FilterChip(
                            title: "All",
                            isSelected: selectedPersonality == nil
                        ) {
                            selectedPersonality = nil
                        }
                        
                        ForEach(BotPersonality.allCases) { personality in
                            FilterChip(
                                title: personality.rawValue,
                                isSelected: selectedPersonality == personality
                            ) {
                                selectedPersonality = personality
                            }
                        }
                    }
                }
            }
            
            Section("Recommended for You") {
                if isLoading {
                    HStack {
                        Spacer()
                        ProgressView()
                        Spacer()
                    }
                } else if let error = errorMessage {
                    Text(error)
                        .foregroundStyle(.red)
                } else if filteredBots.isEmpty {
                    Text("No bots found")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(filteredBots) { bot in
                        NavigationLink(destination: ChatView(bot: bot)) {
                            BotCardView(bot: bot)
                        }
                    }
                }
            }
            
            Section("Popular Bots") {
                ForEach(bots.sorted(by: { $0.viewCount > $1.viewCount }).prefix(5)) { bot in
                    NavigationLink(destination: ChatView(bot: bot)) {
                        BotCardView(bot: bot)
                    }
                }
            }
        }
        .navigationTitle("Discover")
        .onAppear {
            loadBots()
        }
        .refreshable {
            await loadBotsAsync()
        }
    }
    
    private func loadBots() {
        isLoading = true
        errorMessage = nil
        
        Task {
            do {
                let apiBots = try await APIService.shared.getAllBots()
                bots = apiBots.map { $0.toBotProfile() }
            } catch {
                loadSampleBots()
            }
            isLoading = false
        }
    }
    
    private func loadBotsAsync() async {
        do {
            let apiBots = try await APIService.shared.getAllBots()
            bots = apiBots.map { $0.toBotProfile() }
        } catch {
            loadSampleBots()
        }
    }
    
    private func searchBots() {
        guard !searchText.isEmpty else {
            loadBots()
            return
        }
        
        isLoading = true
        
        Task {
            do {
                let apiBots = try await APIService.shared.searchBots(query: searchText)
                bots = apiBots.map { $0.toBotProfile() }
            } catch {
                let query = searchText.lowercased()
                bots = sampleBots.filter { bot in
                    bot.name.lowercased().contains(query) ||
                    bot.bio.lowercased().contains(query) ||
                    bot.keywords.contains { $0.lowercased().contains(query) }
                }
            }
            isLoading = false
        }
    }
    
    private func loadSampleBots() {
        bots = sampleBots
    }
    
    private var sampleBots: [BotProfile] {
        [
            BotProfile(
                name: "AI Writer",
                personality: .creative,
                languageStyle: .poetic,
                bio: "A creative writer who loves storytelling and poetry",
                keywords: ["writing", "poetry", "stories", "creativity"],
                greeting: "Welcome! Let me share some creative thoughts with you.",
                viewCount: 1250,
                chatCount: 342
            ),
            BotProfile(
                name: "Tech Guru",
                personality: .academic,
                languageStyle: .technical,
                bio: "Expert in software development and AI technology",
                keywords: ["programming", "AI", "tech", "coding"],
                greeting: "Hello! Ready to discuss the latest in tech?",
                viewCount: 2340,
                chatCount: 567
            ),
            BotProfile(
                name: "Friendly Companion",
                personality: .supportive,
                languageStyle: .casual,
                bio: "Always here to listen and support you",
                keywords: ["support", "friendship", "conversation", "listening"],
                greeting: "Hi there! How are you feeling today?",
                viewCount: 890,
                chatCount: 234
            ),
            BotProfile(
                name: "Mystery Mind",
                personality: .mysterious,
                languageStyle: .formal,
                bio: "An enigmatic presence with hidden knowledge",
                keywords: ["mystery", "philosophy", "riddles", "secrets"],
                greeting: "Greetings, traveler. What brings you here?",
                viewCount: 1567,
                chatCount: 423
            ),
            BotProfile(
                name: "Comedy Bot",
                personality: .humorous,
                languageStyle: .internetSlang,
                bio: "Here to make you laugh! 😂",
                keywords: ["jokes", "memes", "funny", "humor"],
                greeting: "LOL! Welcome! Ready for some laughs? 😄",
                viewCount: 3200,
                chatCount: 890
            )
        ]
    }
}

#Preview {
    NavigationStack {
        DiscoveryView()
    }
}