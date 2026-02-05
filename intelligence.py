import re

def extract_intel(session, text):
    text_l = text.lower()

    upis = re.findall(r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}", text)
    session["intel"]["upiIds"].extend(upis)

    if "upi" in text_l:
        session["intel"]["suspiciousKeywords"].append("upi")

    phones = re.findall(r"\+91\d{10}", text)
    session["intel"]["phoneNumbers"].extend(phones)

    links = re.findall(r"https?://\S+", text)
    session["intel"]["phishingLinks"].extend(links)

def maybe_finish(session):
    return session["messages"] >= 15
