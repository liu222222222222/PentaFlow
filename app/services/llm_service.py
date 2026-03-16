from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings
import json
import asyncio
import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """LLM 响应模型"""
    content: str
    reasoning: str = ""
    scores: Dict[str, float] = Field(default_factory=dict)
    raw_response: Optional[Any] = None
    success: bool = True
    error: str = ""


class LLMService:
    """LLM 服务 - 使用 FastAPI 和 Pydantic 重构"""
    
    def __init__(self):
        self.settings = settings
        
        # 验证LLM API key是否已配置
        if not self.settings.llm_api_key or not self.settings.llm_api_key.strip():
            raise ValueError(
                "LLM API key未配置！\n"
                "请在 .env 文件中设置 LLM_API_KEY=your_dashscope_api_key\n"
                "阿里云DashScope API密钥获取地址: https://dashscope.console.aliyun.com/apiKey"
            )
        
        self.client = AsyncOpenAI(
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url
        )
        self.model = self.settings.llm_model
        self._last_api_key = self.settings.llm_api_key
    
    def _ensure_client_updated(self):
        """确保client使用最新的API key"""
        if self.settings.llm_api_key != self._last_api_key:
            self.client = AsyncOpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url
            )
            self._last_api_key = self.settings.llm_api_key
    
    async def completion(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """兼容旧的completion方法"""
        self._ensure_client_updated()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000),
                response_format=kwargs.get("response_format", {"type": "text"})
            )
            
            content = response.choices[0].message.content
            return content
        except Exception as e:
            error_msg = f"LLM 调用失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ConnectionError(error_msg)

    async def chat_completion(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """异步聊天完成"""
        self._ensure_client_updated()
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000),
                response_format=kwargs.get("response_format", {"type": "text"})
            )
            
            content = response.choices[0].message.content
            return LLMResponse(
                content=content,
                reasoning=content,
                success=True
            )
        except Exception as e:
            logger.error(f"LLM 调用失败: {str(e)}")
            return LLMResponse(
                content="",
                success=False,
                error=str(e)
            )
    
    async def structured_completion(
        self, 
        system_prompt: str, 
        user_prompt: str,
        expected_scores: Optional[List[str]] = None
    ) -> LLMResponse:
        """结构化输出完成 - 用于智能体评分"""
        self._ensure_client_updated()
        
        try:
            # 如果期望特定评分维度，则在提示中明确要求
            if expected_scores:
                scores_format = ', '.join([f'"{score}": 0.0' for score in expected_scores])
                user_prompt += f"\n\n请返回以下维度的评分 (0.0-1.0): {', '.join(expected_scores)}\n格式: {{\"scores\": {{{scores_format}}}, \"reasoning\": \"分析推理过程...\"}}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # 评分任务使用较低温度以获得更一致的结果
                max_tokens=2000,
                response_format={"type": "json_object"}  # 要求 JSON 格式输出
            )
            
            content = response.choices[0].message.content
            parsed_response = self._parse_structured_response(content)
            
            return LLMResponse(
                content=content,
                reasoning=parsed_response.get("reasoning", ""),
                scores=parsed_response.get("scores", {}),
                success=True
            )
        except Exception as e:
            logger.error(f"结构化 LLM 调用失败: {str(e)}")
            # 返回默认评分，但不抛出错误，系统继续运行
            default_scores = {score: 0.5 for score in expected_scores or []}
            return LLMResponse(
                content="",
                reasoning=f"评分过程中出现错误: {str(e)}，使用默认评分",
                scores=default_scores,
                success=False,
                error=str(e)
            )
    
    def _parse_structured_response(self, content: str) -> Dict:
        """解析结构化响应"""
        try:
            # 尝试直接解析 JSON
            data = json.loads(content)
            return data
        except json.JSONDecodeError:
            # 尝试提取 JSON 部分
            try:
                start = content.find('{')
                end = content.rfind('}') + 1
                if start != -1 and end > start:
                    json_part = content[start:end]
                    return json.loads(json_part)
            except:
                pass
        
        # 如果都失败，返回空字典
        return {"reasoning": content, "scores": {}}
    
    async def validate_connection(self) -> bool:
        """验证 LLM 连接"""
        try:
            response = await self.chat_completion([
                {"role": "user", "content": "Hello, test connection."}
            ])
            return response.success
        except:
            return False


# 全局实例
_llm_service: Optional[LLMService] = None
_last_api_key: Optional[str] = None


async def get_llm_service() -> LLMService:
    """获取 LLM 服务实例"""
    global _llm_service, _last_api_key
    
    current_api_key = settings.llm_api_key
    
    # 检查 API key 是否变化或实例未创建
    if _llm_service is None or _last_api_key != current_api_key:
        logger.info(f"API key 已变化或首次初始化，创建新的 LLM 服务实例")
        _llm_service = LLMService()
        _last_api_key = current_api_key
        # 验证连接
        if not await _llm_service.validate_connection():
            logger.warning("LLM 服务连接验证失败")
    else:
        logger.debug(f"使用缓存的 LLM 服务实例（API key 未变化）")
    
    return _llm_service
