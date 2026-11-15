/** Server message on `/ws`. See contracts/ws-messages.schema.json. */
export interface WsMessage {
  /** Outbox id when the message originates from an event; null on ticks. */
  seq: number | null
  topic: string
  type: string
  at: string
  data: unknown
}
