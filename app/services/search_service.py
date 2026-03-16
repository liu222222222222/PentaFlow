from typing import List, Dict, Optional
import httpx
import logging
from pydantic import BaseModel, Field
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings


logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """搜索结果模型"""
    title: str
    url: str
    content: str
    score: Optional[float] = None


class SearchService:
    """搜索服务 - 仅使用 Tavily API"""
    
    def __init__(self):
        self.settings = settings
        self.tavily_api_key = self.settings.tavily_api_key
        self.max_results = self.settings.max_search_results
        
        # 验证Tavily API key是否已配置
        if not self.tavily_api_key or not self.tavily_api_key.strip():
            raise ValueError(
                "Tavily API key未配置！\n"
                "请在 .env 文件中设置 TAVILY_API_KEY=your_tavily_api_key\n"
                "Tavily API密钥获取地址: https://tavily.com/"
            )
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {self.tavily_api_key}"}
        )
        self._last_api_key = self.tavily_api_key
    
    def _ensure_client_updated(self):
        """确保client使用最新的API key"""
        if self.settings.tavily_api_key != self._last_api_key:
            self.tavily_api_key = self.settings.tavily_api_key
            self.client = httpx.AsyncClient(
                timeout=30.0,
                headers={"Authorization": f"Bearer {self.tavily_api_key}"}
            )
            self._last_api_key = self.tavily_api_key
    
    async def search(self, query: str, perspective: str = "general", num_results: Optional[int] = None) -> List[SearchResult]:
        """执行搜索 - 仅使用 Tavily API"""
        self._ensure_client_updated()
        
        search_query = f"{query} {perspective}"
        limit = num_results or self.max_results
        
        try:
            logger.info(f"使用 Tavily API 搜索 '{query}'")
            response = await self.client.post(
                "https://api.tavily.com/search",
                json={
                    "query": search_query,
                    "search_depth": "advanced",
                    "include_answer": True,
                    "include_images": False,
                    "max_results": limit,
                    "include_domains": [],
                    "exclude_domains": []
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get("results", []):
                    result = SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        content=item.get("content", "")
                    )
                    results.append(result)
                
                logger.info(f"Tavily 搜索 '{query}' 返回 {len(results)} 个结果")
                return results
            else:
                error_msg = f"Tavily API 请求失败: HTTP {response.status_code}"
                logger.error(error_msg)
                raise ConnectionError(error_msg)
                
        except httpx.HTTPError as e:
            error_msg = f"Tavily API 连接错误: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg)
        except Exception as e:
            error_msg = f"Tavily API 搜索失败: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg)
    
    async def search_with_summary(self, query: str, perspective: str = "general") -> Dict:
        """搜索并生成摘要"""
        results = await self.search(query, perspective)
        
        if not results:
            return {
                "query": query,
                "results": [],
                "summary": f"未找到关于 '{query}' 的相关信息"
            }
        
        # 摘要前几个结果
        summary_content = "\n".join([f"• {r.title}: {r.content[:150]}..." for r in results[:3]])
        
        return {
            "query": query,
            "results": results,
            "summary": f"找到 {len(results)} 条关于 '{query}' 的信息:\n{summary_content}"
        }
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局实例
_search_service: Optional[SearchService] = None
_last_tavily_api_key: Optional[str] = None


async def get_search_service() -> SearchService:
    """获取搜索服务实例"""
    global _search_service, _last_tavily_api_key
    
    current_api_key = settings.tavily_api_key
    
    # 检查 API key 是否变化或实例未创建
    if _search_service is None or _last_tavily_api_key != current_api_key:
        logger.info(f"Tavily API key 已变化或首次初始化，创建新的搜索服务实例")
        _search_service = SearchService()
        _last_tavily_api_key = current_api_key
    else:
        logger.debug(f"使用缓存的搜索服务实例（API key 未变化）")
    
    return _search_service
