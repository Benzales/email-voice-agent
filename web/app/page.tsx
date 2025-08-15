"use client";

import { useEffect, useRef, useState } from "react";
import { createWsAudioClient } from "../lib/audio/ws-client";
import { createPcm16Player } from "../lib/audio/playback";

type Email = { id: string; from?: string; subject?: string; date?: string };

export default function HomePage() {
  const [emails, setEmails] = useState<Email[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [status, setStatus] = useState("Idle");
  const [sessionActive, setSessionActive] = useState(false);
  const [wsClient, setWsClient] = useState<ReturnType<typeof createWsAudioClient> | null>(null);
  const playerRef = useRef<ReturnType<typeof createPcm16Player> | null>(null);

  const currentEmail = emails[currentIndex];

  // Fetch inbox on mount
  useEffect(() => {
    const backend = process.env.NEXT_PUBLIC_MCP_BACKEND_URL || process.env.MCP_BACKEND_URL || "";
    if (!backend) return;
    fetch(`${backend}/mcp/inbox`).then(async (r) => {
      const data = await r.json();
      setEmails(data.emails || []);
    }).catch(() => {});
  }, []);

  async function startSession() {
    try {
      setStatus("Requesting microphone permission…");
      setStatus("Connecting to realtime backend…");
      const backend = process.env.NEXT_PUBLIC_MCP_BACKEND_URL || process.env.MCP_BACKEND_URL || "";
      const url = backend.replace(/^http/, "ws") + "/realtime";

      playerRef.current = createPcm16Player();
      const client = createWsAudioClient(
        url,
        (msg) => setStatus(msg || ""),
        (pcm) => playerRef.current?.playPcm16(pcm, 24000)
      );

      await client.start();
      setWsClient(client);
      setSessionActive(true);
      setStatus("Session started. Speaking…");
    } catch (e: any) {
      setStatus(`Error: ${e?.message || e}`);
      setSessionActive(false);
    }
  }

  function stopSession() {
    // For MVP UI, page reload can serve as a reset; more graceful teardown can be added
    wsClient?.stop();
    setSessionActive(false);
    setStatus("Stopped");
  }

  function getSystemInstruction(): string {
    return [
      "You are a voice-driven Gmail assistant with full access to the Gmail API through tools.",
      "PRIMARY BEHAVIOR - Single Email Focus:",
      "- You will be provided with information for ONE email at a time",
      "- Announce ONLY: sender and subject",
      "- After reading the email, ask what the user would like to do",
      "- Possible actions include: reply, archive, delete, mark as read/unread, or skip to next",
      "- CRITICAL WORKFLOW: After you execute ANY action on an email (via tools), you MUST immediately call the complete_current_email tool.",
      "- CRITICAL WORKFLOW: If the user says 'skip', 'next', 'continue', immediately call the complete_current_email tool",
      "- Do NOT ask 'what would you like to do next' after completing an email action - just call complete_current_email immediately",
      "- When performing actions on 'this email', use the email ID that was provided with the email information",
      "Key Behaviors:",
      "- Be concise but helpful in your responses",
      "- Focus only on the current email",
      "Important Action Instructions:",
      "- When archiving an email, use gmail_modify_email with removeLabelIds: [\"INBOX\"]",
    ].join("\n");
  }

  return (
    <div style={{ padding: 24, maxWidth: 720, margin: "0 auto", fontFamily: "system-ui, sans-serif" }}>
      <h2>Email Voice Agent</h2>
      <p>{status}</p>
      {!sessionActive ? (
        <button onClick={startSession} style={{ padding: 12 }}>Start session</button>
      ) : (
        <button onClick={stopSession} style={{ padding: 12 }}>Stop</button>
      )}

      <div style={{ marginTop: 16 }}>
        <strong>Current email:</strong>
        <div style={{ marginTop: 8 }}>
          {currentEmail ? (
            <div>
              <div>From: {currentEmail.from || "Unknown"}</div>
              <div>Subject: {currentEmail.subject || "No subject"}</div>
              <div>ID: {currentEmail.id}</div>
            </div>
          ) : (
            <div>No emails loaded.</div>
          )}
        </div>
      </div>

      {/* Audio handled by WebAudio player */}
    </div>
  );
}


