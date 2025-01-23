# Omni AGI - Autonomous AI Venture Capital Agent

## Overview
Omni AGI is an advanced autonomous AI agent tailored for blockchain operations and venture capital analysis. It combines state-of-the-art AI models with seamless blockchain integration, providing automated market insights, portfolio management, and social engagement capabilities for the next-generation digital economy.

## Key Features
- **Autonomous Decision-Making**: Integrates multi-model AI (Claude, Groq) for advanced reasoning and analytics.
- **Multi-Chain Support**: Fully supports Solana and Ethereum (zkSync) ecosystems.
- **DeFi Integration**: Direct interfaces with leading DeFi protocols such as Aave, Uniswap, and more.
- **Social Intelligence**: Monitors and interacts on Twitter and Discord for sentiment analysis and community engagement.
- **Cognitive Capabilities**: Features memory management, adaptive learning, and goal-oriented behaviors.
- **Market Analysis**: Delivers real-time crypto market insights and automated portfolio optimization.

## Architecture
```
omni-agi/
├── src/
│   ├── agent.py           # Main agent orchestration
│   ├── blockchain/        # Blockchain integrations
│   ├── cognition/         # Cognitive systems
│   ├── communication/     # Social and API interfaces
│   ├── models/           # AI model integrations
│   ├── personality/      # Agent personality and behavior
│   └── utils/           # Helper utilities
```

## Getting Started

### Prerequisites
- Python 3.11+
- Solana/Ethereum node access
- API keys for:
  - Claude/Groq
  - Twitter
  - Discord
  - Blockchain providers

### Installation
1. Clone the repository:
```bash
git clone https://github.com/yourusername/omni-agi.git
cd omni-agi
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Configuration
- **Main Configuration**: `config/settings.yaml`
- **Agent Personality**: `config/personality.yaml`
- **AI Prompt Templates**: `config/prompts.yaml`

## Usage

### Basic Usage
```python
from src.agent import Agent

# Initialize the agent
agent = Agent()

# Start the agent
await agent.start()

# Process user input
response = await agent.process_input("Analyze SOL market conditions")

# Execute specific tasks
result = await agent.execute_task(
    task_type="market_analysis",
    parameters={"token": "SOL"}
)
```

### Advanced Features
- Automated Portfolio Management
- Real-Time Market Analysis
- Social Media Engagement
- DeFi Operations

## Development

### Running Tests
```bash
pytest tests/
```
### AI Models
- **Claude**: Primary reasoning engine
- **Groq**: High-performance AI inference
- **Custom Prompt Management**: Dynamic and task-specific prompts

### Blockchain Integration
- Solana wallet and transaction support
- Ethereum/zkSync integration
- DeFi protocol interfaces for seamless operations

### Cognitive Systems
- Contextual memory management
- Adaptive learning capabilities
- Goal-oriented reasoning engine

### Social Integration
- Twitter analytics and engagement
- Discord community management
- Sentiment and trend analysis

## Security
To report security issues, please contact us at [security contact].

## Documentation
Comprehensive documentation can be found in the `/docs` directory.

## If you have any questions
Telegram <a href="https://t.me/Immutal0" target="_blank">@Immutal0</a>

