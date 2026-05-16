import pytest
from shared.utils.pii_masker import PIIMasker

def test_email_masking():
    text = "Please contact me at test@example.com."
    masked = PIIMasker.mask(text)
    assert masked == "Please contact me at [EMAIL REDACTED]."
    
def test_phone_masking():
    text = "My phone number is 123-456-7890."
    masked = PIIMasker.mask(text)
    assert masked == "My phone number is [PHONE REDACTED]."

# def test_link_masking():
#     text = "Check out my profile at linkedin.com/in/testuser."
#     masked = PIIMasker.mask(text)
#     assert masked == "Check out my profile at [LINK REDACTED]."

def test_multiple_pii():
    text = "Name: John Doe, Email: john@doe.com, Phone: (555) 555-5555"
    masked = PIIMasker.mask(text)
    assert "[EMAIL REDACTED]" in masked
    assert "[PHONE REDACTED]" in masked
    # If spaCy model is loaded, it should also mask 'John Doe' as [PERSON REDACTED]
    if PIIMasker.nlp is not None:
        assert "[PERSON REDACTED]" in masked

def test_empty_string():
    assert PIIMasker.mask("") == ""
    assert PIIMasker.mask(None) == ""