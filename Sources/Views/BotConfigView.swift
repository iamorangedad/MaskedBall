import SwiftUI

struct BotConfigView: View {
    @State private var config = BotConfiguration()
    @State private var showPreview = false
    
    var body: some View {
        Form {
            Section("Basic Info") {
                TextField("Bot Name", text: $config.name)
                
                TextField("Greeting Message", text: $config.greeting)
            }
            
            Section("Personality") {
                Picker("Personality", selection: $config.personality) {
                    ForEach(BotPersonality.allCases) { personality in
                        VStack(alignment: .leading) {
                            Text(personality.rawValue)
                            Text(personality.description)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .tag(personality)
                    }
                }
            }
            
            Section("Language Style") {
                Picker("Style", selection: $config.languageStyle) {
                    ForEach(BotLanguageStyle.allCases) { style in
                        Text(style.rawValue).tag(style)
                    }
                }
            }
            
            Section("Background Story") {
                TextEditor(text: $config.bio)
                    .frame(minHeight: 100)
            }
            
            Section("Interest Keywords") {
                KeywordsEditor(keywords: $config.keywords)
            }
            
            Section {
                Button("Preview Prompt") {
                    showPreview = true
                }
            }
        }
        .navigationTitle("Configure Bot")
        .sheet(isPresented: $showPreview) {
            PromptPreviewView(prompt: config.generateSystemPrompt())
        }
    }
}

struct KeywordsEditor: View {
    @Binding var keywords: [String]
    @State private var newKeyword = ""
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            FlowLayout(spacing: 8) {
                ForEach(keywords, id: \.self) { keyword in
                    KeywordTag(keyword: keyword) {
                        keywords.removeAll { $0 == keyword }
                    }
                }
            }
            
            HStack {
                TextField("Add keyword", text: $newKeyword)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        addKeyword()
                    }
                
                Button(action: addKeyword) {
                    Image(systemName: "plus.circle.fill")
                }
                .disabled(newKeyword.isEmpty)
            }
        }
    }
    
    private func addKeyword() {
        let trimmed = newKeyword.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty && !keywords.contains(trimmed) {
            keywords.append(trimmed)
            newKeyword = ""
        }
    }
}

struct KeywordTag: View {
    let keyword: String
    let onRemove: () -> Void
    
    var body: some View {
        HStack(spacing: 4) {
            Text(keyword)
                .font(.caption)
            
            Button(action: onRemove) {
                Image(systemName: "xmark.circle.fill")
                    .font(.caption)
            }
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Color.purple.opacity(0.2))
        .clipShape(Capsule())
    }
}

struct FlowLayout: Layout {
    var spacing: CGFloat = 8
    
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = FlowResult(in: proposal.replacingUnspecifiedDimensions().width, subviews: subviews, spacing: spacing)
        return result.size
    }
    
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = FlowResult(in: bounds.width, subviews: subviews, spacing: spacing)
        for (index, subview) in subviews.enumerated() {
            subview.place(at: CGPoint(x: bounds.minX + result.positions[index].x, y: bounds.minY + result.positions[index].y), proposal: .unspecified)
        }
    }
    
    struct FlowResult {
        var size: CGSize = .zero
        var positions: [CGPoint] = []
        
        init(in width: CGFloat, subviews: Subviews, spacing: CGFloat) {
            var x: CGFloat = 0
            var y: CGFloat = 0
            var rowHeight: CGFloat = 0
            
            for subview in subviews {
                let size = subview.sizeThatFits(.unspecified)
                
                if x + size.width > width && x > 0 {
                    x = 0
                    y += rowHeight + spacing
                    rowHeight = 0
                }
                
                positions.append(CGPoint(x: x, y: y))
                rowHeight = max(rowHeight, size.height)
                x += size.width + spacing
            }
            
            self.size = CGSize(width: width, height: y + rowHeight)
        }
    }
}

struct PromptPreviewView: View {
    let prompt: String
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            ScrollView {
                Text(prompt)
                    .font(.system(.body, design: .monospaced))
                    .padding()
            }
            .navigationTitle("System Prompt")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
                
                ToolbarItem(placement: .primaryAction) {
                    Button("Copy") {
                        UIPasteboard.general.string = prompt
                    }
                }
            }
        }
    }
}

#Preview {
    NavigationStack {
        BotConfigView()
    }
}