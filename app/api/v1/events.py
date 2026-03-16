from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio
import logging
from datetime import datetime
import uuid
import sys
import os
# 添加项目根路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.models.metrics import EventModel
from app.services.search_service import get_search_service
from app.services.llm_service import get_llm_service
from config import settings


logger = logging.getLogger(__name__)


router = APIRouter()


class EventRequest(BaseModel):
    name: str
    llm_api_key: Optional[str] = ""
    search_api_key: Optional[str] = ""


class EventEnrichmentResponse(BaseModel):
    name: str
    description: str
    category: str
    key_points: List[str] = []


class AnalysisRequest(BaseModel):
    event: EventModel


@router.post("/events/enrich", response_model=EventEnrichmentResponse)
async def enrich_event(event_request: EventRequest):
    """根据事件名称补全信息"""
    try:
        logger.info(f"开始处理事件补全请求: {event_request.name}")
        logger.info(f"收到的LLM API Key: {'有' if event_request.llm_api_key else '无'}")
        logger.info(f"收到的搜索API Key: {'有' if event_request.search_api_key else '无'}")
        
        # 强制设置API key到settings（只在用户提供了新的 key 时才更新）
        if event_request.llm_api_key:
            settings.llm_api_key = event_request.llm_api_key
            logger.info(f"使用用户提供的LLM API Key")
        else:
            logger.info(f"使用默认LLM API Key（用户未提供）")
        
        if event_request.search_api_key:
            settings.tavily_api_key = event_request.search_api_key
            logger.info(f"使用用户提供的搜索API Key")
        else:
            logger.info(f"使用默认搜索API Key（用户未提供）")
        
        search_service = await get_search_service()
        llm_service = await get_llm_service()
        
        event_name = event_request.name.strip()
        if not event_name:
            raise HTTPException(status_code=400, detail="事件名称不能为空")
        
        # 搜索相关信息
        search_results = await search_service.search(
            f"{event_name} AI 影响 介绍 最新进展",
            num_results=5
        )
        
        logger.info(f"搜索结果数量: {len(search_results)}")
        
        # 使用 LLM 分析并补全信息
        search_context = "\n".join([
            f"{i+1}. {r.title}\n{r.content[:200]}..."
            for i, r in enumerate(search_results[:3])
        ])
        
        system_prompt = """你是一个专业的 AI 行业信息整理助手。
请根据提供的事件名称和搜索结果，生成完整的事件描述、类别和关键点。

返回严格的 JSON 格式：
{
    "description": "事件的详细描述，包括技术特点、影响范围、市场意义等，100-200字",
    "category": "选择一个最合适的类别: 技术突破/产品发布/政策法规/行业应用/投资并购/其他",
    "key_points": ["关键点1", "关键点2", "关键点3"]
}"""
        
        user_prompt = f"""事件名称: {event_name}

搜索结果参考:
{search_context}

请生成完整的事件描述、类别和关键点，确保返回有效的JSON格式。"""
        
        try:
            response = await llm_service.completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # 打印LLM响应以便调试
            logger.info(f"LLM 响应: {response[:500]}...")
            
        except Exception as llm_error:
            logger.error(f"LLM 调用失败: {llm_error}", exc_info=True)
            # 如果LLM调用失败，直接从搜索结果中提取信息
            if search_results:
                description = f"{event_name}: {search_results[0].title}. {search_results[0].content[:100]}..."
                category = "其他"
                key_points = [r.title for r in search_results[:3]]
            else:
                description = f"{event_name}是近期AI领域的重要事件，引发了行业广泛关注。"
                category = "其他"
                key_points = []
            
            logger.info(f"使用搜索结果作为备选方案")
            return EventEnrichmentResponse(
                name=event_name,
                description=description,
                category=category,
                key_points=key_points
            )
        
        # 尝试解析 LLM 返回的 JSON
        import json
        import re
        
        # 初始化默认值
        description = ""
        category = "其他"
        key_points = []
        
        try:
            # 从响应中提取 JSON 部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group()
                    result_data = json.loads(json_str)
                    
                    description = result_data.get("description", "")
                    category = result_data.get("category", "其他")
                    key_points = result_data.get("key_points", [])
                    
                    logger.info(f"成功解析 JSON: description={description[:50]}..., category={category}, key_points={len(key_points)}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 解析失败: {e}, JSON内容: {json_str[:200]}...", exc_info=True)
                    # 如果 JSON 解析失败，尝试从搜索结果中提取信息
                    if search_results:
                        description = f"{event_name}: {search_results[0].title}. {search_results[0].content[:100]}..."
                        category = "其他"
                        key_points = [r.title for r in search_results[:3]]
                    else:
                        description = f"{event_name}是近期AI领域的重要事件，引发了行业广泛关注。"
                        category = "其他"
                        key_points = []
            else:
                logger.warning("未找到 JSON 格式，尝试从搜索结果中提取信息")
                # 如果没有找到 JSON，尝试从搜索结果中提取信息
                if search_results:
                    description = f"{event_name}: {search_results[0].title}. {search_results[0].content[:100]}..."
                    category = "其他"
                    key_points = [r.title for r in search_results[:3]]
                else:
                    description = f"{event_name}是近期AI领域的重要事件，引发了行业广泛关注。"
                    category = "其他"
                    key_points = []
            
            # 确保描述不为空
            if not description:
                description = f"{event_name}是近期AI领域的重要事件，引发了行业广泛关注。"
            
            logger.info(f"事件补全成功: {event_name}")
            return EventEnrichmentResponse(
                name=event_name,
                description=description,
                category=category,
                key_points=key_points
            )
            
        except Exception as parse_error:
            logger.error(f"解析处理失败: {parse_error}", exc_info=True)
            # 最后的备选方案
            if search_results:
                description = f"{event_name}: {search_results[0].title}. {search_results[0].content[:100]}..."
                category = "其他"
                key_points = [r.title for r in search_results[:3]]
            else:
                description = f"{event_name}是近期AI领域的重要事件，引发了行业广泛关注。"
                category = "其他"
                key_points = []
            
            logger.info(f"使用最后的备选方案")
            return EventEnrichmentResponse(
                name=event_name,
                description=description,
                category=category,
                key_points=key_points
            )
        
    except HTTPException:
        # 重新抛出HTTPException
        raise
    except Exception as e:
        logger.error(f"事件补全失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"事件补全失败: {str(e)}")


@router.get("/events/sample")
async def get_sample_events():
    """获取示例事件"""
    sample_events = [
        {
            "id": "seedance_2.0",
            "name": "Seedance 2.0 发布",
            "description": "字节跳动推出 Seedance 2.0，支持更高质量的 AI 视频生成，引发视频内容创作革命",
            "category": "产品发布"
        },
        {
            "id": "gpt-5",
            "name": "GPT-5 发布",
            "description": "OpenAI 发布 GPT-5，性能大幅提升，支持多模态理解和生成",
            "category": "技术突破"
        },
        {
            "id": "ai-regulation",
            "name": "AI 监管法案通过",
            "description": "多国联合通过 AI 监管法案，要求所有 AI 系统必须通过安全审查和伦理评估",
            "category": "政策法规"
        }
    ]
    return {"events": sample_events}