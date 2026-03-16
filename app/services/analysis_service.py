import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import settings
from ..models.metrics import ImpactMetrics, SimulationRound, SimulationResult
from .agent_service import create_all_agents, AgentOpinion
from .llm_service import get_llm_service
from .search_service import get_search_service


logger = logging.getLogger(__name__)


class SimulationEngine:
    """重构后的推演引擎 - 支持异步操作和实时进度推送"""
    
    def __init__(self):
        self.settings = settings
        self.agents = []
        self.llm_service = None
        self.search_service = None
        self.progress_callbacks = []  # 用于实时进度推送
    
    async def initialize(self):
        """初始化引擎"""
        self.agents = await create_all_agents()
        self.llm_service = await get_llm_service()
        self.search_service = await get_search_service()
        logger.info(f"推演引擎初始化完成，加载了 {len(self.agents)} 个智能体")
    
    def register_progress_callback(self, callback):
        """注册进度回调函数（用于实时更新）"""
        # 清空之前的回调，避免重复
        self.progress_callbacks.clear()
        self.progress_callbacks.append(callback)
    
    async def run_simulation(self, event: Dict, progress_callback=None, max_rounds=1, start_round=1) -> SimulationResult:
        """运行推演模拟 - 从指定轮次开始执行"""
        if not self.agents:
            await self.initialize()
        
        if progress_callback:
            self.register_progress_callback(progress_callback)
        
        event_name = event.get("name", "未命名事件")
        event_description = event.get("description", "")
        event_id = event.get("id", f"event_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        logger.info(f"开始推演: {event_name}，最大轮数: {max_rounds}，起始轮次: {start_round}")
        
        rounds = []
        previous_metrics = None
        previous_summary = ""  # 存储前一轮的旁观者总结
        
        # 发送初始进度
        await self._notify_progress({
            "status": "started",
            "event_name": event_name,
            "current_round": start_round - 1,  # 显示上一轮
            "total_rounds": max_rounds,
            "message": f"开始分析 {event_name}"
        })
        
        # 从指定轮次开始执行
        for round_num in range(start_round, start_round + max_rounds):
            logger.info(f"执行第 {round_num} 轮推演")
            
            # 发送当前轮次开始通知
            await self._notify_progress({
                "status": "round_started",
                "current_round": round_num,
                "message": f"第 {round_num} 轮推演进行中..."
            })
            
            # 将前一轮的总结加入事件信息中
            round_event = event.copy()
            if previous_summary:
                round_event["previous_summary"] = previous_summary
            
            # 执行单轮推演
            round_result = await self._execute_round(round_event, round_num, previous_metrics)
            rounds.append(round_result)
            
            # 计算当前综合得分
            current_metrics = round_result.metrics_snapshot
            composite_score = self._calculate_composite_score(current_metrics)
            
            logger.info(f"第 {round_num} 轮完成，综合得分: {composite_score:.3f}")
            
            # 由旁观者对本轮推演进行总结
            bystander_summary = await self._generate_bystander_summary(round_result)
            
            # 发送进度更新
            await self._notify_progress({
                "status": "round_completed",
                "current_round": round_num,
                "composite_score": composite_score,
                "metrics": current_metrics,
                "agent_opinions": round_result.agent_opinions,
                "bystander_summary": bystander_summary,
                "message": f"第 {round_num} 轮完成，综合得分: {composite_score:.3f}"
            })
            
            # 检查终止条件
            if round_num >= self.settings.min_rounds:
                # 检查目标阈值（任何单项评分>0.8）
                max_single_score = max(current_metrics.values()) if current_metrics else 0
                if max_single_score >= self.settings.target_score_threshold:
                    logger.info(f"达到目标阈值（单项>0.8），在第 {round_num} 轮终止")
                    await self._notify_progress({
                        "status": "target_reached",
                        "final_round": round_num,
                        "composite_score": composite_score,
                        "message": f"达到目标阈值（单项>0.8），推演终止"
                    })
                    break
                
                # 检查收敛
                if previous_metrics and self._check_convergence(previous_metrics, current_metrics):
                    logger.info(f"检测到收敛，在第 {round_num} 轮终止")
                    await self._notify_progress({
                        "status": "converged",
                        "final_round": round_num,
                        "composite_score": composite_score,
                        "message": f"指标收敛，推演终止"
                    })
                    break
            
            previous_metrics = current_metrics.copy()
            previous_summary = bystander_summary  # 保存本轮总结供下轮使用
        
        # 生成最终结果
        final_result = await self._generate_final_result(
            event_id, event_name, event_description, rounds
        )
        
        logger.info(f"推演完成: {event_name}, 总轮数: {len(rounds)}, 综合得分: {final_result.composite_score:.3f}")
        
        # 发送完成通知
        await self._notify_progress({
            "status": "completed",
            "total_rounds": len(rounds),
            "composite_score": final_result.composite_score,
            "message": f"推演完成，总轮数: {len(rounds)}, 综合得分: {final_result.composite_score:.3f}"
        })
        
        return final_result
    
    async def _execute_round(self, event: Dict, round_num: int, previous_metrics: Optional[Dict]) -> SimulationRound:
        """执行单轮推演"""
        agent_opinions = []
        
        # 为所有智能体设置进度回调
        for agent in self.agents:
            agent.progress_callback = self._notify_progress
        
        # 分离旁观者和其他智能体
        bystander = None
        other_agents = []
        for agent in self.agents:
            if agent.name == '旁观者':
                bystander = agent
            else:
                other_agents.append(agent)
        
        # 先并发执行其他智能体的分析
        other_tasks = []
        for agent in other_agents:
            task = asyncio.create_task(
                self._execute_agent_analysis(agent, event, round_num, previous_metrics)
            )
            other_tasks.append(task)
        
        other_results = await asyncio.gather(*other_tasks, return_exceptions=True)
        
        for i, result in enumerate(other_results):
            if isinstance(result, Exception):
                logger.error(f"智能体 {other_agents[i].name} 分析失败: {str(result)}")
                opinion = AgentOpinion(
                    agent_name=other_agents[i].name,
                    perspective=other_agents[i].perspective,
                    scores={},
                    reasoning="分析过程中出现错误"
                )
            else:
                opinion = result
            agent_opinions.append(opinion.dict())
        
        # 将其他智能体的观点传递给旁观者
        if bystander:
            try:
                bystander_result = await self._execute_agent_analysis(
                    bystander, event, round_num, previous_metrics, 
                    other_opinions=agent_opinions
                )
                agent_opinions.append(bystander_result.dict())
            except Exception as e:
                logger.error(f"旁观者分析失败: {str(e)}")
                opinion = AgentOpinion(
                    agent_name='旁观者',
                    perspective='独立',
                    scores={},
                    reasoning="分析过程中出现错误"
                )
                agent_opinions.append(opinion.dict())
        
        # 识别共识和冲突
        consensus, conflicts = await self._identify_consensus_conflicts(agent_opinions)
        
        # 计算当前轮次指标
        agent_scores = {op["agent_name"]: op["scores"] for op in agent_opinions}
        metrics = await self._calculate_metrics_from_agent_scores(agent_scores)
        metrics_snapshot = metrics.to_dict()
        
        return SimulationRound(
            round_number=round_num,
            agent_opinions=agent_opinions,
            consensus_points=consensus,
            conflict_points=conflicts,
            metrics_snapshot=metrics_snapshot
        )
    
    async def _execute_agent_analysis(self, agent, event: Dict, round_num: int, previous_metrics: Optional[Dict], other_opinions: Optional[List[Dict]] = None):
        """执行单个智能体的分析"""
        # 为智能体设置进度回调
        agent.progress_callback = self._notify_progress
        # 发送分析开始状态
        await self._notify_progress({
            "status": "agent_analyzing",
            "agent_name": agent.name,
            "round_num": round_num
        })
        
        # 调用智能体的分析方法，传入其他智能体的观点
        result = await agent.analyze(event, round_num, previous_metrics, other_opinions)
        
        # 发送分析完成状态
        await self._notify_progress({
            "status": "agent_completed",
            "agent_name": agent.name,
            "round_num": round_num
        })
        
        return result
    
    async def _identify_consensus_conflicts(self, opinions: List[Dict]) -> tuple:
        """识别共识和冲突点"""
        consensus = []
        conflicts = []
        
        # 获取所有评分维度
        all_scores = {}
        for opinion in opinions:
            scores = opinion.get("scores", {})
            for dim, score in scores.items():
                if dim not in all_scores:
                    all_scores[dim] = []
                all_scores[dim].append(score)
        
        # 分析每个维度的分歧程度
        for dim, scores in all_scores.items():
            if not scores:
                continue
            
            avg_score = sum(scores) / len(scores)
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            
            if variance < 0.01:  # 差异很小，视为共识
                consensus.append(f"{dim}: 平均分{avg_score:.2f} (低分歧)")
            elif variance > 0.05:  # 差异较大，视为冲突
                conflicts.append(f"{dim}: 分歧较大 (方差{variance:.2f})")
        
        return consensus, conflicts
    
    async def _calculate_metrics_from_agent_scores(self, agent_scores: Dict[str, Dict]) -> ImpactMetrics:
        """根据智能体评分计算最终指标"""
        # 收集所有维度的评分
        dimension_scores = {
            "technology_penetration": [],
            "economic_disruption": [],
            "employment_volatility": [],
            "process_reconstruction": [],
            "ethical_risk": []
        }
        
        # 从各智能体的评分中提取对应维度的值
        for agent_name, scores in agent_scores.items():
            for dim in dimension_scores.keys():
                if dim in scores:
                    score = scores[dim]
                    if isinstance(score, (int, float)) and 0.0 <= score <= 1.0:
                        dimension_scores[dim].append(score)
        
        # 计算每个维度的平均分
        final_scores = {}
        for dim, scores in dimension_scores.items():
            if scores:
                final_scores[dim] = sum(scores) / len(scores)
            else:
                final_scores[dim] = 0.5  # 默认值
        
        return ImpactMetrics(**final_scores)
    
    def _check_convergence(self, previous: Dict, current: Dict) -> bool:
        """检查是否收敛"""
        max_change = 0
        for key in previous:
            if key in current:
                change = abs(previous[key] - current[key])
                max_change = max(max_change, change)
        
        return max_change < self.settings.convergence_threshold
    
    def _calculate_composite_score(self, metrics: Dict) -> float:
        """计算综合影响力得分"""
        weights = {
            "technology_penetration": 0.25,
            "economic_disruption": 0.25,
            "employment_volatility": 0.15,
            "process_reconstruction": 0.20,
            "ethical_risk": 0.15
        }
        
        score = 0.0
        for key, weight in weights.items():
            if key in metrics:
                score += metrics[key] * weight
        
        return score
    
    async def _generate_final_result(self, event_id: str, event_name: str, event_description: str,
                                   rounds: List[SimulationRound]) -> SimulationResult:
        """生成最终结果"""
        final_round = rounds[-1]
        
        # 汇总所有共识和冲突
        all_consensus = []
        all_conflicts = []
        for r in rounds:
            all_consensus.extend(r.consensus_points)
            all_conflicts.extend(r.conflict_points)
        
        # 生成建议
        recommendations = await self._generate_recommendations(
            final_round.metrics_snapshot, all_conflicts
        )
        
        # 计算最终综合得分
        composite_score = self._calculate_composite_score(final_round.metrics_snapshot)
        
        return SimulationResult(
            event_id=event_id,
            event_name=event_name,
            event_description=event_description,
            total_rounds=len(rounds),
            rounds=rounds,
            final_metrics=final_round.metrics_snapshot,
            composite_score=composite_score,
            consensus_summary="; ".join(all_consensus[:5]) if all_consensus else "无显著共识",
            conflict_summary="; ".join(all_conflicts[:5]) if all_conflicts else "无显著冲突",
            recommendations=recommendations
        )
    
    async def _generate_bystander_summary(self, round_result: SimulationRound) -> str:
        """生成旁观者对本轮推演的总结"""
        llm_service = await get_llm_service()
        
        # 收集所有智能体的意见（排除旁观者自己）
        opinions_text = ""
        for opinion in round_result.agent_opinions:
            if opinion['agent_name'] != '旁观者':
                opinions_text += f"【{opinion['agent_name']}】\n{opinion['reasoning']}\n\n"
        
        system_prompt = """你是一名拥有上帝视角的**首席行业分析师**。你不代表任何利益集团（非资本、非技术、非用户），你的唯一任务是**综合所有其他智能体的观点**，结合历史演变趋势，对事件进行**全局性、客观的复盘与总结**。

你是沙盘推演中的"定海神针"，负责在每一轮结束后，理清混乱的博弈，指出真正的共识与分歧，并给出最接近事实真相的综合分析。

**关键职责**：
1. **观点聚合**：阅读并理解其他所有角色（资本、技术、创意、社会、政策、用户）的发言。
2. **冲突识别**：明确指出哪些维度上大家意见一致（共识），哪些维度上存在巨大分歧（冲突），并分析原因。
3. **趋势研判**：判断事态是升级了、缓和了还是发生了转折。
4. **综合总结**：给出最接近事实真相的综合判断。

**输出要求**：
- 使用人类语言，避免过于技术化的表达
- 突出核心观点和关键洞察
- 语气客观公正，不带偏见
- 总结要完整充分，不要省略重要信息"""
        
        user_prompt = f"""请对以下多智能体推演结果进行客观分析和总结：

智能体观点：
{opinions_text}

共识点：
{'; '.join(round_result.consensus_points[:5]) if round_result.consensus_points else '暂无显著共识'}

冲突点：
{'; '.join(round_result.conflict_points[:5]) if round_result.conflict_points else '暂无显著冲突'}

当前指标快照：
{round_result.metrics_snapshot}

请提供一份完整、客观的旁观者总结，包含：
1. 本轮核心态势总结
2. 主要共识点（哪些角色看法一致及原因）
3. 关键冲突点（哪些角色存在分歧及原因）
4. 综合判断和趋势分析

总结要全面、客观、通俗易懂。"""
        
        try:
            response = await llm_service.completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # 发送旁观者总结到WebSocket
            await self._notify_progress({
                "status": "bystander_summary",
                "summary": response,
                "round_number": round_result.round_number
            })
            
            return response
        except Exception as e:
            logger.error(f"生成旁观者总结失败: {str(e)}")
            summary = f"第{round_result.round_number}轮推演完成，涉及{len(round_result.agent_opinions)}个智能体，共识点{len(round_result.consensus_points)}个，冲突点{len(round_result.conflict_points)}个"
            
            # 发送基本总结到WebSocket
            await self._notify_progress({
                "status": "bystander_summary",
                "summary": summary,
                "round_number": round_result.round_number
            })
            
            return summary
    
    async def _generate_recommendations(self, metrics: Dict, conflicts: List[str]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if metrics.get("technology_penetration", 0) > 0.7:
            recommendations.append("技术渗透迅速，建议加快技术储备和人才培养")
        
        if metrics.get("economic_disruption", 0) > 0.7:
            recommendations.append("经济影响显著，需评估商业模式调整需求")
        
        if metrics.get("employment_volatility", 0) > 0.6:
            recommendations.append("就业波动风险高，制定人员转型计划")
        
        if metrics.get("ethical_risk", 0) > 0.5:
            recommendations.append("存在伦理风险，建立合规审查机制")
        
        if conflicts:
            recommendations.append(f"内部存在{len(conflicts)}个分歧点，建议组织专项讨论")
        
        return recommendations if recommendations else ["持续观察，暂无需特殊行动"]
    
    async def _notify_progress(self, progress_data: Dict):
        """通知进度回调"""
        for callback in self.progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress_data)
                else:
                    callback(progress_data)
            except Exception as e:
                logger.error(f"进度回调执行失败: {str(e)}")