import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from streamlit.testing.v1 import AppTest

# --- MOCK DATA ---
MOCK_TREND_DATA = [
    {"posted_at": "2026-01-01", "Python": 0.45, "Docker": 0.20},
    {"posted_at": "2026-01-02", "Python": 0.47, "Docker": 0.22}
]
MOCK_MOMENTUM_DATA = {"Python": 12.5, "Docker": 8.2}

MOCK_RECOMMEND_RESPONSE = {
    "masked_resume": "[REDACTED] Professional Experience...",
    "extracted_skills": ["Python", "Docker"],
    "recommendations": [
        {
            "title": "MLOps Engineer",
            "company": "Tech Corp",
            "match_score": 0.85,
            "missing_skills": ["Kubernetes"]
        }
    ]
}

# --- TESTS ---

@patch("requests.get")
def test_market_trends_fetch_success(mock_get):
    """Test that clicking 'Refresh Trends' successfully loads data into the session state and renders components."""
    # 1. Setup mocked responses for both trends and momentum API calls
    mock_resp_trends = MagicMock(status_code=200)
    mock_resp_trends.json.return_value = MOCK_TREND_DATA
    
    mock_resp_momentum = MagicMock(status_code=200)
    mock_resp_momentum.json.return_value = MOCK_MOMENTUM_DATA
    
    mock_get.side_effect = [mock_resp_trends, mock_resp_momentum]

    # 2. Initialize Streamlit App Test
    at = AppTest.from_file("app.py").run()
    
    # 3. Simulate clicking the "Refresh Trends" button
    # active_loop simulation finds the button by label
    at.button[0].click().run()

    # 4. Assertions
    assert not at.exception
    assert "trend_df" in at.session_state
    assert "momentum" in at.session_state
    # Check if the subheader for Momentum rendered
    assert any("Skill Momentum" in block.value for block in at.subheader)


def test_too_many_skills_guardrail():
    """Test that selecting > 40 skills triggers the safety error message to prevent system crashes."""
    at = AppTest.from_file("app.py").run()
    
    # Manually inject a mock dataframe into session state to bypass the API click
    fake_skills = {f"Skill_{i}": [1, 2] for i in range(45)}
    df = pd.DataFrame(fake_skills)
    df.index.name = 'posted_at'
    
    at.session_state.trend_df = df
    at.session_state.momentum = pd.Series({"Skill_1": 1.0})
    at.run()

    # Select all 45 skills in the multiselect widget
    at.multiselect[0].select_all().run()

    # Check if the system safety error is triggered
    assert len(at.error) > 0
    assert "Too many skills selected" in at.error[0].value


@patch("requests.post")
def test_resume_matcher_upload_and_parse(mock_post):
    """Test that uploading a PDF resume calls the recommendation endpoint and updates metrics."""
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = MOCK_RECOMMEND_RESPONSE
    mock_post.return_value = mock_resp

    at = AppTest.from_file("app.py").run()
    
    # Switch to the Resume Matcher Tab (Index 1)
    # Simulate file uploader receiving a dummy byte stream
    at.file_uploader[0].upload(b"fake pdf content").run()

    # Assertions
    assert not at.exception
    # Check if the extracted skills are visible in an info box
    assert "Extracted Skills:" in at.info[0].value
    # Check if our metric displays the 85% match calculation (0.85 * 100)
    assert "85%" in at.metric[0].value