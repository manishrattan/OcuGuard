from __future__ import annotations

import html
import json
import os
import uuid
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from dotenv import load_dotenv

from core.config import load_settings


load_dotenv()


def _api_request(
    method: str,
    api_url: str,
    path: str,
    timeout: float,
    *,
    params: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    headers = {}
    api_key = os.getenv("API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        response = requests.request(
            method,
            f"{api_url.rstrip('/')}{path}",
            params=params,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        return None, "The API request timed out."
    except requests.exceptions.RequestException as error:
        return None, f"The API request failed ({type(error).__name__})."

    if not response.ok:
        message = f"The API returned HTTP {response.status_code}."
        try:
            body = response.json()
        except requests.exceptions.JSONDecodeError:
            body = None
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                message = f"{message} {error['message']}"
        return None, message

    if response.status_code == 204:
        return {}, None
    try:
        result = response.json()
    except requests.exceptions.JSONDecodeError:
        return None, "The API returned a response that was not valid JSON."
    if not isinstance(result, dict):
        return None, "The API response did not contain a JSON object."
    return result, None


def _form_text(
    label: str, value: str = "", *, key: str, max_chars: int | None = None
) -> str:
    return st.text_input(label, value=value, key=key, max_chars=max_chars)


def _format_recurrence(minutes: int) -> str:
    if minutes == 0:
        return "One time"
    if minutes % 10080 == 0:
        count = minutes // 10080
        return f"Every {count} week{'s' if count != 1 else ''}"
    if minutes % 1440 == 0:
        count = minutes // 1440
        return f"Every {count} day{'s' if count != 1 else ''}"
    return f"Every {minutes} minutes"


def _speak_instruction(text: str, key: str) -> None:
    encoded_text = (
        json.dumps(text)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    st.components.v1.html(
        f"""
        <div style="display:flex;gap:.5rem;align-items:center">
          <button id="speak-{html.escape(key)}" type="button"
            style="padding:.55rem .85rem;border-radius:.5rem;border:1px solid #53677f;
            background:#1b2b40;color:#f8fafc;font-size:1rem">
            Read instruction aloud
          </button>
          <button id="stop-speech-{html.escape(key)}" type="button"
            style="padding:.55rem .85rem;border-radius:.5rem;border:1px solid #53677f;
            background:#1b2b40;color:#f8fafc;font-size:1rem">
            Stop reading aloud
          </button>
        </div>
        <span id="speech-status-{html.escape(key)}" role="status" aria-live="polite"></span>
        <script>
          const text = {encoded_text};
          const button = document.getElementById("speak-{html.escape(key)}");
          const stopButton = document.getElementById("stop-speech-{html.escape(key)}");
          const status = document.getElementById("speech-status-{html.escape(key)}");
          stopButton.addEventListener("click", () => {{
            if ("speechSynthesis" in window) window.speechSynthesis.cancel();
            status.textContent = "Reading stopped.";
          }});
          button.addEventListener("click", () => {{
            if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {{
              status.textContent = "Speech output is not supported in this browser.";
              return;
            }}
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.onend = () => {{ status.textContent = "Finished reading."; }};
            utterance.onerror = () => {{ status.textContent = "Speech output could not be completed."; }};
            status.textContent = "Reading instruction.";
            window.speechSynthesis.speak(utterance);
          }});
        </script>
        """,
        height=62,
        scrolling=False,
    )


def render() -> None:
    settings = load_settings()
    st.set_page_config(
        page_title="Recovery Companion | OcuGuard",
        page_icon=":material/accessibility_new:",
        layout="wide",
    )
    st.title("Recovery Companion prototype")
    st.caption(
        "A hands-free-friendly way to access text the user supplies and schedules "
        "they choose. It does not create, interpret, or change care instructions."
    )
    st.warning(settings["application"]["prototype_notice"])
    st.info(
        "Prototype data is stored in the configured local SQLite database without "
        "encryption. Use synthetic text only; do not enter real patient information."
    )

    features = settings["features"]
    if not features["recovery_companion"]:
        st.error("The recovery companion feature is disabled in configuration.")
        return

    api_url = os.getenv("OCUGUARD_API_URL", settings["ui"]["api_url"])
    timeout = float(settings["ui"]["api_timeout_seconds"])
    max_user_id_chars = settings["recovery"]["max_user_id_chars"]
    user_id = st.session_state.get("recovery_demo_user_id")
    if not isinstance(user_id, str):
        user_id = f"demo-{uuid.uuid4().hex[:12]}"
        st.session_state["recovery_demo_user_id"] = user_id
    if len(user_id) > max_user_id_chars:
        st.error("Configured demo user identifier exceeds the configured limit.")
        return

    st.caption(f"Session-scoped demo identifier: `{user_id}`")
    st.caption(f"API: `{api_url}`")

    instructions_result, instructions_error = _api_request(
        "GET",
        api_url,
        "/v1/recovery/instructions",
        timeout,
        params={"user_id": user_id},
    )
    reminders_result, reminders_error = _api_request(
        "GET",
        api_url,
        "/v1/recovery/reminders",
        timeout,
        params={"user_id": user_id},
    )
    if instructions_error:
        st.error(f"Could not load instruction cards. {instructions_error}")
    if reminders_error:
        st.error(f"Could not load reminders. {reminders_error}")

    instructions = (
        instructions_result.get("items", [])
        if isinstance(instructions_result, dict)
        else []
    )
    reminders = (
        reminders_result.get("items", [])
        if isinstance(reminders_result, dict)
        else []
    )

    cards_tab, reminders_tab, device_tab, privacy_tab = st.tabs(
        ["Instruction cards", "Reminders", "Device status", "Privacy controls"]
    )

    with cards_tab:
        st.subheader("Add an instruction card")
        st.caption(
            "Enter wording already provided to you. OcuGuard stores and presents "
            "the text as supplied; the source label is user-entered and not verified."
        )
        with st.form("instruction-create-form", clear_on_submit=True):
            title = _form_text(
                "Card title",
                key="recovery-new-title",
                max_chars=settings["recovery"]["max_title_chars"],
            )
            source = _form_text(
                "Source label (as entered)",
                key="recovery-new-source",
                max_chars=settings["recovery"]["max_source_chars"],
            )
            instruction_text = st.text_area(
                "Instruction text (preserved verbatim)",
                key="recovery-new-instruction",
                max_chars=settings["recovery"]["max_instruction_chars"],
            )
            submitted = st.form_submit_button("Save instruction card")
        if submitted:
            if not title.strip() or not source.strip() or not instruction_text.strip():
                st.error("Enter a title, source label, and instruction text.")
            else:
                result, error = _api_request(
                    "POST",
                    api_url,
                    "/v1/recovery/instructions",
                    timeout,
                    payload={
                        "user_id": user_id,
                        "title": title,
                        "source_label": source,
                        "instruction_text": instruction_text,
                    },
                )
                if error:
                    st.error(f"Could not save the instruction card. {error}")
                elif result:
                    st.success("Instruction card saved.")
                    st.rerun()

        st.divider()
        st.subheader("Saved cards")
        if instructions_result is not None and not instructions:
            st.info("No instruction cards have been saved for this demo session.")
        for item in instructions:
            card_id = str(item["id"])
            with st.expander(str(item["title"])):
                st.caption(
                    f"Source as entered: {item['source_label']} · "
                    f"Saved: {item['created_at']}"
                )
                st.text(item["instruction_text"])
                if features["browser_speech"]:
                    _speak_instruction(item["instruction_text"], card_id)
                    st.caption(
                        "Uses this browser's speech engine. It does not send audio "
                        "to OcuGuard or play through connected glasses. Browser or "
                        "operating-system speech services may process text differently; "
                        "use synthetic text only."
                    )

                with st.form(f"edit-instruction-{card_id}"):
                    edited_title = _form_text(
                        "Edit title",
                        str(item["title"]),
                        key=f"edit-title-{card_id}",
                        max_chars=settings["recovery"]["max_title_chars"],
                    )
                    edited_source = _form_text(
                        "Edit source label",
                        str(item["source_label"]),
                        key=f"edit-source-{card_id}",
                        max_chars=settings["recovery"]["max_source_chars"],
                    )
                    edited_text = st.text_area(
                        "Edit instruction text",
                        value=str(item["instruction_text"]),
                        key=f"edit-text-{card_id}",
                        max_chars=settings["recovery"]["max_instruction_chars"],
                    )
                    save_changes = st.form_submit_button("Save changes")
                if save_changes:
                    result, error = _api_request(
                        "PUT",
                        api_url,
                        f"/v1/recovery/instructions/{card_id}",
                        timeout,
                        payload={
                            "user_id": user_id,
                            "title": edited_title,
                            "source_label": edited_source,
                            "instruction_text": edited_text,
                        },
                    )
                    if error:
                        st.error(f"Could not update the instruction card. {error}")
                    elif result:
                        st.success("Instruction card updated.")
                        st.rerun()
                confirm_delete = st.checkbox(
                    "Confirm deleting this card and its reminders",
                    key=f"confirm-delete-card-{card_id}",
                )
                if st.button(
                    "Delete card",
                    key=f"delete-card-{card_id}",
                    disabled=not confirm_delete,
                ):
                    _, error = _api_request(
                        "DELETE",
                        api_url,
                        f"/v1/recovery/instructions/{card_id}",
                        timeout,
                        params={"user_id": user_id},
                    )
                    if error:
                        st.error(f"Could not delete the instruction card. {error}")
                    else:
                        st.success("Instruction card and linked reminders deleted.")
                        st.rerun()

    with reminders_tab:
        st.subheader("Choose your own reminder schedule")
        st.caption(
            "Reminders are user-set prompts only. They do not monitor adherence, "
            "confirm a health status, or provide new care instructions."
        )
        if instructions:
            timezone_options = settings["ui"]["timezones"]
            if not all(_is_timezone(value) for value in timezone_options):
                st.error("One or more configured timezones are invalid.")
            else:
                with st.form("reminder-create-form", clear_on_submit=True):
                    selected_instruction_id = st.selectbox(
                        "Instruction card",
                        options=[str(item["id"]) for item in instructions],
                        format_func=lambda value: next(
                            str(item["title"])
                            for item in instructions
                            if str(item["id"]) == value
                        ),
                        key="reminder-instruction",
                    )
                    selected_timezone = st.selectbox(
                        "Timezone",
                        options=timezone_options,
                        key="reminder-timezone",
                    )
                    local_now = datetime.now(ZoneInfo(selected_timezone))
                    reminder_date = st.date_input(
                        "First reminder date",
                        value=local_now.date(),
                        key="reminder-date",
                    )
                    reminder_time = st.time_input(
                        "First reminder time",
                        value=time(hour=local_now.hour, minute=local_now.minute),
                        key="reminder-time",
                    )
                    allowed_intervals = settings["recovery"][
                        "allowed_recurrence_minutes"
                    ]
                    recurrence = st.selectbox(
                        "Repeat",
                        options=allowed_intervals,
                        format_func=_format_recurrence,
                        key="reminder-recurrence",
                    )
                    create_reminder = st.form_submit_button("Save reminder")
                if create_reminder:
                    local_scheduled = datetime.combine(
                        reminder_date,
                        reminder_time,
                        tzinfo=ZoneInfo(selected_timezone),
                    )
                    result, error = _api_request(
                        "POST",
                        api_url,
                        "/v1/recovery/reminders",
                        timeout,
                        payload={
                            "user_id": user_id,
                            "instruction_id": selected_instruction_id,
                            "scheduled_at": local_scheduled.isoformat(),
                            "timezone": selected_timezone,
                            "recurrence_minutes": recurrence,
                        },
                    )
                    if error:
                        st.error(f"Could not save the reminder. {error}")
                    elif result:
                        st.success("Reminder schedule saved.")
                        st.rerun()
        else:
            st.info("Add an instruction card before scheduling a reminder.")

        st.divider()
        st.subheader("Scheduled reminders")
        if reminders_result is not None and not reminders:
            st.info("No reminders have been scheduled for this demo session.")
        for reminder in reminders:
            reminder_id = str(reminder["id"])
            due_status = (
                "Due according to the schedule you set"
                if reminder["due"]
                else str(reminder["status"]).capitalize()
            )
            with st.container(border=True):
                st.markdown(f"**{reminder['instruction_title']}**")
                st.caption(
                    f"{due_status} · {reminder['scheduled_at']} "
                    f"({reminder['timezone']}) · "
                    f"{_format_recurrence(reminder['recurrence_minutes'] or 0)}"
                )
                if reminder["due"]:
                    st.warning(
                        "This is a user-scheduled reminder. It does not indicate "
                        "a health status or confirm that an instruction was followed."
                    )
                action_columns = st.columns(2)
                status = reminder["status"]
                if status in {"active", "paused"}:
                    label, action = (
                        ("Pause", "pause")
                        if status == "active"
                        else ("Resume", "resume")
                    )
                    if action_columns[0].button(
                        label, key=f"reminder-{action}-{reminder_id}"
                    ):
                        _perform_reminder_action(
                            api_url,
                            timeout,
                            user_id,
                            reminder_id,
                            action,
                        )
                if status == "active" and reminder["due"]:
                    if action_columns[1].button(
                        "Acknowledge / next",
                        key=f"reminder-ack-{reminder_id}",
                    ):
                        _perform_reminder_action(
                            api_url,
                            timeout,
                            user_id,
                            reminder_id,
                            "acknowledge",
                        )
                    snooze_options = settings["recovery"][
                        "allowed_snooze_minutes"
                    ]
                    with st.container():
                        snooze_columns = st.columns(2)
                        snooze_minutes = snooze_columns[0].selectbox(
                            "Snooze (minutes)",
                            options=snooze_options,
                            key=f"reminder-snooze-minutes-{reminder_id}",
                        )
                        if snooze_columns[1].button(
                            "Snooze",
                            key=f"reminder-snooze-{reminder_id}",
                        ):
                            _perform_reminder_action(
                                api_url,
                                timeout,
                                user_id,
                                reminder_id,
                                "snooze",
                                snooze_minutes=snooze_minutes,
                            )
                if action_columns[2].button(
                    "Delete reminder", key=f"reminder-delete-{reminder_id}"
                ):
                    _, error = _api_request(
                        "DELETE",
                        api_url,
                        f"/v1/recovery/reminders/{reminder_id}",
                        timeout,
                        params={"user_id": user_id},
                    )
                    if error:
                        st.error(f"Could not delete reminder. {error}")
                    else:
                        st.rerun()

    with device_tab:
        st.subheader("Wearable adapter status")
        st.caption(
            "This is a lifecycle-contract simulator only. It does not discover, "
            "pair with, or connect to Meta glasses or any other hardware."
        )
        if features["device_session_demo"]:
            capabilities, error = _api_request(
                "GET",
                api_url,
                "/v1/device/capabilities",
                timeout,
            )
            if error:
                st.error(f"Could not load adapter capabilities. {error}")
            elif capabilities:
                st.json(capabilities)
                st.caption(
                    "The adapter status and all capabilities are configuration-driven; "
                    "hardware, capture, and glasses output remain unavailable."
                )

            if st.button("Start synthetic session", key="start-device-session"):
                result, error = _api_request(
                    "POST",
                    api_url,
                    "/v1/device/sessions",
                    timeout,
                    payload={
                        "user_id": user_id,
                        "requested_capabilities": [],
                    },
                )
                if error:
                    st.error(f"Could not start synthetic session. {error}")
                elif result:
                    st.session_state["recovery_device_session"] = result["session"]
                    st.rerun()

            session = st.session_state.get("recovery_device_session")
            if isinstance(session, dict):
                st.write(
                    f"Session state: **{session['status']}** "
                    f"· Hardware connected: **No**"
                )
                if session["status"] in {"simulated", "paused"}:
                    action = "pause" if session["status"] == "simulated" else "resume"
                    if st.button(
                        f"{action.capitalize()} simulated session",
                        key=f"device-{action}",
                    ):
                        _perform_device_action(
                            api_url,
                            timeout,
                            user_id,
                            session["session_id"],
                            action,
                        )
                if session["status"] in {"simulated", "paused"}:
                    if st.button(
                        "Stop simulated session", key="device-stop"
                    ):
                        _perform_device_action(
                            api_url,
                            timeout,
                            user_id,
                            session["session_id"],
                            "stop",
                        )
        else:
            st.info("Device session demo is disabled in configuration.")

    with privacy_tab:
        st.subheader("Data and permissions")
        st.markdown(
            "- The API stores card text, a user-entered source label, reminder "
            "schedules, and a session-scoped demo ID in local SQLite.\n"
            "- Data is not encrypted at rest by this prototype. Keep the service "
            "private and use synthetic text only.\n"
            "- The browser speech button uses the browser speech engine; the app "
            "does not send speech audio to the API. Browser/OS speech services may "
            "process text differently, so use synthetic text only.\n"
            "- No camera or microphone capture, glasses pairing, or cloud media "
            "processing is implemented."
        )
        confirm_clear = st.checkbox(
            "I understand this permanently deletes this demo session's cards and reminders.",
            key="confirm-clear-recovery-data",
        )
        if st.button(
            "Delete my demo cards and reminders",
            disabled=not confirm_clear,
            key="delete-recovery-data",
        ):
            _, error = _api_request(
                "DELETE",
                api_url,
                "/v1/recovery/data",
                timeout,
                payload={"user_id": user_id, "confirm": True},
            )
            if error:
                st.error(f"Could not delete demo data. {error}")
            else:
                st.success("Demo instruction cards and reminders were deleted.")
                st.rerun()


def _is_timezone(value: str) -> bool:
    try:
        ZoneInfo(value)
    except (ValueError, KeyError):
        return False
    return True


def _perform_reminder_action(
    api_url: str,
    timeout: float,
    user_id: str,
    reminder_id: str,
    action: str,
    snooze_minutes: int | None = None,
) -> None:
    payload: dict[str, Any] = {"user_id": user_id, "action": action}
    if snooze_minutes is not None:
        payload["snooze_minutes"] = snooze_minutes
    _, error = _api_request(
        "PATCH",
        api_url,
        f"/v1/recovery/reminders/{reminder_id}",
        timeout,
        payload=payload,
    )
    if error:
        st.error(f"Could not update reminder. {error}")
    else:
        st.rerun()


def _perform_device_action(
    api_url: str,
    timeout: float,
    user_id: str,
    session_id: str,
    action: str,
) -> None:
    result, error = _api_request(
        "POST",
        api_url,
        f"/v1/device/sessions/{session_id}/actions",
        timeout,
        payload={"user_id": user_id, "action": action},
    )
    if error:
        st.error(f"Could not update simulated session. {error}")
    elif result:
        st.session_state["recovery_device_session"] = result["session"]
        st.rerun()
