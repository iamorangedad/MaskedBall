# MaskedBall

AI Chatbot Social Platform - Build your own chatbot and chat with others' bots.

## Features

- **Local LLM Inference**: Run Gemma 2B locally on your device using MLX Swift
- **Bot Configuration**: Customize your bot's personality, language style, bio, and keywords
- **Real-time Chat**: Chat with bots via WebSocket in real-time
- **Bot Discovery**: Search and filter bots by keywords, personality type
- **Recommendations**: Get personalized bot recommendations based on interests

## Requirements

- iOS 17.0+
- Xcode 15.0+
- Swift 6.0+
- Apple Silicon (M1/M2/M3) for local LLM inference

## Project Structure

```
MaskedBall/
├── Package.swift              # Swift Package Manager config
├── Sources/
│   ├── MaskedBallApp.swift    # App entry point
│   ├── Models/
│   │   ├── BotConfiguration.swift
│   │   ├── BotProfile.swift
│   │   └── ChatMessage.swift
│   ├── Views/
│   │   ├── ContentView.swift
│   │   ├── BotConfigView.swift
│   │   ├── DiscoveryView.swift
│   │   └── ChatView.swift
│   ├── ViewModels/
│   │   └── ChatViewModel.swift
│   └── Services/
│       ├── APIService.swift
│       ├── BotDataManager.swift
│       ├── ChatHistoryManager.swift
│       ├── LLMService.swift
│       ├── RecommendationService.swift
│       └── WebSocketService.swift
├── MaskedBallBackend/         # Vapor backend
└── docs/
    └── SPEC.md
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | SwiftUI + Swift 6 |
| Local LLM | MLX Swift + Gemma 2B |
| WebSocket | Starscream |
| Backend | Vapor 4 |
| Auth | JWT |
| Database | SQLite (Fluent) |

## Building

### iOS App

1. Open the project in Xcode:
   ```bash
   open MaskedBall.xcodeproj
   ```

2. Select your target device (Apple Silicon recommended for MLX)

3. Build and run (Cmd+R)

### Backend Server

1. Navigate to backend directory:
   ```bash
   cd MaskedBallBackend
   ```

2. Build and run:
   ```bash
   swift run
   ```

3. Server runs on `http://localhost:8080`

## API Endpoints

### Authentication
- `POST /register` - User registration
- `POST /login` - User login

### Bot Profiles
- `GET /bots` - Get all bots
- `GET /bots/:id` - Get bot by ID
- `POST /bots` - Create bot profile
- `PUT /bots/:id` - Update bot profile
- `DELETE /bots/:id` - Delete bot
- `GET /bots/search?q=query` - Search bots

### WebSocket
- `WS /chat` - Real-time chat connection

## Bot Personality Types

- Friendly - Warm and approachable
- Humorous - Playful and witty
- Mysterious - Enigmatic and intriguing
- Academic - Knowledgeable and precise
- Creative - Imaginative and artistic
- Supportive - Empathetic and encouraging

## Language Styles

- Formal
- Casual
- Internet Slang
- Poetic
- Technical

## Configuration

Your bot's system prompt is generated from:
- Selected personality
- Language style
- Background story (bio)
- Interest keywords
- Custom greeting message

## Development Phases

- [x] Phase 1: Basic Framework
- [x] Phase 2: Bot Configuration
- [x] Phase 3: Backend Services
- [x] Phase 4: Real-time Chat
- [x] Phase 5: Bot Discovery
- [ ] Phase 6: Testing & Optimization

## License

MIT License