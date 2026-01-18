import pytest
from unittest.mock import MagicMock, patch
from src.utils.image_generation import generate_image
from google.genai import types

@pytest.fixture
def mock_genai_client():
    with patch("src.utils.image_generation.genai.Client") as mock:
        yield mock

@pytest.mark.parametrize("seed", [None, 12345])
@pytest.mark.parametrize("reference_image", [None, b"fake_image_bytes"])
def test_generate_image_success(mock_genai_client, seed, reference_image):
    # Setup mock response
    mock_client_instance = mock_genai_client.return_value
    mock_response = MagicMock()
    
    # Mock part with inline data
    mock_part = MagicMock()
    mock_part.inline_data.data = b"generated_image_bytes"
    
    # Needs to match: response.candidates[0].content.parts
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]
    mock_candidate.thought_signature = None  # Explicitly set to None
    mock_response.candidates = [mock_candidate]
    
    mock_client_instance.models.generate_content.return_value = mock_response

    # Execute
    prompt = "A beautiful sunset"
    result_bytes, result_token = generate_image(prompt, seed=seed, reference_image=reference_image)

    # Verify
    assert result_bytes == b"generated_image_bytes"
    assert result_token is None  # No thought_signature in mock
    
    # Verify arguments passed to client
    mock_client_instance.models.generate_content.assert_called_once()
    call_args = mock_client_instance.models.generate_content.call_args
    _, kwargs = call_args
    
    assert kwargs["model"] is not None
    assert len(kwargs["contents"]) >= 1
    assert kwargs["contents"][0] == prompt
    
    if reference_image:
        # Check if Part object is in contents
        assert len(kwargs["contents"]) == 2
        # Note: We can't strict check Part.from_bytes return since it's an external lib object,
        # unless we mock types.Part.from_bytes as well.
        
    config = kwargs["config"]
    assert isinstance(config, types.GenerateContentConfig)
    assert config.response_modalities == ["IMAGE"]
    if seed:
        assert config.seed == seed

def test_generate_image_no_data_error(mock_genai_client):
    # Setup mock response with no candidates/parts
    mock_client_instance = mock_genai_client.return_value
    mock_response = MagicMock()
    mock_response.candidates = [] # Empty candidates
    
    mock_client_instance.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="No image data found"):
        generate_image("prompt")

def test_generate_image_api_error(mock_genai_client):
    # Setup mock to raise exception
    mock_client_instance = mock_genai_client.return_value
    mock_client_instance.models.generate_content.side_effect = Exception("API 500 Error")

    with pytest.raises(Exception, match="API 500 Error"):
        generate_image("prompt")
