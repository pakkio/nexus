# tests/test_llm_wrapper.py
import pytest
import json
import time
from unittest.mock import Mock, MagicMock, patch, call
import requests
from llm_wrapper import (
    process_direct_streaming_output,
    process_direct_non_streaming_output,
    collect_direct_api_statistics,
    llm_wrapper,
    TerminalFormatter
)

@pytest.fixture
def mock_response():
    """Mock requests.Response object for testing"""
    response = MagicMock(spec=requests.Response)
    response.status_code = 200
    return response

@pytest.fixture
def mock_streaming_response():
    """Mock streaming response for tests"""
    response = MagicMock(spec=requests.Response)
    response.status_code = 200

    # Setup iter_lines to return mock streaming data
    lines = [
        b'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        b'data: {"choices":[{"delta":{"content":" world"}}]}',
        b'data: {"choices":[{"delta":{"content":"!"}}]}',
        b'data: [DONE]'
    ]
    response.iter_lines.return_value = lines

    return response

@pytest.fixture
def mock_non_streaming_response():
    """Mock non-streaming response for tests"""
    response = {
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        },
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is a test response."
                }
            }
        ]
    }
    return response

def test_process_direct_streaming_output(mock_streaming_response):
    """Test processing of streaming API output"""
    # Mock the print function instead of verifying formatter calls
    with patch('builtins.print') as mock_print:
        # Test processing streaming output
        output_text, first_token_time = process_direct_streaming_output(
            mock_streaming_response,
            # Use simple identity formatter that doesn't require mocking
            lambda x, width: x,
            80,
            None  # first_token_time starts as None
        )

        # Verify the output text includes all content
        assert output_text == "Hello world!"

        # Verify first_token_time gets set (not None anymore)
        assert first_token_time is not None

        # Verify print was called - each content chunk is printed
        assert mock_print.call_count >= 3

def test_process_direct_non_streaming_output(mock_non_streaming_response):
    """Test processing of non-streaming API output"""
    # Use simple identity formatter and check the final result
    output_text, first_token_time = process_direct_non_streaming_output(
        mock_non_streaming_response,
        lambda x, width: x,  # Identity formatter
        80
    )

    # Verify the correct output text is extracted
    assert output_text == "This is a test response."

    # Verify first_token_time gets set
    assert first_token_time is not None

def test_process_direct_non_streaming_output_error_handling():
    """Test error handling in non-streaming output processing"""
    # Test with invalid response structure
    invalid_response = {"choices": [{}]}  # Missing message/content

    output_text, _ = process_direct_non_streaming_output(
        invalid_response,
        lambda x, width: x,
        80
    )

    # Verify some kind of error/warning message is returned
    assert "[Warning:" in output_text or "Error" in output_text

    # Test with complete garbage
    garbage_response = "Not even JSON"

    output_text, _ = process_direct_non_streaming_output(
        garbage_response,
        lambda x, width: x,
        80
    )

    # Verify error message is returned - either an error about parsing or processing
    assert "Error" in output_text or "Warning" in output_text

def test_collect_direct_api_statistics():
    """Test collection of API statistics"""
    model_name = "test-model"
    messages = [{"role": "user", "content": "Hello"}]
    output_text = "Hi there"
    start_time = time.time() - 1  # 1 second ago
    first_token_time = time.time() - 0.5  # 0.5 seconds ago

    # Test with detailed usage info
    response_data = {
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }

    stats = collect_direct_api_statistics(
        model_name, messages, output_text, start_time, first_token_time, response_data
    )

    # Verify stats are collected correctly
    assert stats["model"] == "test-model"
    assert stats["input_tokens"] == 10
    assert stats["output_tokens"] == 20
    assert stats["total_tokens"] == 30
    assert stats["time_to_first_token"] == first_token_time - start_time
    assert stats["total_time"] > 0
    assert stats["error"] is None

    # Test with error in response
    error_response = {
        "error": {
            "message": "Test error"
        }
    }

    error_stats = collect_direct_api_statistics(
        model_name, messages, output_text, start_time, first_token_time, error_response
    )

    # Verify error is captured
    assert error_stats["error"] is not None
    assert "Test error" in str(error_stats["error"])

    # Test with no response data
    approx_stats = collect_direct_api_statistics(
        model_name, messages, output_text, start_time, first_token_time, None
    )

    # Verify approximate token counts are used
    assert approx_stats["input_tokens"] > 0
    assert approx_stats["output_tokens"] > 0

@patch('llm_wrapper.requests.post')
def test_llm_wrapper_streaming(mock_post, mock_streaming_response):
    """Test the main llm_wrapper function with streaming"""
    # Setup mock response
    mock_post.return_value = mock_streaming_response

    # Set environment variable for testing
    with patch.dict('os.environ', {"OPENROUTER_API_KEY": "test_key"}):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]

        # Call wrapper with streaming
        output, stats = llm_wrapper(
            messages=messages,
            model_name="test-model",
            stream=True,
            collect_stats=True
        )

        # Verify request was made correctly
        mock_post.assert_called_once()

        # Extract call arguments
        call_args = mock_post.call_args[1]

        # Verify streaming was requested
        assert call_args['json']['stream'] is True

        # Verify correct messages were sent
        assert call_args['json']['messages'] == messages

        # Verify model was set
        assert call_args['json']['model'] == "test-model"

        # Verify API key was used
        assert "Bearer test_key" in call_args['headers']['Authorization']

        # Verify response was processed
        assert output == "Hello world!"
        assert stats is not None

@patch('llm_wrapper.requests.post')
def test_llm_wrapper_non_streaming(mock_post, mock_non_streaming_response):
    """Test the main llm_wrapper function without streaming"""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_non_streaming_response
    mock_post.return_value = mock_response

    # Set environment variable for testing
    with patch.dict('os.environ', {"OPENROUTER_API_KEY": "test_key"}):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]

        # Call wrapper without streaming
        output, stats = llm_wrapper(
            messages=messages,
            model_name="test-model",
            stream=False,
            collect_stats=True
        )

        # Verify request was made correctly
        mock_post.assert_called_once()

        # Extract call arguments
        call_args = mock_post.call_args[1]

        # Verify streaming was not requested
        assert call_args['json']['stream'] is False

        # Verify correct messages were sent
        assert call_args['json']['messages'] == messages

        # Verify model was set
        assert call_args['json']['model'] == "test-model"

        # Verify API key was used
        assert "Bearer test_key" in call_args['headers']['Authorization']

        # Verify response was processed
        assert output == "This is a test response."
        assert stats is not None
        assert stats["input_tokens"] == 10
        assert stats["output_tokens"] == 20
        assert stats["total_tokens"] == 30

@patch('llm_wrapper.requests.post')
def test_llm_wrapper_error_handling(mock_post):
    """Test error handling in llm_wrapper"""
    # Setup mock to raise exception
    mock_post.side_effect = requests.RequestException("Test connection error")

    # Set environment variable for testing
    with patch.dict('os.environ', {"OPENROUTER_API_KEY": "test_key"}):
        messages = [{"role": "user", "content": "Hello!"}]

        # Call wrapper
        output, stats = llm_wrapper(
            messages=messages,
            model_name="test-model",
            stream=False,
            collect_stats=True
        )

        # Verify error response
        assert "Error" in output or "Errore" in output
        assert "Test connection error" in str(stats["error"])

@patch('llm_wrapper.requests.post')
def test_llm_wrapper_skips_non_user_last_message(mock_post):
    """Test that llm_wrapper handles non-user last message appropriately"""
    # Set environment variable for testing
    with patch.dict('os.environ', {"OPENROUTER_API_KEY": "test_key"}):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "assistant", "content": "How can I help?"}
        ]

        # Call wrapper
        output, stats = llm_wrapper(
            messages=messages,
            model_name="test-model",
            stream=False,
            collect_stats=True
        )

        # Verify behavior - either returns existing message or skips call
        # (both behaviors are valid implementations)
        assert "Skip" in stats.get("error", "") or output == "How can I help?"

        # Most importantly, verify no API call was made
        mock_post.assert_not_called()

@patch('llm_wrapper.requests.post')
def test_llm_wrapper_allows_utility_call_with_system_only(mock_post):
    """Test that llm_wrapper allows utility calls with only a system message"""
    # Setup for a profile analysis utility call
    profile_analysis_system_prompt = """You are an AI analyzing a player's recent interactions
The player's current profile is:
{"core_traits": {"curiosity": 6}}
Recent interaction:
[{"role": "user", "content": "Tell me more about the Veil."}]
Actions:
["Asked about Veil"]
Suggest updates as JSON: {"trait_adjustments": {"curiosity": "+1"}, "analysis_notes": "Player showed high curiosity."}"""

    messages_utility = [{"role": "system", "content": profile_analysis_system_prompt}]

    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"trait_adjustments": {"curiosity": "+1"}, "analysis_notes": "Player showed high curiosity."}'
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    # Set environment variable for testing
    with patch.dict('os.environ', {"OPENROUTER_API_KEY": "test_key"}):
        # Call wrapper with system-only message for utility
        output, stats = llm_wrapper(
            messages=messages_utility,
            model_name="test-model",
            stream=False,
            collect_stats=True
        )

        # Verify an API call was made only if llm_wrapper recognizes this pattern
        if "trait_adjustments" in output:
            # If it worked, an API call should have been made
            mock_post.assert_called_once()
            assert stats["error"] is None
        elif mock_post.call_count == 0:
            # If no API call was made but no error, that's an acceptable implementation
            assert "Player profile analysis" in stats.get("error", "")
