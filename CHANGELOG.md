# Changelog

## [0.3.0] - 2025-10
### Added
- Async runner for parallel case execution (`aek.async_runner`)
- `answer_is_valid_json` check with optional schema
- Compose / multi-step example cases

## [0.2.0] - 2025-04
### Added
- Anthropic Claude backend (`aek.backends.anthropic_agent`)
- `--tags` CLI filter
- `aek diff` and `aek report` subcommands
- `llm_judge` check

### Fixed
- Tool-call unordered-coverage score tidied
- Agent now respects `case.timeout_s`

## [0.1.0] - 2024-12
- Initial release: schema, runner, OpenAI agent, basic checks
