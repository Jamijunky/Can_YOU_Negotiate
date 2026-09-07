"use client";

import {
  useVoiceAssistant,
  useRemoteParticipants,
  useRoomContext,
} from "@livekit/components-react";
import { memo, useEffect, useRef } from "react";
import { useToast } from "./Toast";
import {
  MID_CALL_DROP_TIMEOUT_MS,
  INITIAL_DISPATCH_TIMEOUT_MS,
  NETWORK_STALL_TIMEOUT_MS,
} from "@/lib/constants";

const Watchdog = memo(function Watchdog({
  onDisconnect,
  isHolding,
}: {
  onDisconnect: () => void;
  isHolding: boolean;
}) {
  const { state } = useVoiceAssistant();
  const participants = useRemoteParticipants();
  const room = useRoomContext();
  const hasAgentJoinedRef = useRef(false);
  const { addToast } = useToast();

  useEffect(() => {
    if (participants.length > 0) {
      hasAgentJoinedRef.current = true;
    }
  }, [participants.length]);

  useEffect(() => {
    if (
      room.state === "connected" &&
      hasAgentJoinedRef.current &&
      participants.length === 0
    ) {
      const t = setTimeout(() => {
        if (
          room.state === "connected" &&
          hasAgentJoinedRef.current &&
          participants.length === 0
        ) {
          addToast(
            "Connection Lost: The subject disconnected unexpectedly.",
            "error"
          );
          try {
            room.disconnect();
          } catch {
            // Room may already be disconnected
          }
          onDisconnect();
        }
      }, MID_CALL_DROP_TIMEOUT_MS);
      return () => clearTimeout(t);
    }

    if (
      room.state === "connected" &&
      !hasAgentJoinedRef.current &&
      participants.length === 0
    ) {
      const t = setTimeout(() => {
        if (
          room.state === "connected" &&
          !hasAgentJoinedRef.current &&
          participants.length === 0
        ) {
          addToast(
            "Dispatch Timeout: The secure servers failed to wake up in time. Please try connecting again.",
            "error"
          );
          try {
            room.disconnect();
          } catch {
            // Room may already be disconnected
          }
          onDisconnect();
        }
      }, INITIAL_DISPATCH_TIMEOUT_MS);
      return () => clearTimeout(t);
    }
  }, [participants.length, room.state, room, onDisconnect, addToast]);

  useEffect(() => {
    if (isHolding) return;

    if (state === "listening" || state === "thinking") {
      const t = setTimeout(() => {
        addToast(
          "Network timeout: The comms link stalled. Automatically dropping the call to prevent freezing.",
          "warning"
        );
        try {
          room.disconnect();
        } catch {
          // Room may already be disconnected
        }
        onDisconnect();
      }, NETWORK_STALL_TIMEOUT_MS);
      return () => clearTimeout(t);
    }
  }, [state, room, onDisconnect, isHolding, addToast]);

  return null;
});

export default Watchdog;
