# Model Provider Layer v0.1

## Purpose

Provide a single model interface for AIDPL agents without coupling the
pipeline to one vendor.

## Providers

- `mock`
- `openai`
- `deepseek`
- `qwen`

Anthropic is reserved for v0.2.

## Commands

```bash
./bin/aidpl-provider doctor
```

```bash
./bin/aidpl-provider smoke --provider mock
```

Live smoke tests require the corresponding environment variable.

## Security Rules

- API keys are read only from environment variables.
- API keys are never written to manifests, reports or Git.
- `.env.example` contains names only, never secrets.
- Live inference remains disabled in the example routing configuration.
- Every live response should preserve provider, model, usage and request ID.

## Protocols

- OpenAI uses the Responses API.
- DeepSeek uses its OpenAI-compatible chat-completions endpoint.
- Qwen uses Alibaba Cloud Model Studio's OpenAI-compatible endpoint.

## Next Integration

The first consumer will be the model-assisted `LK-EXTRACT` reviewer.
