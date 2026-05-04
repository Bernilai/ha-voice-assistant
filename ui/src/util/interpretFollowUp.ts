/**
 * UI glue for interpret_stub "missing_room" clarification only:
 * stub returns canonical_intent=null; we infer light on/off from normalized text
 * so the user can pick a room and we POST /api/intents/execute without duplicating HA resolution.
 */
export function inferLightToggleIntent(normalizedText: string): 'turn_on_device' | 'turn_off_device' | null {
  if (normalizedText.includes('выключи')) {
    return 'turn_off_device'
  }
  if (normalizedText.includes('включи')) {
    return 'turn_on_device'
  }
  return null
}
