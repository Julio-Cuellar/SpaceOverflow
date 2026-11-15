import { describe, it, expect, vi, afterEach } from "vitest";
import { voiceService } from "./voice";
const response = (body: unknown) =>
  new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
  });
afterEach(() => vi.unstubAllGlobals());
describe("Voice backend confirmation boundary", () => {
  it("uploads and polls a transcript without asking until explicitly confirmed", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response({ utterance_id: "voice-1" }))
      .mockResolvedValueOnce(
        response({ status: "TRANSCRIBED", text: "Review the oxygen source." }),
      )
      .mockResolvedValueOnce(
        response({
          outcome: "NO_INFO",
          text: "No source loaded.",
          citations: [],
          degraded: true,
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    const voice = voiceService("/api/v1/voice/utterances");
    expect(
      await voice.transcribe(new Blob(["demo"], { type: "audio/webm" })),
    ).toEqual({ text: "Review the oxygen source." });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const answer = await voice.confirm("Corrected text");
    expect(fetchMock.mock.calls[2][0]).toBe(
      "/api/v1/voice/utterances/voice-1/confirm",
    );
    expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual({
      text: "Corrected text",
    });
    expect(answer.degraded).toBe(true);
  });
  it("discards a reviewed utterance without calling the assistant", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response({ utterance_id: "voice-2" }))
      .mockResolvedValueOnce(response({ status: "TRANSCRIBED", text: "Draft" }))
      .mockResolvedValueOnce(response({ status: "DISCARDED" }));
    vi.stubGlobal("fetch", fetchMock);
    const voice = voiceService("/voice");
    await voice.transcribe(new Blob(["demo"]));
    await voice.discard();
    expect(fetchMock.mock.calls[2][0]).toBe("/voice/voice-2/discard");
    await expect(voice.confirm("Draft")).rejects.toThrow("No transcript");
  });
  it("distinguishes an unavailable model from silence", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response({ utterance_id: "voice-3" }))
      .mockResolvedValueOnce(
        response({ status: "NO_TRANSCRIPT", reason_code: "NO_MODEL" }),
      );
    vi.stubGlobal("fetch", fetchMock);
    await expect(
      voiceService("/voice").transcribe(new Blob(["demo"])),
    ).rejects.toThrow("unavailable");
  });
});
