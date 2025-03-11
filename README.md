# AI-Powered Autonomous Agent Framework

An intelligent agent framework that runs in dedicated Ubuntu VMs and performs complex tasks autonomously using natural language instructions, powered by large language models like GPT-4 and Claude.

## Architecture Overview

This autonomous agent framework is designed with a scalable, secure architecture:

- **VM-per-session model**: Each user session runs in a dedicated Ubuntu VM, providing isolation and security
- **Central orchestration server**: Manages VM provisioning, monitoring, and lifecycle
- **Web-based frontend**: Intuitive interface for users to interact with their agent and monitor task progress
- **LLM integration**: Powered by GPT-4, Claude, or other LLMs to enable natural language processing and planning

The agent itself can:
- Execute complex multi-step tasks based on natural language instructions
- Utilize both terminal commands and web browser automation
- Dynamically plan and adapt to changing circumstances
- Self-verify and refine its outputs

## Project Structure

```
src/
  ├── agent/       # Core agent logic, planning, and execution loop
  ├── models/      # LLM integration and prompt engineering
  ├── execution/   # Command execution and browser automation
  ├── server/      # Backend API server and VM orchestration
  ├── ui/          # Web interface for users
  ├── vm/          # VM provisioning and management
tests/             # Test cases and fixtures
```

## System Components

### VM Agent
The agent runs inside an Ubuntu VM and includes:
- Planning and execution engine
- Terminal command executor (with security restrictions)
- Browser automation capabilities
- Self-verification mechanisms

### Orchestration Backend
The central server handles:
- User authentication and session management
- VM provisioning and configuration
- Task queuing and status tracking
- LLM API management

### Web Frontend
The user interface provides:
- Natural language input for tasks
- Real-time task progress monitoring
- Plan visualization and execution logs
- Session management

## Getting Started

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (for local development)
- Kubernetes (for production deployment)
- Cloud provider account (AWS/GCP/Azure) for VM deployment

### Development Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/ai-agent-framework.git
cd ai-agent-framework
```

2. Install Python dependencies
```bash
pip install -r requirements.txt
```

3. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. Run the development server
```bash
python -m src.server.main
```

5. For local VM testing, use Docker to simulate VM environments:
```bash
docker-compose up -d
```

## Development Roadmap

This project follows the phased development approach:

- **Phase 1 (Current)**: MVP with basic planning and execution capabilities in a single VM
- **Phase 2**: Enhanced robustness, dynamic re-planning, and improved VM orchestration
- **Phase 3**: Improved UI, scalable VM provisioning, and user management
- **Phase 4**: Production-ready features, security hardening, and enterprise capabilities

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.