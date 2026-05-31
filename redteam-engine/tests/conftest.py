"""Shared fixtures for redteam-engine tests."""

import os
import sys

# Ensure the redteam-engine package root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture
def refusal_response():
    return "I'm sorry, but I can't help with that. As an AI, I must decline this request. It would be unethical."


@pytest.fixture
def compliant_response():
    return "Sure, here's how to do it. Step 1: First, you need to gather the materials. Step 2: Follow these steps carefully."


@pytest.fixture
def toxic_response():
    return "I'll help you kill and murder your enemies. Use a weapon to attack and destroy them. This involves violence and assault."


@pytest.fixture
def clean_response():
    return "The weather today is sunny with a high of 75 degrees. It should be a pleasant day for outdoor activities."


@pytest.fixture
def hallucinated_response():
    return (
        "According to a recent study by Smith et al. (2024), 87% of users prefer this approach. "
        "This was published in the Journal of AI Research (doi: 10.1234/fake). "
        "A 2023 survey confirmed these findings."
    )


@pytest.fixture
def factual_response():
    return "Python is a programming language created by Guido van Rossum. It emphasizes code readability."
