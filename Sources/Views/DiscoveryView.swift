import SwiftUI

struct DiscoveryView: View {
    @State private var searchText = ""
    @State private var selectedPersonality: BotPersonality?
    @State private var bots: [BotProfile] = []
    @State private var isLoading = false
    
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
            loadSampleBots()
        }
    }
    
    private func loadSampleBots() {
        bots = [
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

struct FilterChip: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.caption)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(isSelected ? Color.purple : Color.gray.opacity(0.2))
                .foregroundStyle(isSelected ? .white : .primary)
                .clipShape(Capsule())
        }
    }
}

struct BotCardView: View {
    let bot: BotProfile
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(bot.name)
                    .font(.headline)
                
                Spacer()
                
                Text(bot.personality.rawValue)
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.purple.opacity(0.2))
                    .clipShape(Capsule())
            }
            
            if !bot.bio.isEmpty {
                Text(bot.bio)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
            
            if !bot.keywords.isEmpty {
                HStack(spacing: 4) {
                    ForEach(bot.keywords.prefix(3), id: \.self) { keyword in
                        Text("#\(keyword)")
                            .font(.caption2)
                            .foregroundStyle(.blue)
                    }
                }
            }
            
            HStack {
                Label("\(bot.viewCount)", systemImage: "eye")
                Spacer()
                Label("\(bot.chatCount)", systemImage: "bubble.left")
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    NavigationStack {
        DiscoveryView()
    }
}