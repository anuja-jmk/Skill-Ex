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
    """Test that clicking 'Refresh Trends' successfully loads data into the session state."""
    mock_resp_trends = MagicMock(status_code=200)
    mock_resp_trends.json.return_value = MOCK_TREND_DATA
    
    mock_resp_momentum = MagicMock(status_code=200)
    mock_resp_momentum.json.return_value = MOCK_MOMENTUM_DATA
    
    mock_get.side_effect = [mock_resp_trends, mock_resp_momentum]

    at = AppTest.from_file("app.py").run()
    
    # Click 'Refresh Trends' button safely
    at.button[0].click().run()

    assert not at.exception
    assert "trend_df" in at.session_state
    assert "momentum" in at.session_state
    assert any("Skill Momentum" in block.value for block in at.subheader)


def test_too_many_skills_guardrail():
    """Test that selecting > 40 skills triggers the safety error message."""
    at = AppTest.from_file("app.py").run()
    
    # 1. Create a fake dataframe with 45 unique skills (columns)
    fake_skills = {f"Skill_{i}": [1, 2] for i in range(45)}
    df = pd.DataFrame(fake_skills)
    df.index.name = 'posted_at'
    
    # Inject it directly into the state
    at.session_state.trend_df = df
    at.session_state.momentum = pd.Series({"Skill_1": 1.0})
    at.run()

    # 2. FIX: Instead of select_all(), grab all the strings from the mock frame
    all_skills_list = df.columns.tolist()

    # 3. FIX: Pass the entire list into the multiselect using .set_value()
    at.multiselect[0].set_value(all_skills_list).run()

    # Verify the protection triggered
    assert len(at.error) > 0
    assert "Too many skills selected" in at.error[0].value

@patch("requests.post")
def test_resume_matcher_upload_and_parse(mock_post):
    """Test that uploading a PDF resume calls the recommendation endpoint."""
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = MOCK_RECOMMEND_RESPONSE
    mock_post.return_value = mock_resp

    at = AppTest.from_file("app.py").run()
    
    # FIX: Create a mock file object that explicitly has a 'name' attribute
    # built directly into it, rather than passing it as a keyword argument.
    import io
    fake_pdf = io.BytesIO(b"fake pdf content")
    fake_pdf.name = "resume.pdf"  # Streamlit looks for this attribute on the object
    
    # Pass just the content bytes using positional arguments
    at.file_uploader[0].upload(fake_pdf.getvalue()).run()

    assert not at.exception
    assert "Extracted Skills:" in at.info[0].value
    assert "85%" in at.metric[0].value