"""
API エンドポイントのテスト

テスト対象:
- /api/chat/stream のPPTXテンプレート対応
- /api/template/analyze のテンプレート解析エンドポイント
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import base64
import json
import sys

# 依存関係がない場合はスキップ
pytest.importorskip("sse_starlette", reason="sse_starlette not installed")

# template_analyzer のオプション依存関係チェック
try:
    import pdf2image
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False



class TestChatEndpointWithTemplate:
    """ChatエンドポイントのPPTXテンプレート対応テスト"""
    
    def test_chat_endpoint_without_template(self):
        """テンプレートなしでの通常リクエストが動作することを確認"""
        from fastapi.testclient import TestClient
        from src.api.app import app
        
        with patch("src.api.app.run_agent_workflow") as mock_workflow, \
             patch("src.api.app._extract_design_context") as mock_extract:
            
            # モック設定
            async def mock_generator():
                yield {"event": "start_of_workflow", "data": {"workflow_id": "test"}}
                yield {"event": "end_of_workflow", "data": {"workflow_id": "test"}}
            
            mock_workflow.return_value = mock_generator()
            mock_extract.return_value = None
            
            client = TestClient(app)
            response = client.post(
                "/api/chat/stream",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "debug": False,
                    "deep_thinking_mode": False,
                    "search_before_planning": False,
                }
            )
            
            # レスポンスが正常であることを確認
            assert response.status_code == 200
    
    def test_chat_endpoint_with_pptx_template(self):
        """PPTXテンプレート付きリクエストが処理されることを確認"""
        from fastapi.testclient import TestClient
        from src.api.app import app
        
        # Base64エンコードされたダミーPPTX
        dummy_pptx_bytes = b"PK\x03\x04..."
        pptx_base64 = base64.b64encode(dummy_pptx_bytes).decode()
        
        with patch("src.api.app._extract_design_context") as mock_extract, \
             patch("src.api.app.run_agent_workflow") as mock_workflow:
            
            # モック DesignContext
            mock_design_context = Mock()
            mock_design_context.layouts = []
            mock_design_context.layout_image_bytes = {}
            mock_extract.return_value = mock_design_context
            
            async def mock_generator():
                yield {"event": "start_of_workflow", "data": {"workflow_id": "test"}}
                yield {"event": "end_of_workflow", "data": {"workflow_id": "test"}}
            
            mock_workflow.return_value = mock_generator()
            
            client = TestClient(app)
            response = client.post(
                "/api/chat/stream",
                json={
                    "messages": [{"role": "user", "content": "スライドを作って"}],
                    "pptx_template_base64": pptx_base64,
                }
            )
            
            assert response.status_code == 200
            
            # _extract_design_context が呼ばれたことを確認
            mock_extract.assert_called_once_with(pptx_base64)


class TestExtractDesignContextHelper:
    """_extract_design_context ヘルパー関数のテスト"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_PDF2IMAGE, reason="pdf2image not installed")
    async def test_extract_design_context_success(self):
        """正常なPPTX解析が動作することを確認"""
        from src.api.app import _extract_design_context
        import src.utils.template_analyzer as template_analyzer_module
        
        dummy_bytes = b"PPTX_CONTENT"
        pptx_base64 = base64.b64encode(dummy_bytes).decode()
        
        mock_design_context = Mock()
        mock_design_context.layouts = [Mock()]
        mock_design_context.layout_image_bytes = {"title_slide": b"PNG"}
        
        with patch.object(template_analyzer_module, "analyze_pptx_template", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_design_context
            
            result = await _extract_design_context(pptx_base64)
            
            assert result == mock_design_context
            mock_analyze.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_design_context_returns_none_for_empty(self):
        """空の入力に対してNoneを返すことを確認"""
        from src.api.app import _extract_design_context
        
        result = await _extract_design_context(None)
        assert result is None
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_PDF2IMAGE, reason="pdf2image not installed")
    async def test_extract_design_context_handles_error(self):
        """エラー時にNoneを返すことを確認"""
        from src.api.app import _extract_design_context
        import src.utils.template_analyzer as template_analyzer_module
        
        pptx_base64 = base64.b64encode(b"INVALID").decode()
        
        with patch.object(template_analyzer_module, "analyze_pptx_template", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = Exception("Parse error")
            
            result = await _extract_design_context(pptx_base64)
            
            assert result is None


class TestTemplateAnalyzeEndpoint:
    """/api/template/analyze エンドポイントのテスト"""
    
    def test_analyze_rejects_non_pptx_file(self):
        """PPTXでないファイルを拒否することを確認"""
        from fastapi.testclient import TestClient
        from src.api.app import app
        
        client = TestClient(app)
        
        # テキストファイルをアップロード
        response = client.post(
            "/api/template/analyze",
            files={"file": ("test.txt", b"Hello world", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    @pytest.mark.skipif(not HAS_PDF2IMAGE, reason="pdf2image not installed")
    def test_analyze_accepts_pptx_file(self):
        """PPTXファイルを受け入れることを確認"""
        from fastapi.testclient import TestClient
        from src.api.app import app
        import src.utils.template_analyzer as template_analyzer_module
        
        mock_design_context = Mock()
        mock_design_context.layouts = [Mock(layout_type="title_slide")]
        mock_design_context.layout_image_bytes = {}
        mock_design_context.color_scheme = Mock(accent1="#FF0000", accent2="#00FF00")
        mock_design_context.font_scheme = Mock(major_latin="Arial", minor_latin="Calibri")
        mock_design_context.model_dump.return_value = {"layouts": []}
        
        with patch.object(template_analyzer_module, "analyze_pptx_template", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_design_context
            
            client = TestClient(app)
            response = client.post(
                "/api/template/analyze",
                files={"file": ("template.pptx", b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["filename"] == "template.pptx"
            assert "summary" in data
