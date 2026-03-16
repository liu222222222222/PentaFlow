from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """应用配置设置"""
    
    # API 配置 - 必需配置
    llm_api_key: str = Field(..., env="LLM_API_KEY", description="阿里云DashScope API密钥（必需）")
    llm_base_url: str = Field(default="https://coding.dashscope.aliyuncs.com/v1", env="LLM_BASE_URL", description="LLM API基础URL")
    llm_model: str = Field(default="qwen3.5-plus", env="LLM_MODEL", description="LLM模型名称")
    tavily_api_key: str = Field(..., env="TAVILY_API_KEY", description="Tavily搜索API密钥（必需）")
    
    # 应用配置
    app_name: str = "PentaFlow 五维推演"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # 推演配置
    max_rounds: int = Field(default=5, env="MAX_ROUNDS")
    min_rounds: int = Field(default=3, env="MIN_ROUNDS")
    target_score_threshold: float = Field(default=0.80, env="TARGET_SCORE_THRESHOLD")
    convergence_threshold: float = Field(default=0.03, env="CONVERGENCE_THRESHOLD")
    
    # 搜索配置
    max_search_results: int = Field(default=5, env="MAX_SEARCH_RESULTS")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # 路径配置
    data_dir: Path = Path("data")
    log_dir: Path = Path("logs")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )
    
    @model_validator(mode='after')
    def validate_required_keys(self) -> 'Settings':
        """验证必需的API keys"""
        if not self.llm_api_key or not self.llm_api_key.strip():
            raise ValueError(
                "LLM_API_KEY 是必需的配置项！\n"
                "请在 .env 文件中设置 LLM_API_KEY=your_dashscope_api_key\n"
                "阿里云DashScope API密钥获取地址: https://dashscope.console.aliyun.com/apiKey"
            )
        
        if not self.tavily_api_key or not self.tavily_api_key.strip():
            raise ValueError(
                "TAVILY_API_KEY 是必需的配置项！\n"
                "请在 .env 文件中设置 TAVILY_API_KEY=your_tavily_api_key\n"
                "Tavily API密钥获取地址: https://tavily.com/"
            )
        
        return self


# 全局配置实例
settings = Settings()

def get_settings() -> Settings:
    """获取配置实例"""
    return settings