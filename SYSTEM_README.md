# Full-Self-Crawl System

A distributed intelligent web crawling system composed of an Orchestrator and multiple Agents.

## Overview

The Full-Self-Crawl System is a sophisticated web data extraction platform designed for autonomous web crawling tasks. The system follows a modular architecture with a central orchestrator coordinating multiple autonomous agents.

## Architecture

### Components

1. **Orchestrator** - Central coordinator that manages task distribution, schedules agents, monitors progress, and aggregates results
2. **Agents** - Autonomous crawlers that perform actual data extraction tasks using a 7-step process

### Communication Flow

```
User Request → Orchestrator → Agent (via subprocess/Docker/mock) → Target Websites
Target Websites → Agent → Orchestrator → User Results
```

## Prerequisites

- Python 3.8+
- Docker (for Docker mode)
- Access to LLM API (Anthropic/OpenAI/other supported providers)
- Redis server (for progress monitoring)

## Installation

### 1. Clone both repositories:

```bash
git clone https://github.com/YOUR_USERNAME/full-self-crawl-orchestrator.git
git clone https://github.com/YOUR_USERNAME/full-self-crawl-agent.git
```

### 2. Install dependencies for Orchestrator:

```bash
cd full-self-crawl-orchestrator
pip install -r requirements.txt
```

### 3. Install dependencies for Agent:

```bash
cd full-self-crawl-agent
pip install -r requirements.txt
```

### 4. Configure environment variables:

Create `.env` files in both repositories with appropriate API keys and settings.

## Usage

### Running the Orchestrator

```bash
cd full-self-crawl-orchestrator
python -c "
import asyncio
from src.orchestrator.orchestrator import Orchestrator

async def main():
    orchestrator = Orchestrator()
    result = await orchestrator.run_research('Find HTML format PPTs on codepen.io')
    print(result)

asyncio.run(main())
"
```

### Running an Agent independently

```bash
cd ../full-self-crawl-agent
python -m src.main specs/example_task.yaml
```

## Configuration

### Orchestrator Configuration

The orchestrator can be configured to run agents in different modes:

- **Subprocess mode**: Agents run as child processes (development)
- **Docker mode**: Agents run in isolated containers (production)
- **Mock mode**: Simulated agent responses (testing)

### Agent Capabilities

Each agent implements a 7-step process:

1. **Sense**: Perceive page structure and features
2. **Plan**: Plan data extraction strategy
3. **Act**: Execute data extraction operations
4. **Verify**: Verify data quality
5. **Gate**: Check if completion conditions are met
6. **Judge**: Decide subsequent actions
7. **Reflect**: Optimize strategy

## Deployment Modes

### Development Mode
- Use subprocess mode for easy debugging
- Run orchestrator and agents on the same machine
- Ideal for development and testing

### Production Mode
- Use Docker mode for containerized execution
- Deploy orchestrator and agents separately
- Leverage resource isolation and scalability

## Troubleshooting

### Common Issues

1. **Docker module not found**: Install docker with `pip install docker`
2. **Redis connection errors**: Ensure Redis server is running
3. **LLM API errors**: Check API key configuration in `.env` files

### Verifying Installation

Test that both components can communicate:

```bash
# From the orchestrator directory
python -c "from src.orchestrator.orchestrator import Orchestrator; print('Import successful')"
```

## Contributing

1. Fork both repositories
2. Create feature branches
3. Submit pull requests to the respective repositories

## License

MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the respective GitHub repositories.