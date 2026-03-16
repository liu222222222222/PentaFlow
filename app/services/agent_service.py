from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings
from .llm_service import get_llm_service
from .search_service import get_search_service
from ..models.metrics import ImpactMetrics


class AgentOpinion(BaseModel):
    """智能体观点模型"""
    agent_name: str
    perspective: str
    scores: Dict[str, float] = Field(default_factory=dict)
    reasoning: str = ""
    evidence: List[str] = Field(default_factory=list)
    round: int = 1
    timestamp: Optional[str] = None


class AgentProfile(BaseModel):
    """智能体画像"""
    name: str
    perspective: str
    description: str
    key_concerns: List[str] = Field(default_factory=list)
    evaluation_dimensions: List[str] = Field(default_factory=list)
    icon: str = "🤖"


class BaseAgent(ABC):
    """智能体基类 - 重构为异步版本"""
    
    def __init__(self, profile: AgentProfile):
        self.profile = profile
        self.name = profile.name
        self.perspective = profile.perspective
        self.knowledge_base = []
        self.search_history = []
        self.progress_callback = None
    
    @abstractmethod
    async def analyze(self, event: Dict, round_num: int, previous_metrics: Optional[Dict], other_opinions: Optional[List[Dict]] = None) -> AgentOpinion:
        """异步分析方法"""
        pass
    
    async def search_information(self, query: str) -> List[Dict]:
        """异步搜索信息"""
        # 发送搜索状态
        if hasattr(self, 'progress_callback') and self.progress_callback:
            await self.progress_callback({
                "status": "agent_searching",
                "agent_name": self.name,
                "query": query,
                "perspective": self.perspective
            })
        
        search_service = await get_search_service()
        results = await search_service.search(query, self.perspective)
        
        search_result = []
        for result in results:
            search_result.append({
                "title": result.title,
                "url": result.url,
                "content": result.content
            })
        
        self.search_history.append({
            "round": len(self.search_history) + 1,
            "query": query,
            "results_count": len(results)
        })
        
        # 发送搜索完成状态
        if hasattr(self, 'progress_callback') and self.progress_callback:
            await self.progress_callback({
                "status": "agent_search_completed",
                "agent_name": self.name,
                "query": query,
                "results_count": len(results)
            })
        
        return search_result


class CapitalAgent(BaseAgent):
    """资本代言人 - 重构版"""
    
    def __init__(self):
        profile = AgentProfile(
            name="资本代言人",
            perspective="资本",
            description="代表投资机构和资本市场的视角，关注商业价值、变现能力、投资回报率、市场份额和增长潜力。",
            key_concerns=["商业价值", "投资回报", "市场规模", "竞争格局", "盈利模式"],
            evaluation_dimensions=["economic_disruption", "employment_volatility"],
            icon="🏦"
        )
        super().__init__(profile)
    
    async def analyze(self, event: Dict, round_num: int, previous_metrics: Optional[Dict], other_opinions: Optional[List[Dict]] = None) -> AgentOpinion:
        """执行资本视角分析"""
        # 搜索相关信息
        search_results = await self.search_information(f"{event['name']} 资本影响 市场规模 投资价值")
        
        # 构建系统提示
        system_prompt = f"""你是一个专业的资本分析师，代表投资机构和资本市场的视角。
关注商业价值、变现能力、投资回报率、市场份额和增长潜力。
评估团队背景、融资历史和退出前景。
请基于提供的信息进行分析并返回JSON格式的评估结果。"""
        
        # 构建用户提示
        user_prompt = f"""事件: {event['name']}
描述: {event['description']}
类别: {event['category']}

搜索结果:
{self._format_search_results(search_results)}

请分析该事件的资本影响，重点关注经济颠覆度和就业波动率两个维度，给出 0.0-1.0 的评分。

返回格式:
{{
    "reasoning": "分析推理过程...",
    "scores": {{
        "economic_disruption": 0.0,
        "employment_volatility": 0.0
    }}
}}"""
        
        # 调用 LLM
        llm_service = await get_llm_service()
        response = await llm_service.structured_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            expected_scores=["economic_disruption", "employment_volatility"]
        )
        
        return AgentOpinion(
            agent_name=self.name,
            perspective=self.perspective,
            scores=response.scores,
            reasoning=response.reasoning,
            evidence=[r['content'][:100] for r in search_results[:2]]
        )
    
    def _format_search_results(self, results: List[Dict]) -> str:
        """格式化搜索结果"""
        formatted = []
        for i, result in enumerate(results[:3]):
            formatted.append(f"{i+1}. {result['title']}\n{result['content'][:200]}...")
        return "\n".join(formatted)


class TechnologyAgent(BaseAgent):
    """技术执行者 - 重构版"""
    
    def __init__(self):
        profile = AgentProfile(
            name="技术执行者",
            perspective="技术",
            description="代表工程师和技术团队的视角，关注技术可行性、工程实现难度、系统架构和可扩展性。",
            key_concerns=["技术可行性", "工程实现", "系统架构", "可扩展性", "技术栈"],
            evaluation_dimensions=["technology_penetration", "process_reconstruction"],
            icon="🔧"
        )
        super().__init__(profile)
    
    async def analyze(self, event: Dict, round_num: int, previous_metrics: Optional[Dict], other_opinions: Optional[List[Dict]] = None) -> AgentOpinion:
        """执行技术视角分析"""
        search_results = await self.search_information(f"{event['name']} 技术特点 实现难度 架构设计")
        
        system_prompt = f"""你是一个资深技术专家，代表工程师和技术团队的视角。
关注技术可行性、工程实现难度、代码质量、系统架构和可扩展性。
评估技术栈先进性、人才密度和开源贡献。
请基于提供的信息进行分析并返回JSON格式的评估结果。"""
        
        user_prompt = f"""事件: {event['name']}
描述: {event['description']}
类别: {event['category']}

搜索结果:
{self._format_search_results(search_results)}

请分析该事件的技术影响，重点关注技术渗透率和流程重构度两个维度，给出 0.0-1.0 的评分。

返回格式:
{{
    "reasoning": "分析推理过程...",
    "scores": {{
        "technology_penetration": 0.0,
        "process_reconstruction": 0.0
    }}
}}"""
        
        llm_service = await get_llm_service()
        response = await llm_service.structured_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            expected_scores=["technology_penetration", "process_reconstruction"]
        )
        
        return AgentOpinion(
            agent_name=self.name,
            perspective=self.perspective,
            scores=response.scores,
            reasoning=response.reasoning,
            evidence=[r['content'][:100] for r in search_results[:2]]
        )
    
    def _format_search_results(self, results: List[Dict]) -> str:
        formatted = []
        for i, result in enumerate(results[:3]):
            formatted.append(f"{i+1}. {result['title']}\n{result['content'][:200]}...")
        return "\n".join(formatted)


class CreativeAgent(BaseAgent):
    """创意指挥官 - 重构版"""
    
    def __init__(self):
        profile = AgentProfile(
            name="创意指挥官",
            perspective="营销",
            description="代表品牌、营销和创意行业的视角，关注品牌认知度、传播力和文化影响力。",
            key_concerns=["品牌认知", "传播力", "用户体验", "设计美感", "情感连接"],
            evaluation_dimensions=["economic_disruption", "process_reconstruction"],
            icon="🎨"
        )
        super().__init__(profile)
    
    async def analyze(self, event: Dict, round_num: int, previous_metrics: Optional[Dict], other_opinions: Optional[List[Dict]] = None) -> AgentOpinion:
        """执行创意视角分析"""
        search_results = await self.search_information(f"{event['name']} 品牌影响 营销策略 用户反馈")
        
        system_prompt = f"""你是一个创意总监，代表品牌、营销和创意行业的视角。
关注品牌认知度、传播力和文化影响力。
重视用户体验、设计美感和情感连接。
评估内容创意、叙事能力和病毒式传播潜力。
请基于提供的信息进行分析并返回JSON格式的评估结果。"""
        
        user_prompt = f"""事件: {event['name']}
描述: {event['description']}
类别: {event['category']}

搜索结果:
{self._format_search_results(search_results)}

请分析该事件的创意营销影响，重点关注经济颠覆度和流程重构度两个维度，给出 0.0-1.0 的评分。

返回格式:
{{
    "reasoning": "分析推理过程...",
    "scores": {{
        "economic_disruption": 0.0,
        "process_reconstruction": 0.0
    }}
}}"""
        
        llm_service = await get_llm_service()
        response = await llm_service.structured_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            expected_scores=["economic_disruption", "process_reconstruction"]
        )
        
        return AgentOpinion(
            agent_name=self.name,
            perspective=self.perspective,
            scores=response.scores,
            reasoning=response.reasoning,
            evidence=[r['content'][:100] for r in search_results[:2]]
        )
    
    def _format_search_results(self, results: List[Dict]) -> str:
        formatted = []
        for i, result in enumerate(results[:3]):
            formatted.append(f"{i+1}. {result['title']}\n{result['content'][:200]}...")
        return "\n".join(formatted)


class SocialAgent(BaseAgent):
    """社会观察员 - 重构版"""
    
    def __init__(self):
        profile = AgentProfile(
            name="社会观察员",
            perspective="社会",
            description="代表公众、社会和伦理视角，关注 AI 对社会的影响、伦理问题和公众接受度。",
            key_concerns=["社会影响", "伦理问题", "公众接受度", "隐私保护", "算法公平性"],
            evaluation_dimensions=["ethical_risk", "employment_volatility"],
            icon="👁️"
        )
        super().__init__(profile)
    
    async def analyze(self, event: Dict, round_num: int, previous_metrics: Optional[Dict], other_opinions: Optional[List[Dict]] = None) -> AgentOpinion:
        """执行社会视角分析"""
        search_results = await self.search_information(f"{event['name']} 社会影响 伦理问题 公众反应")
        
        # 整合其他智能体观点
        context_info = ""
        if other_opinions:
            context_info = "\n其他智能体的观点：\n"
            for op in other_opinions:
                if op['agent_name'] != '社会观察员':
                    context_info += f"【{op['agent_name']}】{op['reasoning']}\n"
        
        system_prompt = f"""你是一个社会学家，代表公众、社会和伦理视角。
关注 AI 对社会的影响、伦理问题和公众接受度。
重视隐私保护、算法公平性和透明度。
评估就业影响、数字鸿沟和社会责任。
请基于提供的信息进行分析并返回JSON格式的评估结果。"""
        
        user_prompt = f"""事件: {event['name']}
描述: {event['description']}
类别: {event['category']}
{context_info}
搜索结果:
{self._format_search_results(search_results)}

请分析该事件的社会影响，重点关注伦理风险值和就业波动率两个维度，给出 0.0-1.0 的评分。

返回格式:
{{
    "reasoning": "分析推理过程...",
    "scores": {{
        "ethical_risk": 0.0,
        "employment_volatility": 0.0
    }}
}}"""
        
        llm_service = await get_llm_service()
        response = await llm_service.structured_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            expected_scores=["ethical_risk", "employment_volatility"]
        )
        
        return AgentOpinion(
            agent_name=self.name,
            perspective=self.perspective,
            scores=response.scores,
            reasoning=response.reasoning,
            evidence=[r['content'][:100] for r in search_results[:2]]
        )
    
    def _format_search_results(self, results: List[Dict]) -> str:
        formatted = []
        for i, result in enumerate(results[:3]):
            formatted.append(f"{i+1}. {result['title']}\n{result['content'][:200]}...")
        return "\n".join(formatted)


class PolicyAgent(BaseAgent):
    """政策监管者 - 重构版"""
    
    def __init__(self):
        profile = AgentProfile(
            name="政策监管者",
            perspective="政策",
            description="代表政府部门、监管机构和立法者的视角，关注合规性、安全可控和国家战略契合度。",
            key_concerns=["合规性", "安全可控", "国家战略", "数据主权", "内容安全"],
            evaluation_dimensions=["ethical_risk", "process_reconstruction"],
            icon="⚖️"
        )
        super().__init__(profile)
    
    async def analyze(self, event: Dict, round_num: int, previous_metrics: Optional[Dict], other_opinions: Optional[List[Dict]] = None) -> AgentOpinion:
        """执行政策视角分析"""
        search_results = await self.search_information(f"{event['name']} 政策法规 合规要求 安全监管")
        
        system_prompt = f"""你是一个政策专家，代表政府部门、监管机构和立法者的视角。
关注合规性、安全可控和国家战略契合度。
重视数据主权、内容安全和产业健康发展。
评估对国家安全、公共利益的影响。
请基于提供的信息进行分析并返回JSON格式的评估结果。"""
        
        user_prompt = f"""事件: {event['name']}
描述: {event['description']}
类别: {event['category']}

搜索结果:
{self._format_search_results(search_results)}

请分析该事件的政策影响，重点关注伦理风险值和流程重构度两个维度，给出 0.0-1.0 的评分。

返回格式:
{{
    "reasoning": "分析推理过程...",
    "scores": {{
        "ethical_risk": 0.0,
        "process_reconstruction": 0.0
    }}
}}"""
        
        llm_service = await get_llm_service()
        response = await llm_service.structured_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            expected_scores=["ethical_risk", "process_reconstruction"]
        )
        
        return AgentOpinion(
            agent_name=self.name,
            perspective=self.perspective,
            scores=response.scores,
            reasoning=response.reasoning,
            evidence=[r['content'][:100] for r in search_results[:2]]
        )
    
    def _format_search_results(self, results: List[Dict]) -> str:
        formatted = []
        for i, result in enumerate(results[:3]):
            formatted.append(f"{i+1}. {result['title']}\n{result['content'][:200]}...")
        return "\n".join(formatted)


class UserAgent(BaseAgent):
    """用户代表 - 重构版"""
    
    def __init__(self):
        profile = AgentProfile(
            name="用户代表",
            perspective="用户",
            description="代表终端用户、消费者和实际使用者的视角，关注产品易用性、实际价值和性价比。",
            key_concerns=["易用性", "实用价值", "用户体验", "服务质量", "问题解决"],
            evaluation_dimensions=["technology_penetration", "process_reconstruction"],
            icon="👤"
        )
        super().__init__(profile)
    
    async def analyze(self, event: Dict, round_num: int, previous_metrics: Optional[Dict], other_opinions: Optional[List[Dict]] = None) -> AgentOpinion:
        """执行用户视角分析"""
        search_results = await self.search_information(f"{event['name']} 用户体验 实际使用 价值反馈")
        
        system_prompt = f"""你是一个用户体验专家，代表终端用户、消费者和实际使用者的视角。
关注产品易用性、实际价值和性价比。
重视用户体验、服务质量和问题解决效率。
评估是否真正满足日常需求。
请基于提供的信息进行分析并返回JSON格式的评估结果。"""
        
        user_prompt = f"""事件: {event['name']}
描述: {event['description']}
类别: {event['category']}

搜索结果:
{self._format_search_results(search_results)}

请分析该事件的用户影响，重点关注技术渗透率和流程重构度两个维度，给出 0.0-1.0 的评分。

返回格式:
{{
    "reasoning": "分析推理过程...",
    "scores": {{
        "technology_penetration": 0.0,
        "process_reconstruction": 0.0
    }}
}}"""
        
        llm_service = await get_llm_service()
        response = await llm_service.structured_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            expected_scores=["technology_penetration", "process_reconstruction"]
        )
        
        return AgentOpinion(
            agent_name=self.name,
            perspective=self.perspective,
            scores=response.scores,
            reasoning=response.reasoning,
            evidence=[r['content'][:100] for r in search_results[:2]]
        )
    
    def _format_search_results(self, results: List[Dict]) -> str:
        formatted = []
        for i, result in enumerate(results[:3]):
            formatted.append(f"{i+1}. {result['title']}\n{result['content'][:200]}...")
        return "\n".join(formatted)


class BystanderAgent(BaseAgent):
    """旁观者 - 重构版"""
    
    def __init__(self):
        profile = AgentProfile(
            name="旁观者",
            perspective="独立",
            description="独立观察者，综合各方观点进行分析总结，识别共识和冲突点。",
            key_concerns=["综合分析", "共识识别", "冲突识别", "趋势分析", "风险评估"],
            evaluation_dimensions=["technology_penetration", "economic_disruption", "employment_volatility", "process_reconstruction", "ethical_risk"],
            icon="🤔"
        )
        super().__init__(profile)
    
    async def analyze(self, event: Dict, round_num: int, previous_metrics: Optional[Dict], other_opinions: Optional[List[Dict]] = None) -> AgentOpinion:
        """执行旁观者综合分析"""
        search_results = await self.search_information(f"{event['name']} 专家观点 综合分析 行业趋势")
        
        system_prompt = """你是一名拥有上帝视角的**首席行业分析师**。你不代表任何利益集团（非资本、非技术、非用户），你的唯一任务是**综合所有其他智能体的观点**，结合历史演变趋势，对事件进行**全局性、客观的复盘与总结**。

你是沙盘推演中的"定海神针"，负责在每一轮结束后，理清混乱的博弈，指出真正的共识与分歧，并给出最接近事实真相的综合评分。

**关键职责**：
1. **观点聚合**：阅读并理解其他所有角色（资本、技术、创意、社会、政策、用户）的发言和评分。
2. **冲突识别**：明确指出哪些维度上大家意见一致（共识），哪些维度上存在巨大分歧（冲突），并分析原因。
3. **趋势研判**：结合前一轮总结和上一轮数据，判断事态是升级了、缓和了还是发生了转折。
4. **全维打分**：基于综合分析，独立给出五个维度的最终修正评分（0.0-1.0）。你的评分应具有最高的权重参考价值。

**思维链**：
- **Step 1 [回顾]**：上一轮的核心结论是什么？现在的局势相比上一轮有什么变化？
- **Step 2 [横向对比]**：资本方是否过于乐观？技术方是否忽略了落地难点？社会方是否过度恐慌？谁的观点最符合当前事实？
- **Step 3 [纵向演进]**：随着推演轮次增加，该技术的冲击是增强了还是减弱了？
- **Step 4 [综合决策]**：基于上述分析，调整五个维度的分数。如果某两个角色观点截然相反，需根据客观事实判断谁更合理，并在推理中说明。"""
        
        previous_info = ""
        if previous_metrics:
            previous_info = f"\n上一轮指标: {previous_metrics}"
        
        # 如果有前一轮的总结，将其包含在输入中
        previous_summary = event.get("previous_summary", "")
        summary_info = ""
        if previous_summary:
            summary_info = f"\n前一轮旁观者总结: {previous_summary}"
        
        # 汇总其他智能体的观点
        opinions_info = ""
        if other_opinions:
            opinions_info = "\n其他智能体的观点：\n"
            for op in other_opinions:
                if op['agent_name'] != '旁观者':
                    opinions_info += f"【{op['agent_name']}】{op['reasoning']}\n"
        
        user_prompt = f"""事件: {event['name']}
描述: {event['description']}
类别: {event['category']}
轮次: 第 {round_num} 轮
{previous_info}
{summary_info}
{opinions_info}

搜索结果:
{self._format_search_results(search_results)}

请进行综合分析，对所有五个维度进行评估，给出 0.0-1.0 的评分。

返回格式（严格JSON格式）:
{{
    "reasoning": "综合分析报告：1. 本轮核心态势总结；2. 主要共识点（哪些角色看法一致）；3. 关键冲突点（哪些角色存在分歧及原因）；4. 相比上一轮的演变趋势。",
    "scores": {{
        "technology_penetration": 0.0,
        "economic_disruption": 0.0,
        "employment_volatility": 0.0,
        "process_reconstruction": 0.0,
        "ethical_risk": 0.0
    }}
}}"""
        
        llm_service = await get_llm_service()
        response = await llm_service.structured_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            expected_scores=["technology_penetration", "economic_disruption", "employment_volatility", "process_reconstruction", "ethical_risk"]
        )
        
        return AgentOpinion(
            agent_name=self.name,
            perspective=self.perspective,
            scores=response.scores,
            reasoning=response.reasoning,
            evidence=[r['content'][:100] for r in search_results[:2]]
        )
    
    def _format_search_results(self, results: List[Dict]) -> str:
        formatted = []
        for i, result in enumerate(results[:3]):
            formatted.append(f"{i+1}. {result['title']}\n{result['content'][:200]}...")
        return "\n".join(formatted)


# 智能体工厂
async def create_all_agents() -> List[BaseAgent]:
    """创建所有智能体，确保旁观者最后"""
    agents = [
        CapitalAgent(),
        TechnologyAgent(),
        CreativeAgent(),
        SocialAgent(),
        PolicyAgent(),
        UserAgent(),
        BystanderAgent()  # 旁观者始终最后
    ]
    return agents