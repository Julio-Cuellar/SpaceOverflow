/** Mensaje del servidor en `/ws`. Ver contracts/ws-messages.schema.json. */
export interface WsMessage {
  /** Id del outbox cuando el mensaje nace de un evento; null en los ticks. */
  seq: number | null
  topic: string
  type: string
  at: string
  data: unknown
}
