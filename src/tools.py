"""AnimaLearn — Pydantic Tool Schemas"""
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator

class GenerateTTSInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    output_path: str = Field(...)
    voice: str = Field(default="en-US-AriaNeural")

class GenerateTTSOutput(BaseModel):
    audio_path: str; duration_seconds: float; word_count: int

class GenerateAnimationInput(BaseModel):
    prompt: str = Field(..., min_length=1, description="Scene description for AI video generation")
    background_color: str = Field(default="#0b3d91")
    text_overlay: str = Field(default="")
    output_path: str = Field(...)
    duration_seconds: int = Field(default=5, ge=2, le=16)

class GenerateAnimationOutput(BaseModel):
    video_path: str; duration_seconds: float; method: str

class GenerateAvatarInput(BaseModel):
    text: str = Field(..., min_length=1, description="Narration text for the avatar to speak")
    output_path: str = Field(...)
    avatar_image_url: str = Field(default="", description="URL of face image; empty = default avatar")

class GenerateAvatarOutput(BaseModel):
    video_path: str; duration_seconds: float; method: str

class ComposeVideoInput(BaseModel):
    clip_paths: list[str] = Field(..., min_length=1, description="Ordered list of video/image clip paths")
    audio_paths: list[str] = Field(default_factory=list)
    output_path: str = Field(...)

class ComposeVideoOutput(BaseModel):
    video_path: str; duration_seconds: float; num_clips: int

class BurnSubtitlesInput(BaseModel):
    video_path: str = Field(...)
    subtitles: list[dict] = Field(..., min_length=1)
    output_path: str = Field(...)

class BurnSubtitlesOutput(BaseModel):
    video_path: str; num_subtitles: int

class FetchReferenceInput(BaseModel):
    url: str = Field(..., min_length=10)
    max_tokens: int = Field(default=15000)

class FetchReferenceOutput(BaseModel):
    text: str; source_url: str; token_count: int; title: str

def validate_tool_input(schema_class, raw_input):
    try:
        return schema_class(**raw_input), None
    except Exception as e:
        return None, f"Validation error: {e}"
