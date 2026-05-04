# Prompt 02 — Home Assistant integration layer

Use the master prompt and project rules.

Implement only the Home Assistant integration and config layer:
- ha/configuration.yaml
- ha/intent_script.yaml
- ha/scenes.yaml
- ha/packages/living_room.yaml
- ha/packages/kitchen.yaml
- ha/packages/bedroom.yaml
- ha/custom_sentences/ru/control_device.yaml
- ha/custom_sentences/ru/scene_control.yaml
- ha/custom_sentences/ru/status_queries.yaml

Requirements:
- use realistic Russian sentence templates
- keep YAML as a thin integration layer
- do not push core business logic into YAML
- align entities and room names with the domain model

After implementation, explain how the HA layer connects to the backend.