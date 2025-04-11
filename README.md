# GASPAR

**G**enAI-powered **S**ystem for **P**rivacy incident **A**nalysis and **R**ecovery

GASPAR is a comprehensive system designed to:
- Extract privacy-related fields from assessment documents
- Model data distributions and sample input data based on extracted fields
- Detect anomalous values in sampled data batches
- Create code filters to exclude anomalous data
- Safely deploy filters to quarantine problematic data

## Features

- Privacy rule extraction from IPA documents
- Adaptive data sampling based on distribution modeling
- Statistical and distribution-based anomaly detection
- Automatic filter generation for anomalous data
- Safe deployment with monitoring capabilities
- Support for multiple LLM providers (OpenAI, Anthropic, Mistral)
- Azure integration for cloud deployment

## Installation

Local installation can be done using [`uv`](https://github.com/astral-sh/uv):

```bash
$ uv python install 3.10
$ uv python pin 3.10
$ uv venv -p python3.10
$ source .venv/bin/activate
$ uv pip install -e .
```

For development mode:

```bash
$ pip install -e ".[dev]"
```

For Databricks deployment
```bash
pip install -e ".[databricks]"
```
## Usage

### Basic Usage

```python
from gaspar.config import load_config
from gaspar.pipeline.executor import PipelineExecutor
import asyncio

async def main():
    # Load configuration from file
    config = load_config("config.yaml")
    
    # Initialize pipeline
    executor = PipelineExecutor(config)
    
    # Process IPA document
    result = await executor.execute("documents/privacy_assessment.txt")
    
    if result.success:
        print("Privacy rules extracted successfully")
        print(f"Generated {len(result.outputs['filters'])} filters")

if __name__ == "__main__":
    asyncio.run(main())
```

### Command Line Usage

After installation, the `gaspar` command-line tool is available:

```bash
$ gaspar document.txt
# Process IPA document and start monitoring

$ gaspar -c config.yaml document.txt
# Use custom configuration

$ gaspar -v document.txt
# Enable verbose logging
```

## Configuration

GASPAR can be configured via YAML files. Example configuration:

```yaml
# LLM Model Configuration
model:
  provider: "openai"
  model_name: "gpt-4"
  api_key: ${OPENAI_API_KEY}

# Storage Configuration
storage:
  type: "local"
  local_path: "./data"

# Pipeline Configuration
pipeline:
  batch_size: 100
  max_retries: 3
  temp_directory: "./temp"
```
# Note
For the configuration to be used in the repo, it was adapted to use a locally deployed version of GPT-4
To use Openai API or any other LLM API provider, update openai_model.py or create a new one
## Development

### Testing

Running the tests can be done using [`tox`](https://tox.wiki/):

```bash
$ tox -p
```

### Building Packages

Building the packages:

```bash
$ tox -e packages
$ ls dist/
```

## License

MIT