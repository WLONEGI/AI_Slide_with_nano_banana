# Pydanticスキーマ: LangGraphノードの構造化出力定義
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# === Planner Output ===
class TaskStep(BaseModel):
    """実行計画の1ステップ"""
    id: int = Field(description="ステップ番号（1から始まる）")
    role: Literal["researcher", "storywriter", "visualizer", "coder", "data_analyst"] = Field(
        description="担当エージェント名"
    )
    instruction: str = Field(
        description="エージェントへの詳細な指示（トーン、対象読者、具体的な要件を含む）"
    )
    description: str = Field(description="このステップの概要説明")


class PlannerOutput(BaseModel):
    """Plannerノードの出力"""
    steps: List[TaskStep] = Field(description="実行計画のステップリスト")


# === Storywriter Output ===
class SlideContent(BaseModel):
    """スライド1枚分のコンテンツ"""
    slide_number: int = Field(description="スライド番号")
    title: str = Field(description="スライドのタイトル（短く印象的に）")
    bullet_points: List[str] = Field(
        description="箇条書きのリスト（各項目は20文字以内を推奨）"
    )
    key_message: Optional[str] = Field(
        default=None, 
        description="このスライドで伝えたい核心メッセージ（オプション）"
    )


class StorywriterOutput(BaseModel):
    """Storywriterノードの出力"""
    slides: List[SlideContent] = Field(description="スライドコンテンツのリスト")


# === Visualizer Output ===
class ThoughtSignature(BaseModel):
    """思考署名: 一貫性のある修正（Deep Edit）に必要な生成メタデータ"""
    seed: int = Field(description="生成に使用された乱数シード")
    base_prompt: str = Field(description="生成に使用されたベースプロンプト")
    refined_prompt: Optional[str] = Field(default=None, description="修正後のプロンプト（編集時）")
    model_version: str = Field(default="gemini-exp-1121", description="使用モデルバージョン")
    reference_image_url: Optional[str] = Field(default=None, description="使用されたリファレンス画像のURL")


class ImagePrompt(BaseModel):
    """画像生成プロンプト"""
    slide_number: int = Field(description="対象スライド番号")
    image_generation_prompt: str = Field(
        description="英語で記述された画像生成プロンプト。5つの要素（[Role], [Context], [Logic], [Style], [Constraints]）を明示的に含めること。"
    )
    rationale: str = Field(description="このビジュアルを選んだ理由（推論の根拠）")
    generated_image_url: Optional[str] = Field(default=None, description="生成的された画像のGCS URL（生成後に入力される）")
    thought_signature: Optional[ThoughtSignature] = Field(default=None, description="Deep Edit用の思考署名")



class GenerationConfig(BaseModel):
    """画像生成設定"""
    thinking_level: Literal["low", "high"] = Field(
        default="high",
        description="推論レベル (High: 複雑な図解, Low: 単純なアイコン)"
    )
    media_resolution: Literal["medium", "high"] = Field(
        default="high",
        description="解像度設定 (High: スライド用, Medium: プレビュー用)"
    )
    aspect_ratio: Literal["16:9", "4:3", "1:1"] = Field(
        default="16:9",
        description="強制アスペクト比"
    )
    reference_anchor: Optional[str] = Field(
        default=None,
        description="アスペクト比固定用のリファレンス画像（Base64またはURL）"
    )


class VisualizerOutput(BaseModel):
    """Visualizerノードの出力"""
    anchor_image_prompt: Optional[str] = Field(
        default=None,
        description="スライド全体のデザインスタイルを定義するアンカー画像用のプロンプト（テキストを含まない、背景やスタイルのみの画像）"
    )
    anchor_image_url: Optional[str] = Field(
        default=None,
        description="生成された（または既存の）Style Anchor画像のURL。Deep Edit時の再利用に使用。"
    )
    prompts: List[ImagePrompt] = Field(description="各スライド用の画像生成プロンプト")
    generation_config: GenerationConfig = Field(
        default_factory=lambda: GenerationConfig(
            thinking_level="high", 
            media_resolution="high", 
            aspect_ratio="16:9"
        ),
        description="画像生成エンジンの設定パラメータ"
    )
    seed: Optional[int] = Field(default=None, description="画像生成に使用するランダムシード（一貫性用）")
    parent_id: Optional[str] = Field(default=None, description="修正元の画像ID（編集時）")


# === Researcher Query Planner Output ===
class SearchQuery(BaseModel):
    """検索クエリ"""
    perspective: str = Field(description="調査観点（例: 市場規模、競合動向、規制環境）")
    query: str = Field(description="Google検索に投げるクエリ文字列（英語推奨）")
    priority: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="優先度"
    )


class QueryPlannerOutput(BaseModel):
    """Researcher内部のQuery Plannerの出力"""
    queries: List[SearchQuery] = Field(
        description="生成された検索クエリのリスト（最大10個）",
        max_length=10
    )
    synthesis_focus: str = Field(
        description="Synthesizerへの指示（どのような観点で統合するか）"
    )


# === Data Analyst Output ===
class DataPoint(BaseModel):
    label: str = Field(description="ラベル（例: 2020年, iPhone）")
    value: float | str = Field(description="値（数値またはテキスト）")

class VisualBlueprint(BaseModel):
    """視覚的設計図"""
    visual_type: Literal["bar_chart", "line_chart", "pie_chart", "flowchart", "infographic"] = Field(description="視覚化タイプ")
    title: str = Field(description="図のタイトル")
    data_series: List[DataPoint] = Field(description="データ系列")
    annotations: List[str] = Field(description="注釈リスト")
    design_notes: str = Field(description="デザイン上の注意点")

class DataAnalystOutput(BaseModel):
    """Data Analystノードの出力"""
    blueprints: List[VisualBlueprint] = Field(description="生成された視覚的設計図のリスト")


# === Reviewer Output ===
class ReviewOutput(BaseModel):
    """Reviewerノードの出力"""
    approved: bool = Field(description="品質基準を満たしているか否か")
    score: float = Field(description="品質スコア (0.0 - 1.0)")
    feedback: str = Field(description="改善のための具体的なフィードバック、または承認時のコメント")

