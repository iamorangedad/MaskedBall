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

## Project Structure

```
MaskedBall/
├── web/                  # Browser client and local server
└── docs/
    └── SPEC.md
```

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