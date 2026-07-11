// Contrat de message temps réel — miroir du `LiveEvent` backend (E00US008).

export interface LiveEvent {
  type: string
  data: Record<string, unknown>
}
