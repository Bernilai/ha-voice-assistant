# Prompt 04 — Scenarios and ambiguity

Use the master prompt and project rules.

Implement the core product logic:
- scenario_engine
- ambiguity_resolver
- response_builder
- clarification continuation
- support for scene activation
- support for status queries
- support for compound actions

Requirements:
- clarification-first behavior for ambiguous commands
- deterministic behavior for demo mode
- event log entries for success, ambiguity, and failure
- avoid speculative patterns and overengineering

After implementation, add or update tests for the supported behavior.