SCAM_KEYWORDS = [
    "account blocked", "verify", "urgent",
    "upi", "bank", "suspended", "click link"
]

def detect_scam(text, history):
    text = text.lower()
    score = sum(1 for k in SCAM_KEYWORDS if k in text)
    return score >= 1