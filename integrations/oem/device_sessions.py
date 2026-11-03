from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol


class DeviceSessionAdapter(Protocol):
    def capabilities(self) -> dict[str, Any]:
        """Return explicitly supported capabilities without claiming hardware access."""
        ...

    def start(
        self, user_id: str, requested_capabilities: list[str]
    ) -> dict[str, Any]:
        """Create a synthetic session record; this does not connect to a device."""
        ...

    def act(self, session_id: str, user_id: str, action: str) -> dict[str, Any]:
        """Update a synthetic session lifecycle state."""
        ...


class SyntheticDeviceSessionAdapter:
    """Synthetic lifecycle contract for hardware-free adapter development."""

    def __init__(self, capabilities: list[str], session_ttl_seconds: int):
        self._capabilities = tuple(capabilities)
        self._session_ttl = timedelta(seconds=session_ttl_seconds)
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def capabilities(self) -> dict[str, Any]:
        return {
            "adapter": "synthetic",
            "adapter_status": "simulation_only",
            "hardware_connected": False,
            "live_capture": False,
            "display_output": False,
            "audio_output": False,
            "capabilities": list(self._capabilities),
        }

    def start(
        self, user_id: str, requested_capabilities: list[str]
    ) -> dict[str, Any]:
        unsupported = sorted(set(requested_capabilities) - set(self._capabilities))
        if unsupported:
            raise ValueError(
                "Unsupported capabilities: " + ", ".join(unsupported)
            )
        now = datetime.now(timezone.utc)
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "status": "simulated",
            "connection_status": "not_connected",
            "hardware_connected": False,
            "requested_capabilities": requested_capabilities,
            "created_at": now.isoformat(),
            "expires_at": (now + self._session_ttl).isoformat(),
        }
        with self._lock:
            self._sessions[session_id] = session
        return self._public_session(session)

    def act(self, session_id: str, user_id: str, action: str) -> dict[str, Any]:
        allowed_actions = {"pause", "resume", "stop"}
        if action not in allowed_actions:
            raise ValueError("action must be pause, resume, or stop.")
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session["user_id"] != user_id:
                raise KeyError("Device session was not found.")
            if datetime.fromisoformat(session["expires_at"]) <= datetime.now(
                timezone.utc
            ):
                del self._sessions[session_id]
                raise KeyError("Device session has expired.")

            current_status = session["status"]
            transitions = {
                ("simulated", "pause"): "paused",
                ("paused", "resume"): "simulated",
                ("simulated", "stop"): "stopped",
                ("paused", "stop"): "stopped",
            }
            next_status = transitions.get((current_status, action))
            if next_status is None:
                raise ValueError(
                    f"Cannot perform '{action}' while session is {current_status}."
                )
            session["status"] = next_status
            session["updated_at"] = datetime.now(timezone.utc).isoformat()
            return self._public_session(session)

    @staticmethod
    def _public_session(session: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in session.items() if key != "user_id"}
