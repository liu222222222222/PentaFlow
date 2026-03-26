from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Callable
import asyncio
import json
import re
from datetime import datetime
import uuid
import sys
import os
import httpx
from openai import AsyncOpenAI
# 添加项目根路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.models.metrics import EventModel, SimulationResult
from app.services.analysis_service import SimulationEngine
from app.services.llm_service import get_llm_service
from config import settings
from app.services.websocket_service import send_progress_update_to_task
import logging

logger = logging.getLogger(__name__)


router = APIRouter()
simulation_engine = SimulationEngine()  # 这里使用一个新的实例用于分析服务

# 用于存储WebSocket连接的字典
websocket_connections: Dict[str, WebSocket] = {}


class AnalysisRequest(BaseModel):
    event: EventModel
    llm_api_key: Optional[str] = ""
    search_api_key: Optional[str] = ""


class AnalysisResponse(BaseModel):
    task_id: str
    message: str
    event_name: str


@router.post("/analysis", response_model=AnalysisResponse)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """启动推演分析"""
    from fastapi import HTTPException
    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建事件字典格式（与引擎兼容）
        event_dict = {
            "id": request.event.id,
            "name": request.event.name,
            "description": request.event.description,
            "category": request.event.category,
            "llm_api_key": request.llm_api_key,
            "search_api_key": request.search_api_key
        }
        
        logger.info(f"启动分析任务: {task_id}")
        
        # 启动后台分析任务
        background_tasks.add_task(
            run_analysis_task,
            task_id,
            event_dict
        )
        
        return AnalysisResponse(
            task_id=task_id,
            message="推演任务已启动",
            event_name=request.event.name
        )
        
    except Exception as e:
        logger.error(f"分析启动失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析启动失败: {str(e)}")


from fastapi import HTTPException

@router.post("/analysis/generate_summary")
async def generate_summary(request: dict):
    """生成精简版报告"""
    try:
        agent_opinions = request.get("agent_opinions", [])
        composite_score = request.get("composite_score", 0)
        llm_api_key = request.get("llm_api_key", "")
        
        # 如果提供了API key，临时设置到settings
        if llm_api_key:
            settings.llm_api_key = llm_api_key
        
        llm_service = await get_llm_service()
        
        # 构建各方观点文本
        opinions_text = ""
        for op in agent_opinions:
            if op.get("agent_name") == "旁观者":
                continue
            
            agent_name = op.get("agent_name", "未知")
            reasoning = op.get("reasoning", "")
            opinions_text += f"【{agent_name}】: {reasoning}\n\n"
        
        # 提取旁观者总结
        bystander_summary = ""
        bystander_opinion = next((op for op in agent_opinions if op.get("agent_name") == "旁观者"), None)
        if bystander_opinion and bystander_opinion.get("reasoning"):
            bystander_summary = bystander_opinion.get("reasoning")
        
        # 构建各方观点汇总的prompt
        opinions_prompt = f"""请对以下各方观点进行精简汇总，每个智能体不超过120字，用大白话总结：

{opinions_text}

要求：
1. 每个智能体（资本代言人、技术执行者、创意指挥官、社会观察员、政策监管者、用户代表）一句话总结主要观点
2. 每个观点不超过120字
3. 用大白话，通俗易懂
4. 直接列出观点，不要其他说明

输出格式：
【资本代言人】：观点内容
【技术执行者】：观点内容
【创意指挥官】：观点内容
【社会观察员】：观点内容
【政策监管者】：观点内容
【用户代表】：观点内容"""
        
        # 构建旁观者总结的prompt
        bystander_prompt = f"""请对以下旁观者总结进行精简处理，不超过500字，用大白话总结各方观点并给出综合判断：

{bystander_summary}

要求：
1. 提取核心观点，去掉专业术语
2. 用大白话，像人说话一样
3. 保留段落结构，不要全部挤在一起
4. 不超过500字
5. 要体现对各方观点的综合判断"""
        
        # 生成各方观点汇总
        opinions_response = await llm_service.completion(
            system_prompt="你是一个专业的文案整理助手，擅长将复杂的技术内容转化为通俗易懂的文字。",
            user_prompt=opinions_prompt
        )
        
        # 处理各方观点汇总，生成HTML
        opinions_lines = opinions_response.split('\n')
        opinions_html = ""
        for line in opinions_lines:
            line = line.strip()
            if line.startswith('【') and '】：' in line:
                parts = line.split('】：', 1)
                if len(parts) == 2:
                    agent_name = parts[0].replace('【', '').replace('】', '')
                    content = parts[1].strip()
                    opinions_html += f"""
                        <div class="opinion-item">
                            <strong>{agent_name}:</strong>
                            <div style="margin-top: 5px; color: #666;">{content}</div>
                        </div>
                    """
        
        # 生成旁观者总结
        bystander_response = await llm_service.completion(
            system_prompt="你是一个专业的文案整理助手，擅长将复杂的技术内容转化为通俗易懂的文字。",
            user_prompt=bystander_prompt
        )
        
        # 处理旁观者总结，保留段落结构
        bystander_html = re.sub(r'\n\n+', '</p><p style="margin: 8px 0;">', bystander_response)
        bystander_html = re.sub(r'\n', '<br>', bystander_html)
        bystander_html = bystander_html.strip()
        
        # 限制在500字以内
        if len(bystander_html) > 500:
            bystander_html = bystander_html[:500]
            last_period = max(
                bystander_html.rfind('。'),
                bystander_html.rfind('！'),
                bystander_html.rfind('？')
            )
            if last_period > 450:
                bystander_html = bystander_html[:last_period + 1]
            else:
                bystander_html += '...'
        
        bystander_html = f'<p style="margin: 8px 0;">{bystander_html}</p>'
        
        # 处理综合得分
        score = f"{composite_score:.3f}" if composite_score is not None else "计算中"
        
        return {
            "opinions_html": opinions_html,
            "bystander_summary": bystander_html,
            "score": score
        }
        
    except Exception as e:
        logger.error(f"生成精简报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成精简报告失败: {str(e)}")


@router.post("/analysis/control")
async def control_analysis(request: dict, background_tasks: BackgroundTasks):
    """控制推演过程（开始下一轮、生成报告等）"""
    try:
        task_id = request.get("task_id")
        action = request.get("action")  # "next_round", "generate_report", "terminate"
        round = request.get("round", 1)
        
        if action == "next_round":
            # 启动下一轮推演
            logger.info(f"请求启动下一轮推演，任务ID: {task_id}，当前轮次: {round}")
            
            # 获取之前的事件信息和前一轮结果
            from pathlib import Path
            import json
            
            data_dir = Path(settings.data_dir)
            event_data = None
            previous_round_result = None
            
            # 查找最新的结果文件来获取事件信息和前一轮结果
            result_files = sorted(data_dir.glob("result_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
            if result_files:
                with open(result_files[0], 'r', encoding='utf-8') as f:
                    result = json.load(f)
                    event_data = {
                        "id": result.get("event_id"),
                        "name": result.get("event_name"),
                        "description": result.get("event_description"),
                        "category": result.get("event_category", "其他")
                    }
                    
                    # 获取前一轮的结果
                    if result.get("rounds") and len(result["rounds"]) > 0:
                        previous_round_result = result["rounds"][-1]
            
            if not event_data:
                raise HTTPException(status_code=404, detail="未找到之前的事件信息")
            
            # 添加前一轮的总结到事件数据中
            if previous_round_result:
                # 提取旁观者总结
                bystander_summary = ""
                if previous_round_result.get("agent_opinions"):
                    bystander_opinion = next(
                        (op for op in previous_round_result["agent_opinions"] if op.get("agent_name") == "旁观者"),
                        None
                    )
                    if bystander_opinion and bystander_opinion.get("reasoning"):
                        bystander_summary = bystander_opinion["reasoning"]
                
                if bystander_summary:
                    event_data["previous_summary"] = bystander_summary
            
            # 启动下一轮推演任务，传递当前轮次信息
            background_tasks.add_task(
                run_analysis_task,
                task_id,
                event_data,
                max_rounds=1,
                start_round=round + 1  # 从下一轮开始
            )
            
            await send_progress_update(task_id, {
                "status": "next_round_started",
                "task_id": task_id,
                "current_round": round + 1,
                "message": f"开始第 {round + 1} 轮推演"
            })
            
            return {"message": "下一轮推演已开始", "status": "next_round_started"}
            
        elif action == "generate_report":
            # 生成最终报告
            await send_progress_update(task_id, {
                "status": "report_generation_requested",
                "task_id": task_id,
                "message": "报告生成请求已接收"
            })
            return {"message": "报告生成中", "status": "report_generation_started"}
            
        elif action == "terminate":
            # 中止推演
            await send_progress_update(task_id, {
                "status": "terminated",
                "task_id": task_id,
                "message": "推演已中止"
            })
            return {"message": "推演已中止", "status": "terminated"}
            
        else:
            return {"message": f"未知操作: {action}", "status": "unknown_action"}
            
    except Exception as e:
        logger.error(f"控制操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"控制操作失败: {str(e)}")


@router.post("/analysis/generate_timeline")
async def generate_timeline(request: dict):
    """生成多轮推演的时间线总结"""
    try:
        rounds_data = request.get("rounds", [])
        event_name = request.get("event_name", "")
        llm_api_key = request.get("llm_api_key", "")
        
        if len(rounds_data) < 2:
            raise HTTPException(status_code=400, detail="需要至少2轮推演数据才能生成时间线")
        
        # 如果提供了API key，临时设置到settings
        if llm_api_key:
            settings.llm_api_key = llm_api_key
        
        llm_service = await get_llm_service()
        
        # 构建时间线生成prompt
        timeline_prompt = f"""请基于以下多轮推演数据，为事件【{event_name}】生成一个时间线总结，展示每个智能体和旁观者在每一轮的核心思想转变。

推演数据：
{json.dumps(rounds_data, ensure_ascii=False, indent=2)}

请按照以下格式输出JSON：
{{
  "timeline": [
    {{
      "round": 1,
      "title": "第1轮：初始评估",
      "agents": [
        {{
          "name": "资本代言人",
          "core_view": "核心观点",
          "change": "与上一轮对比（第1轮无此项）"
        }}
      ],
      "bystander": {{
        "summary": "旁观者总结",
        "key_insights": ["关键洞察1", "关键洞察2"]
      }}
    }}
  ],
  "overall_trend": "整体趋势分析"
}}

要求：
1. 每个智能体的核心观点不超过100字，简洁明了
2. 突出每轮思想转变的关键点
3. 旁观者的总结要简明扼要，指出本轮的关键发现
4. 整体趋势分析要500字左右，概括所有轮次的演变脉络和核心发现
5. 只返回JSON，不要其他文字"""
        
        response = await llm_service.completion(
            system_prompt="你是一个专业的分析师，擅长梳理多轮推演中的思想演变轨迹，生成清晰的时间线总结。",
            user_prompt=timeline_prompt
        )
        
        logger.debug(f"LLM返回的时间线响应长度: {len(response)} 字符")
        logger.debug(f"LLM返回的时间线响应前500字符:\n{response[:500]}")
        logger.debug(f"LLM返回的时间线响应后500字符:\n{response[-500:]}")
        
        # 解析JSON响应
        try:
            import re
            # 首先尝试从markdown代码块中提取JSON
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                response = json_match.group(1).strip()
                logger.debug(f"从markdown代码块中提取JSON成功，JSON长度: {len(response)} 字符")
            else:
                # 如果没有markdown代码块，尝试直接查找JSON
                # 查找从第一个{到最后一个}的完整JSON
                first_brace = response.find('{')
                last_brace = response.rfind('}')
                if first_brace >= 0 and last_brace > first_brace:
                    response = response[first_brace:last_brace + 1]
                    logger.debug(f"从第一个{{到最后一个}}提取JSON成功，JSON长度: {len(response)} 字符")
                else:
                    logger.warning(f"无法找到JSON格式的内容")
                    raise ValueError("无法找到有效的JSON结构")
            
            # 尝试解析JSON
            try:
                timeline_data = json.loads(response)
                logger.info(f"JSON解析成功，包含 {len(timeline_data.get('timeline', []))} 轮数据")
            except json.JSONDecodeError as e:
                # 尝试修复常见的JSON格式问题
                logger.warning(f"初次JSON解析失败，尝试修复: {e}")
                
                # 修复1: 移除尾部逗号
                response = re.sub(r',(\s*[}\]])', r'\1', response)
                
                # 修复2: 修复未闭合的字符串
                # 如果最后一个字符是反斜杠，可能是未闭合的转义
                if response.rstrip().endswith('\\'):
                    response = response.rstrip()[:-1]
                
                # 修复3: 确保JSON以}结尾
                response = response.rstrip()
                if not response.endswith('}'):
                    # 计算括号平衡
                    open_braces = response.count('{')
                    close_braces = response.count('}')
                    if open_braces > close_braces:
                        response += '}' * (open_braces - close_braces)
                
                # 再次尝试解析
                try:
                    timeline_data = json.loads(response)
                    logger.info(f"JSON修复后解析成功")
                except json.JSONDecodeError as e2:
                    logger.error(f"JSON修复后仍解析失败: {e2}")
                    raise e2
                    
        except json.JSONDecodeError as e:
            # 如果解析失败，返回原始响应作为文本总结
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"解析位置: {e.pos if hasattr(e, 'pos') else '未知'}")
            logger.error(f"错误信息: {e.msg}")
            
            # 尝试从响应中提取有用的文本内容作为总结
            # 移除markdown代码块标记
            clean_response = re.sub(r'```json\s*|\s*```', '', response)
            # 尝试提取overall_trend部分
            trend_match = re.search(r'"overall_trend"\s*:\s*"([^"]+)"', clean_response, re.DOTALL)
            overall_trend = trend_match.group(1) if trend_match else clean_response[:2000]
            
            timeline_data = {
                "timeline": [],
                "overall_trend": overall_trend,
                "error": f"JSON解析失败，显示原始内容。错误: {str(e)}"
            }
        
        return timeline_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成时间线失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成时间线失败: {str(e)}")


async def run_analysis_task(task_id: str, event: Dict, max_rounds=1, start_round=1):
    """后台执行分析任务"""
    logger.info(f"开始执行任务 {task_id} 的分析，最大轮数: {max_rounds}，起始轮次: {start_round}")
    try:
        # 强制设置API key到settings（只在用户提供了新的 key 时才更新）
        if event.get("llm_api_key"):
            settings.llm_api_key = event["llm_api_key"]
            logger.info(f"使用用户提供的LLM API Key")
        else:
            logger.info(f"使用默认LLM API Key（用户未提供）")
        
        if event.get("search_api_key"):
            settings.tavily_api_key = event["search_api_key"]
            logger.info(f"使用用户提供的搜索API Key")
        else:
            logger.info(f"使用默认搜索API Key（用户未提供）")
        
        # 初始化引擎
        await simulation_engine.initialize()
        
        # 注册进度回调（用于WebSocket通知）
        progress_callback = create_progress_callback(task_id)
        simulation_engine.register_progress_callback(progress_callback)
        logger.info(f"进度回调已注册到引擎，任务ID: {task_id}")
        
        # 执行推演（只执行指定轮数，从指定轮次开始）
        result = await simulation_engine.run_simulation(event, progress_callback, max_rounds=max_rounds, start_round=start_round)
        
        # 保存结果（这里可以保存到文件或数据库）
        save_analysis_result(result)
        
        # 发送完成消息
        await send_progress_update(task_id, {
            "status": "completed",
            "task_id": task_id,
            "result": result.dict(),
            "message": "推演分析完成"
        })
        logger.info(f"任务 {task_id} 分析完成，结果已发送")
        
    except Exception as e:
        logger.error(f"任务 {task_id} 执行失败: {e}")
        await send_progress_update(task_id, {
            "status": "error",
            "task_id": task_id,
            "error": str(e),
            "message": f"推演分析失败: {str(e)}"
        })
        raise


def create_progress_callback(task_id: str) -> Callable:
    """创建进度回调函数"""
    async def callback(progress_data: Dict):
        # 添加任务ID到进度数据
        full_data = {
            "task_id": task_id,
            "progress_data": progress_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # 发送数据到WebSocket连接
        await send_progress_update(task_id, full_data)
    
    # 添加任务ID属性以便调试
    callback.task_id = task_id
    return callback


def create_progress_callback(task_id: str) -> Callable:
    """创建进度回调函数"""
    async def callback(progress_data: Dict):
        await send_progress_update(task_id, {
            "status": progress_data.get("status", "update"),
            "task_id": task_id,
            "progress_data": progress_data,
            "timestamp": datetime.now().isoformat()
        })
    return callback


async def send_progress_update(task_id: str, update_data: Dict):
    """发送进度更新到WebSocket连接"""
    # 使用新的WebSocket服务
    success = await send_progress_update_to_task(task_id, update_data)
    
    if not success:
        logger.warning(f"通过WebSocket服务发送失败，任务 {task_id}，尝试使用全局管理器")
        # 如果特定连接失败，尝试使用全局管理器
        try:
            from app.main import manager
            await manager.broadcast(json.dumps(update_data, ensure_ascii=False))
            logger.info(f"已通过全局管理器发送消息到任务 {task_id}")
        except Exception as e:
            logger.error(f"全局管理器发送也失败: {e}")
            # 如果全局连接也不行，仅记录日志
            logger.info(f"本地记录进度更新: {update_data}")


def save_analysis_result(result: SimulationResult):
    """保存分析结果"""
    import json
    from pathlib import Path
    
    # 确保数据目录存在
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(exist_ok=True)
    
    # 生成文件名 - 修复 f-string 中的反斜杠问题
    event_name_safe = result.event_name.replace('/', '_').replace('\\', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"result_{event_name_safe}_{timestamp}.json"
    
    filepath = data_dir / filename
    
    # 保存结果
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result.dict(), f, ensure_ascii=False, indent=2)
    
    logger.info(f"分析结果已保存到: {filepath}")


@router.get("/analysis/{task_id}")
async def get_analysis_status(task_id: str):
    """获取分析状态"""
    # 这里可以查询任务状态（需要实现任务状态存储）
    return {
        "task_id": task_id,
        "status": "running",  # 实际应用中应查询真实状态
        "message": "任务正在运行中",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/analysis/results")
async def get_analysis_results():
    """获取历史分析结果"""
    import json
    from pathlib import Path
    
    data_dir = Path(settings.data_dir)
    if not data_dir.exists():
        return {"results": []}
    
    results = []
    for file_path in data_dir.glob("result_*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
                results.append(result_data)
        except Exception as e:
            logger.error(f"加载结果文件失败 {file_path}: {e}")
    
    return {"results": results}
