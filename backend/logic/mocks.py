
import json
import base64
from PIL import Image
import io
import random
from typing import List, Optional, Any, Dict, Union

class MockTextPart:
    """A mock part of a text content."""
    def __init__(self, text: str):
        self.text: str = text

class MockTextContent:
    """A mock text content object."""
    def __init__(self, text: str):
        self.parts: List[MockTextPart] = [MockTextPart(text)]
        self.role: str = "model"

class MockTextCandidate:
    """A mock candidate response."""
    def __init__(self, text: str):
        self.content: MockTextContent = MockTextContent(text)
        self.finish_reason: str = "STOP"

class MockGeminiResponse:
    """A mock response from the Gemini model."""
    def __init__(self, text: str):
        self._text: str = text
        self.candidates: List[MockTextCandidate] = [MockTextCandidate(text)]

    @property
    def text(self) -> str:
        return self._text

class MockGenerativeModel:
    """
    A mock class for Google Generative AI models.
    """
    def __init__(self, model_name: str = "mock-gemini"):
        self.model_name: str = model_name

    def generate_content(
        self, 
        prompt: Union[str, List[Union[str, Any]]], 
        generation_config: Optional[Dict[str, Any]] = None, 
        tools: Optional[List[Any]] = None
    ) -> MockGeminiResponse:
        """
        Mocks the content generation based on the input prompt keywords.

        Args:
            prompt (Union[str, List]): The input prompt.
            generation_config (Optional[Dict]): Configuration parameters.
            tools (Optional[List]): Tools provided to the model.

        Returns:
            MockGeminiResponse: A mocked response object.
        """
        # Normalize prompt to text for simple pattern matching
        if isinstance(prompt, list):  # Multimodal (Image + Text)
            string_parts = [p for p in prompt if isinstance(p, str)]
            prompt_text = " ".join(string_parts).strip()
        else:
            prompt_text = str(prompt)

        if "legibility" in prompt_text:
            return self._mock_quality_gate()

        if "presentation editor" in prompt_text and "Instruction" in prompt_text:
            return self._mock_edit()
        if "StyleDef" in prompt_text:
            return self._mock_style(prompt_text)
        if "visual_prompt" in prompt_text and "layout_id" in prompt_text and "slides" in prompt_text:
            return self._mock_plan(prompt_text)
        if "Critique" in prompt_text and "Creative Director" in prompt_text:
            return self._mock_refine(prompt_text)
        if "Design Director" in prompt_text and "visual identity" in prompt_text:
            return self._mock_consistency(prompt_text)
        else:
            return MockGeminiResponse(text=json.dumps({"error": "Unknown prompt type"}))

    def _mock_consistency(self, prompt: str) -> MockGeminiResponse:
        data = {
            "consistency_score": 85,
            "is_consistent": True,
            "feedback": "Consistent corporate blue theme and flat illustration style observed across all slides."
        }
        return MockGeminiResponse(text=json.dumps(data))

    def _mock_refine(self, prompt: str) -> MockGeminiResponse:
        # Return a slightly modified plan to simulate refinement
        data = {
            "slides": [
                {
                    "slide_id": 1,
                    "text_expected": True,
                    "layout_id": "title",
                    "visual_prompt": "Refined Title Slide: Minimalist, azure blue",
                    "content_text": "Refined Title"
                },
                {
                    "slide_id": 2,
                    "text_expected": True,
                    "layout_id": "content_left",
                    "visual_prompt": "Refined Content: Chart on left",
                    "content_text": "Refined Content"
                }
            ]
        }
        return MockGeminiResponse(text=json.dumps(data))

    def _mock_quality_gate(self) -> MockGeminiResponse:
        data = {
            "text_block_count": 3,
            "average_confidence": 0.95,
            "illegible_block_count": 0,
            "overall_judgement": "OK"
        }
        return MockGeminiResponse(text=json.dumps(data))

    def _mock_style(self, prompt: str) -> MockGeminiResponse:
        data = {
            "global_prompt": "Mocked global prompt: minimalistic, corporate blue, clean lines.",
            "layouts": [
                {"layout_id": "title", "visual_description": "Centered title with logo on top right."},
                {"layout_id": "content_left", "visual_description": "Text on left, image on right."},
                {"layout_id": "visual_center", "visual_description": "Large visual in center, caption at bottom."}
            ]
        }
        return MockGeminiResponse(text=json.dumps(data))

    def _mock_plan(self, prompt: str) -> MockGeminiResponse:
         # Extract text from prompt to pretend we processed it (simple heuristic)
         # In a real mock, we might return fixed data
         data = {
           "slides": [
             {
               "slide_id": 1,
               "text_expected": True,
               "layout_id": "title",
               "visual_prompt": "A modern title slide background with abstract blue shapes.",
               "content_text": "Mock Project Launch"
             },
             {
               "slide_id": 2,
               "text_expected": True,
               "layout_id": "content_left",
               "visual_prompt": "A clean office meeting room background.",
               "content_text": "Agenda: 1. Overview, 2. Metrics, 3. Next Steps"
             },
             {
               "slide_id": 3,
               "text_expected": False,
               "layout_id": "visual_center",
               "visual_prompt": "A rocket ship launching into space.",
               "content_text": ""
             }
           ]
         }
         return MockGeminiResponse(text=json.dumps(data))

    def _mock_edit(self) -> MockGeminiResponse:
        data = {
            "slide_id": 1,
            "text_expected": True,
            "layout_id": "content_left",
            "visual_prompt": "An updated clean layout with clearer emphasis.",
            "content_text": "Updated content based on instruction."
        }
        return MockGeminiResponse(text=json.dumps(data))

class MockInlineData:
    def __init__(self, data: bytes):
        self.data: bytes = data

class MockPart:
    def __init__(self, data: bytes):
        self.inline_data: MockInlineData = MockInlineData(data)

class MockContent:
    def __init__(self, data: bytes):
        self.parts: List[MockPart] = [MockPart(data)]

class MockCandidate:
    def __init__(self, data: bytes):
        self.content: MockContent = MockContent(data)

class MockGenAIResponse:
    """A mock response for image generation."""
    def __init__(self):
        # Generate a random colored image buffer
        img = Image.new('RGB', (1920, 1080), color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        self.data: bytes = buf.getvalue()
        self._image_bytes: bytes = self.data # Required by image_generator.py
        self.candidates: List[MockCandidate] = [MockCandidate(self.data)]

class MockModels:
    def generate_content(self, model: str, contents: Any, config: Any) -> MockGenAIResponse:
        return MockGenAIResponse()

class MockImageGenerationModel:
    """
    A mock class for Image Generation models.
    """
    def __init__(self, model_name: str = "mock-imagen"):
        self.model_name: str = model_name
        self.models: MockModels = MockModels()
        
    @classmethod
    def from_pretrained(cls, model_name: str) -> "MockImageGenerationModel":
        return cls(model_name)

    def generate_images(self, prompt: str, number_of_images: int = 1, aspect_ratio: str = "16:9") -> List[MockGenAIResponse]:
        """
        Mocks image generation.

        Args:
            prompt (str): The image prompt.
            number_of_images (int): Number of images to generate.
            aspect_ratio (str): Aspect ratio string.

        Returns:
            List[MockGenAIResponse]: List of mock responses containing image data.
        """
        # Mock immediate return for production/clean state, user can verify latency via network throttling if needed.
        return [MockGenAIResponse()]
