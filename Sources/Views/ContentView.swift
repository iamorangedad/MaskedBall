import SwiftUI

struct ContentView: View {
    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Image(systemName: "bubble.left.and.bubble.right.fill")
                    .font(.system(size: 60))
                    .foregroundStyle(.purple)
                
                Text("MaskedBall")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                
                Text("AI Chatbot Social Platform")
                    .foregroundStyle(.secondary)
                
                NavigationLink(destination: BotConfigView()) {
                    Label("Configure Your Bot", systemImage: "person.crop.circle.badge.plus")
                }
                .buttonStyle(.borderedProminent)
                
                NavigationLink(destination: DiscoveryView()) {
                    Label("Discover Bots", systemImage: "magnifyingglass")
                }
                .buttonStyle(.bordered)
            }
            .padding()
        }
    }
}

#Preview {
    ContentView()
}