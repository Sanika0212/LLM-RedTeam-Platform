"""Tests for hallucination detector."""

from detectors.hallucination import detect_hallucination


def test_factual_text(factual_response):
    result = detect_hallucination("What is Python?", factual_response)
    assert result["hallucination_score"] == 0.0
    assert result["indicators"] == []


def test_fake_citations(hallucinated_response):
    result = detect_hallucination("Tell me about AI", hallucinated_response)
    assert result["hallucination_score"] > 0.0
    assert len(result["indicators"]) > 0


def test_fake_doi():
    text = "This was confirmed by recent research (doi: 10.1234/fake-journal)."
    result = detect_hallucination("test", text)
    assert result["hallucination_score"] > 0.0
    assert any("doi" in i.lower() for i in result["indicators"])


def test_percentage_claims():
    text = "Studies show that 95% of participants agreed with the findings."
    result = detect_hallucination("test", text)
    assert result["hallucination_score"] > 0.0


def test_study_claims():
    text = "According to a recent study, this approach works better."
    result = detect_hallucination("test", text)
    assert result["hallucination_score"] > 0.0


def test_suspicious_url():
    text = "See the full paper at https://www.example.com/journal/2024/article/12345/some-paper-about-things"
    result = detect_hallucination("test", text)
    assert result["hallucination_score"] > 0.0


def test_empty_response():
    result = detect_hallucination("test", "")
    assert result["hallucination_score"] == 0.0
    assert result["indicators"] == []


def test_score_capped_at_one():
    text = (
        "Smith et al. (2024) found 90% of cases. Johnson et al. (2023) confirmed 85% success. "
        "Published in the Journal of AI (doi: 10.9999/test). According to a recent survey, "
        "95% of researchers agree. See doi: 10.1111/other and doi: 10.2222/more. "
        "According to the latest research, this is effective."
    )
    result = detect_hallucination("test", text)
    assert result["hallucination_score"] <= 1.0


def test_indicators_limited_to_ten():
    # Many indicators should be capped to 10
    text = " ".join([f"Smith{i} et al. (202{i%10})" for i in range(20)])
    result = detect_hallucination("test", text)
    assert len(result["indicators"]) <= 10
