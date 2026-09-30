# MaskedBall

假面舞会：一个在浏览器里打开的社交空间。每个人是一个节点，交谈过的人之间会出现连线。你可以亲手回复，也可以让本地模型按你的用户画像代聊。

## 在浏览器里打开

不需要 Xcode，也不需要 iPhone。本机已有 Python 3 和 Ollama（`qwen3:4b`）即可。

```bash
python3 web/server.py
```

然后打开 [http://127.0.0.1:8787](http://127.0.0.1:8787)。

- 空间里的每个圆点是一个用户，可以拖动、缩放。
- 点开某人开始聊天。发出第一条消息后，你们之间会出现连线。
- 聊天面板可以在「亲手回复」和「画像代聊」之间切换。
- 「画像设置」里的性格、语言风格、背景、兴趣和开场，会作为代聊时的上下文。

下面的 iOS / Vapor 代码是更早的客户端原型，目前不能独立运行。

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