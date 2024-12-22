# AI Shell Agent

An interactive AI shell agent with a web interface that can help with commands and general queries. The agent runs in a Docker container and provides a secure, terminal-like interface.

## Features

- Web-based terminal interface
- Secure API key handling
- Command execution capabilities
- Real-time AI responses
- Docker containerization
- Modern, user-friendly UI

## Prerequisites

- Docker
- Docker Compose
- OpenAI API key

## Usage

After entering your API key, you can:
- Type messages or questions
- Execute allowed commands (ls, pwd, echo, cat, grep, date, whoami, df, ps)
- Get AI-powered responses

## Troubleshooting

1. **Port Conflicts**: If ports 5000/8080 are in use, modify them in docker-compose.yml
2. **API Key Issues**: Ensure your OpenAI API key is valid and has credits
3. **Container Issues**: Run `docker-compose down` then `docker-compose up --build`

## Security

- API keys are stored in memory only
- Commands run in isolated container
- Only whitelisted commands allowed
- Local Docker network communication only