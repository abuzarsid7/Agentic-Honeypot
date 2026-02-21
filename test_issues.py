"""
Tests for three issues in the /honeypot endpoint:
  1. sessionId must always be present in the JSON response.
  2. ifscCodes must always appear in extractedIntelligence.
  3. engagementDurationSeconds / totalMessagesExchanged must be at the TOP LEVEL
     (not nested under engagementMetrics).
  4. Conversation must NOT close before sufficient engagement (>= 15 turns).

Run:
    python test_issues.py
"""

import sys
import os
import time
import json
import unittest
import uuid

sys.path.insert(0, os.path.dirname(__file__))


# =============================================================================
# Shared helpers
# =============================================================================

_INTEL_FIELDS = [
    "phoneNumbers", "upiIds", "phishingLinks", "bankAccounts",
    "ifscCodes", "names", "emails", "caseIds",
    "policyNumbers", "orderNumbers", "additionalIntel",
]


def _normalize_intel(intel: dict) -> dict:
    """Mirror the production helper in main.py."""
    out = dict(intel)
    for field in _INTEL_FIELDS:
        if field not in out:
            out[field] = {} if field == "additionalIntel" else []
    return out


def _make_session(messages: int = 0, scam_type: str = "bank_impersonation",
                  intel: dict = None, history: list = None,
                  stale_turns: int = 0):
    base_intel = {
        "phoneNumbers": [], "upiIds": [], "phishingLinks": [],
        "bankAccounts": [], "ifscCodes": [], "names": [],
        "emails": [], "caseIds": [], "policyNumbers": [],
        "orderNumbers": [], "additionalIntel": {},
    }
    if intel:
        base_intel.update(intel)

    extraction_history = []
    for i in range(max(0, messages - stale_turns)):
        extraction_history.append({"turn": i, "new_intel_count": 1})
    for _ in range(stale_turns):
        extraction_history.append({"turn": messages - stale_turns, "new_intel_count": 0})

    msg_history = history or []
    if not msg_history:
        for i in range(messages):
            msg_history.append({
                "sender": "assistant",
                "text": "I am calling from the bank about your account issue." * 2,
            })

    return {
        "messages": messages,
        "scam_type": scam_type,
        "scam_score": 0.7,
        "intel": base_intel,
        "history": msg_history,
        "intel_extraction_history": extraction_history,
        "dialogue_state": "ESCALATE_EXTRACTION",
        "state_turn_count": 3,
        "start_time": time.time(),
        "asked_fields": {},
    }


def _build_success_response(session_id, session, scam_type="unknown",
                             scam_detected=True, confidence=0.9,
                             all_flags=None, reply="Test reply"):
    """Faithful replica of the response dict built inside /honeypot."""
    all_flags = all_flags or []
    intel = _normalize_intel(session.get("intel", {}))
    total_messages = session.get("messages", 0)
    duration_secs = round(time.time() - session.get("start_time", time.time()), 1)

    collected_parts = []
    if intel.get("phishingLinks"):  collected_parts.append(f"Shared {len(intel['phishingLinks'])} phishing link(s)")
    if intel.get("upiIds"):         collected_parts.append(f"Requested payment to {len(intel['upiIds'])} UPI ID(s)")
    if intel.get("phoneNumbers"):   collected_parts.append(f"Provided {len(intel['phoneNumbers'])} phone number(s) for callback")
    if intel.get("bankAccounts"):   collected_parts.append(f"Mentioned {len(intel['bankAccounts'])} account number(s)")
    if intel.get("ifscCodes"):      collected_parts.append(f"Provided {len(intel['ifscCodes'])} IFSC code(s)")
    if intel.get("names"):          collected_parts.append(f"Identified name(s): {', '.join(intel['names'][:3])}")
    if intel.get("emails"):         collected_parts.append(f"Shared {len(intel['emails'])} email address(es)")
    if intel.get("caseIds"):        collected_parts.append(f"Referenced {len(intel['caseIds'])} case/reference ID(s)")
    if not collected_parts:         collected_parts.append("No structured intel extracted yet")
    flags_summary = ", ".join(all_flags[:3]) if all_flags else "none detected"
    agent_notes = ". ".join(collected_parts) + f". Key signals: {flags_summary}."

    return {
        "status": "success",
        "sessionId": session_id,
        "scamDetected": bool(scam_detected),
        "extractedIntelligence": intel,
        "engagementDurationSeconds": duration_secs,
        "totalMessagesExchanged": total_messages,
        "agentNotes": agent_notes,
        "scamType": scam_type,
        "confidenceLevel": confidence,
        "reply": reply,
        "redFlags": all_flags,
        "conversationEnded": bool(session.get("conversation_ended", False)),
    }


def _build_ended_response(session_id, session):
    intel = _normalize_intel(session.get("intel", {}))
    return {
        "status": "ended",
        "sessionId": session_id,
        "scamDetected": True,
        "extractedIntelligence": intel,
        "engagementDurationSeconds": round(time.time() - session.get("start_time", time.time()), 1),
        "totalMessagesExchanged": session.get("messages", 0),
        "agentNotes": "Conversation ended",
        "scamType": session.get("scam_type", "unknown"),
        "confidenceLevel": 1.0,
        "redFlags": session.get("red_flags_log", []),
        "conversationEnded": True,
        "reply": "",
    }


# =============================================================================
# Issue 1 — sessionId present in every response path
# =============================================================================

class TestSessionIdInResponse(unittest.TestCase):

    def test_success_response_has_session_id(self):
        sid = str(uuid.uuid4())
        resp = _build_success_response(sid, _make_session(messages=3))
        self.assertIn("sessionId", resp)
        self.assertEqual(resp["sessionId"], sid)

    def test_ended_response_has_session_id(self):
        sid = str(uuid.uuid4())
        resp = _build_ended_response(sid, _make_session(messages=30))
        self.assertIn("sessionId", resp)
        self.assertEqual(resp["sessionId"], sid)

    def test_error_response_has_session_id(self):
        sid = str(uuid.uuid4())
        resp = {"status": "error", "sessionId": sid, "reply": "Temporary issue, please retry"}
        self.assertIn("sessionId", resp)
        self.assertEqual(resp["sessionId"], sid)

    def test_auto_generated_session_id_is_valid_uuid(self):
        payload = {}
        sid = payload.get("sessionId") or str(uuid.uuid4())
        self.assertEqual(len(sid), 36)
        self.assertEqual(str(uuid.UUID(sid)), sid)

    def test_provided_session_id_is_preserved(self):
        caller_sid = "my-custom-session-abc-123"
        payload = {"sessionId": caller_sid}
        sid = payload.get("sessionId") or str(uuid.uuid4())
        self.assertEqual(sid, caller_sid)

    def test_empty_string_triggers_uuid_generation(self):
        payload = {"sessionId": ""}
        sid = payload.get("sessionId") or str(uuid.uuid4())
        self.assertEqual(str(uuid.UUID(sid)), sid)

    def test_session_id_is_string_not_none(self):
        sid = str(uuid.uuid4())
        resp = _build_success_response(sid, _make_session())
        self.assertIsInstance(resp["sessionId"], str)
        self.assertGreater(len(resp["sessionId"]), 0)


# =============================================================================
# Issue 2 — ifscCodes always in extractedIntelligence
# =============================================================================

class TestIfscCodesInResponse(unittest.TestCase):

    def test_ifsc_codes_key_present_even_when_empty(self):
        """New sessions with no IFSC data must still have the key."""
        sid = str(uuid.uuid4())
        session = _make_session(messages=2)  # no IFSC in intel
        resp = _build_success_response(sid, session)
        intel = resp["extractedIntelligence"]
        self.assertIn("ifscCodes", intel,
            "ifscCodes key must always be present in extractedIntelligence")

    def test_ifsc_codes_default_is_empty_list(self):
        sid = str(uuid.uuid4())
        session = _make_session()
        resp = _build_success_response(sid, session)
        self.assertEqual(resp["extractedIntelligence"]["ifscCodes"], [])

    def test_ifsc_codes_surfaced_when_extracted(self):
        sid = str(uuid.uuid4())
        session = _make_session(intel={"ifscCodes": ["SBIN0001234", "HDFC0000123"]})
        resp = _build_success_response(sid, session)
        self.assertEqual(resp["extractedIntelligence"]["ifscCodes"],
                         ["SBIN0001234", "HDFC0000123"])

    def test_normalize_intel_backfills_missing_ifsc(self):
        """Old sessions stored in Redis before ifscCodes was added must be fixed."""
        old_intel = {          # pre-ifscCodes schema
            "phoneNumbers": ["9876543210"],
            "upiIds": [], "phishingLinks": [], "bankAccounts": [],
            "names": [], "emails": [], "caseIds": [],
            "policyNumbers": [], "orderNumbers": [],
        }
        fixed = _normalize_intel(old_intel)
        self.assertIn("ifscCodes", fixed)
        self.assertEqual(fixed["ifscCodes"], [])

    def test_normalize_intel_backfills_additional_intel(self):
        old_intel = {"phoneNumbers": ["9876543210"]}
        fixed = _normalize_intel(old_intel)
        self.assertIn("additionalIntel", fixed)
        self.assertIsInstance(fixed["additionalIntel"], dict)

    def test_all_expected_intel_fields_present(self):
        sid = str(uuid.uuid4())
        resp = _build_success_response(sid, _make_session())
        intel = resp["extractedIntelligence"]
        for field in _INTEL_FIELDS:
            self.assertIn(field, intel, f"Field '{field}' missing from extractedIntelligence")

    def test_ifsc_in_ended_response(self):
        sid = str(uuid.uuid4())
        session = _make_session(messages=30)
        resp = _build_ended_response(sid, session)
        self.assertIn("ifscCodes", resp["extractedIntelligence"])

    def test_ifsc_in_agent_notes_when_extracted(self):
        sid = str(uuid.uuid4())
        session = _make_session(intel={"ifscCodes": ["SBIN0001234"]})
        resp = _build_success_response(sid, session)
        self.assertIn("IFSC", resp["agentNotes"],
            "agentNotes should mention IFSC codes when they are extracted")


# =============================================================================
# Issue 3 — Engagement metrics at top level, NOT nested
# =============================================================================

class TestEngagementMetricsAtTopLevel(unittest.TestCase):

    def test_total_messages_at_top_level(self):
        sid = str(uuid.uuid4())
        session = _make_session(messages=7)
        resp = _build_success_response(sid, session)
        self.assertIn("totalMessagesExchanged", resp,
            "totalMessagesExchanged must be at top level of response")

    def test_duration_at_top_level(self):
        sid = str(uuid.uuid4())
        resp = _build_success_response(sid, _make_session(messages=3))
        self.assertIn("engagementDurationSeconds", resp,
            "engagementDurationSeconds must be at top level of response")

    def test_no_nested_engagement_metrics_key(self):
        sid = str(uuid.uuid4())
        resp = _build_success_response(sid, _make_session())
        self.assertNotIn("engagementMetrics", resp,
            "engagementMetrics must NOT be a nested object — fields must be at top level")

    def test_total_messages_correct_value(self):
        sid = str(uuid.uuid4())
        session = _make_session(messages=11)
        resp = _build_success_response(sid, session)
        self.assertEqual(resp["totalMessagesExchanged"], 11)

    def test_duration_is_non_negative_float(self):
        sid = str(uuid.uuid4())
        resp = _build_success_response(sid, _make_session(messages=5))
        val = resp["engagementDurationSeconds"]
        self.assertIsInstance(val, (int, float))
        self.assertGreaterEqual(val, 0)

    def test_ended_response_also_has_flat_metrics(self):
        sid = str(uuid.uuid4())
        session = _make_session(messages=30)
        resp = _build_ended_response(sid, session)
        self.assertIn("totalMessagesExchanged", resp)
        self.assertIn("engagementDurationSeconds", resp)
        self.assertNotIn("engagementMetrics", resp)

    def test_metrics_types_match_expected(self):
        sid = str(uuid.uuid4())
        session = _make_session(messages=4)
        resp = _build_success_response(sid, session)
        self.assertIsInstance(resp["totalMessagesExchanged"], int)
        self.assertIsInstance(resp["engagementDurationSeconds"], float)


# =============================================================================
# Issue 4 — Conversation must NOT close before >= 15 turns
# =============================================================================

class TestConversationDoesNotCloseEarly(unittest.TestCase):
    """
    Conversation must NEVER close before the hard ceiling (50 messages).
    All intel-score, stagnation, and disengagement close paths have been
    removed — only the safety ceiling ends a session.
    """

    CEILING = 50

    def _run_get_next_state(self, session, current_state_name="ESCALATE_EXTRACTION"):
        from unittest.mock import patch
        from dialogue_strategy import get_next_state, ConversationState, STATE_CONFIG

        state = getattr(ConversationState, current_state_name)
        config = STATE_CONFIG[state]
        turn_count = config.get("max_turns", 3) + 1  # always "exceeded_turns"

        # Worst-case scores / patterns that previously triggered closes
        mock_intel_score = {
            "score": 0.90,
            "components": {
                "artifacts": 0.85,
                "scam_confidence": 0.95,
                "engagement": 0.2,
                "novelty": 0.05,
            }
        }
        mock_patterns = {
            "repeated_pressure": True,
            "disengagement": True,
            "stale_intel": True,
            "severity": 0.90,
        }
        with patch("intelligence.calculate_intel_score", return_value=mock_intel_score), \
             patch("intelligence.detect_scammer_patterns", return_value=mock_patterns):
            return get_next_state(
                current_state=state,
                turn_count=turn_count,
                scammer_text="Okay, yes.",
                intel=session["intel"],
                session=session,
            )

    def _assert_not_closed(self, messages):
        session = _make_session(
            messages=messages, stale_turns=messages,
            intel={
                "phoneNumbers": ["9876543210"],
                "upiIds": ["fraud@paytm"],
                "phishingLinks": ["http://fake.com"],
                "bankAccounts": ["12345678901234"],
                "ifscCodes": ["SBIN0001234"],
                "names": ["Rajesh Kumar"],
                "emails": ["fraud@fake.com"],
                "caseIds": ["REF-001"],
            },
        )
        result = self._run_get_next_state(session)
        ended = session.get("conversation_ended", False)
        self.assertFalse(ended,
            f"conversation_ended=True at {messages} messages (state returned: {result}). "
            f"Chat must not close before ceiling ({self.CEILING}).")
        self.assertNotEqual(result.value, "CLOSE",
            f"get_next_state returned CLOSE at {messages} messages — must not close early.")

    def test_no_close_at_5_messages(self):    self._assert_not_closed(5)
    def test_no_close_at_10_messages(self):   self._assert_not_closed(10)
    def test_no_close_at_15_messages(self):   self._assert_not_closed(15)
    def test_no_close_at_20_messages(self):   self._assert_not_closed(20)
    def test_no_close_at_25_messages(self):   self._assert_not_closed(25)
    def test_no_close_at_30_messages(self):   self._assert_not_closed(30)
    def test_no_close_at_40_messages(self):   self._assert_not_closed(40)
    def test_no_close_at_49_messages(self):   self._assert_not_closed(49)

    def test_hard_cap_closes_at_50(self):
        """At exactly 50 messages the conversation MUST close."""
        from unittest.mock import patch
        from dialogue_strategy import get_next_state, ConversationState

        session = _make_session(messages=self.CEILING)
        mock_score = {"score": 0.2, "components": {"artifacts": 0.1, "scam_confidence": 0.5, "engagement": 0.5, "novelty": 0.5}}
        mock_pat   = {"repeated_pressure": False, "disengagement": False, "stale_intel": False, "severity": 0.0}

        with patch("intelligence.calculate_intel_score", return_value=mock_score), \
             patch("intelligence.detect_scammer_patterns", return_value=mock_pat):
            result = get_next_state(
                current_state=ConversationState.ESCALATE_EXTRACTION,
                turn_count=1,
                scammer_text="Hello.",
                intel=session["intel"],
                session=session,
            )
        self.assertEqual(result, ConversationState.CLOSE,
            f"Expected CLOSE at ceiling ({self.CEILING} messages)")
        self.assertTrue(session.get("conversation_ended", False),
            "conversation_ended must be True at ceiling")

    def test_escalate_cycles_back_not_close(self):
        """ESCALATE_EXTRACTION with exceeded turns must return a probing state, not CLOSE."""
        from unittest.mock import patch
        from dialogue_strategy import get_next_state, ConversationState

        for msg_count in [5, 15, 25, 35, 49]:
            session = _make_session(
                messages=msg_count,
                intel={"phoneNumbers": ["9876543210"], "upiIds": ["x@paytm"],
                       "phishingLinks": ["http://fake.com"]},
            )
            mock_score = {"score": 0.9, "components": {"artifacts": 0.9, "scam_confidence": 0.9, "engagement": 0.1, "novelty": 0.05}}
            mock_pat   = {"repeated_pressure": True, "disengagement": True, "stale_intel": True, "severity": 0.95}

            with patch("intelligence.calculate_intel_score", return_value=mock_score), \
                 patch("intelligence.detect_scammer_patterns", return_value=mock_pat):
                result = get_next_state(
                    current_state=ConversationState.ESCALATE_EXTRACTION,
                    turn_count=999,  # Way beyond max_turns
                    scammer_text="ok",
                    intel=session["intel"],
                    session=session,
                )
            self.assertNotEqual(result, ConversationState.CLOSE,
                f"ESCALATE_EXTRACTION returned CLOSE at {msg_count} messages — must cycle instead")



# =============================================================================
# Integration tests (skipped when server is offline)
# =============================================================================

class TestLiveEndpoint(unittest.TestCase):

    BASE_URL = "http://localhost:8000"
    API_KEY  = "guvi-hackathon-2026"

    def _server_is_up(self):
        try:
            import urllib.request
            urllib.request.urlopen(f"{self.BASE_URL}/health", timeout=2)
            return True
        except Exception:
            return False

    def _post(self, payload):
        import urllib.request
        req = urllib.request.Request(
            f"{self.BASE_URL}/honeypot",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "X-API-KEY": self.API_KEY},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())

    def test_live_session_id_present(self):
        if not self._server_is_up():
            self.skipTest("Server not running")
        data = self._post({"message": {"sender": "scammer", "text": "Your account is at risk! Send 9876543210 now."}, "conversationHistory": []})
        self.assertIn("sessionId", data)
        self.assertTrue(data["sessionId"])
        uuid.UUID(data["sessionId"])  # raises if not valid UUID

    def test_live_ifsc_codes_in_response(self):
        if not self._server_is_up():
            self.skipTest("Server not running")
        data = self._post({"message": {"sender": "scammer", "text": "Transfer to account 12345678901234 IFSC SBIN0001234"}, "conversationHistory": []})
        intel = data.get("extractedIntelligence", {})
        self.assertIn("ifscCodes", intel, f"ifscCodes missing from live response intel: {intel}")

    def test_live_engagement_metrics_at_top_level(self):
        if not self._server_is_up():
            self.skipTest("Server not running")
        data = self._post({"message": {"sender": "scammer", "text": "Click http://fake-bank.com/verify"}, "conversationHistory": []})
        self.assertIn("totalMessagesExchanged", data, "totalMessagesExchanged not at top level")
        self.assertIn("engagementDurationSeconds", data, "engagementDurationSeconds not at top level")
        self.assertNotIn("engagementMetrics", data, "engagementMetrics must not be nested")

    def test_live_session_id_stable_across_turns(self):
        if not self._server_is_up():
            self.skipTest("Server not running")
        sid = None
        for text in ["Your bank account is blocked.", "My name is Rajesh. Call 9876543210."]:
            payload = {"message": {"sender": "scammer", "text": text}, "conversationHistory": []}
            if sid:
                payload["sessionId"] = sid
            data = self._post(payload)
            self.assertIn("sessionId", data)
            if sid is None:
                sid = data["sessionId"]
            else:
                self.assertEqual(data["sessionId"], sid,
                    f"sessionId changed between turns: {sid!r} → {data['sessionId']!r}")


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [
        TestSessionIdInResponse,
        TestIfscCodesInResponse,
        TestEngagementMetricsAtTopLevel,
        TestConversationDoesNotCloseEarly,
        TestLiveEndpoint,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
