# AGENTS.md

## Project identity

This project is a local-first Russian-language smart home voice assistant MVP. It uses Home Assistant as the orchestration and state core, while the product-specific intelligence lives in a custom backend and demo UI.

## High-level architecture

- Home Assistant stores smart home state and executes scenes, scripts, and integrations.
- FastAPI backend owns scenario logic, ambiguity handling, response generation, mock simulation, and event logging.
- UI is a demo and control surface, not a second source of truth.
- Text fallback must always work.
- Voice is an extension layer, not a hard dependency for MVP success.

## Delivery philosophy

- Prefer a reliable MVP over an ambitious but brittle system.
- Prefer deterministic demo behavior over uncontrolled realism.
- Avoid placing core business logic in YAML.
- Keep module boundaries clean and obvious.
- Use small steps, reviewable file changes, and clear implementation plans.

## Required user flows

- Device on and off control
- Scene activation
- Status queries
- Compound actions
- Clarification flow
- Invalid and incomplete command handling
- Demo reset and replay

## Project priorities

1. End-to-end working MVP
2. Demo stability
3. Architecture clarity
4. Clean code organization
5. Voice integration without making the project fragile

## Files to read before major work

- `README.md`
- `docs/architecture.md`
- `docs/intent-catalog.md`
- `docs/api-contracts.md`
- `.cursor/rules/`