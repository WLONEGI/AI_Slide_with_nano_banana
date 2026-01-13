# 検索ツール: Google Search API Wrapper を使用
import logging
import os
from dotenv import load_dotenv
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_core.tools import Tool

# 環境変数をロード
load_dotenv()

logger = logging.getLogger(__name__)

# Google Search API の設定値
GOOGLE_SEARCH_MAX_RESULTS = int(os.getenv("GOOGLE_SEARCH_MAX_RESULTS", "10"))

# GoogleSearchAPIWrapper を初期化
_google_search = GoogleSearchAPIWrapper(k=GOOGLE_SEARCH_MAX_RESULTS)

# Tool として定義（LangChainエージェントで使用可能にする）
def _run_google_search(query: str) -> str:
    """Google検索を実行し、結果を返す"""
    return _google_search.run(query)

# ロギング付きツールとして定義
google_search_tool = Tool(
    name="google_search",
    description="インターネットで情報を検索します。最新のニュース、統計、企業情報などを取得するのに使用してください。",
    func=_run_google_search,
)
