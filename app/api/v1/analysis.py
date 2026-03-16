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
        
        print(f"🚀 启动分析任务: {task_id}")
        
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
        print(f"❌ 分析启动失败: {e}")
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
        print(f"❌ 生成精简报告失败: {e}")
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
            print(f"🔄 请求启动下一轮推演，任务ID: {task_id}，当前轮次: {round}")
            
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
        print(f"❌ 控制操作失败: {e}")
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
        
        print(f"📝 LLM返回的时间线响应长度: {len(response)} 字符")
        print(f"📝 LLM返回的时间线响应前500字符:\n{response[:500]}")
        print(f"📝 LLM返回的时间线响应后500字符:\n{response[-500:]}")
        
        # 解析JSON响应
        try:
            import re
            # 首先尝试从markdown代码块中提取JSON
            json_match = re.search(r'```json\s*(\{[\s\S]*\})\s*```', response)
            if json_match:
                response = json_match.group(1)
                print(f"✅ 从markdown代码块中提取JSON成功，JSON长度: {len(response)} 字符")
            else:
                # 如果没有markdown代码块，尝试直接查找JSON
                # 优化：查找从第一个{到最后一个}的完整JSON
                first_brace = response.find('{')
                last_brace = response.rfind('}')
                if first_brace >= 0 and last_brace > first_brace:
                    response = response[first_brace:last_brace + 1]
                    print(f"✅ 从第一个{{到最后一个}}提取JSON成功，JSON长度: {len(response)} 字符")
                else:
                    print(f"⚠️ 无法找到JSON格式的内容")
                    raise ValueError("无法找到有效的JSON结构")
            
            # 检查JSON是否完整
            if not response.strip().endswith('}'):
                print(f"⚠️ JSON字符串可能不完整，最后100字符: {response[-100:]}")
                # 尝试修复不完整的JSON
                brace_count = response.count('{') - response.count('}')
                if brace_count > 0:
                    print(f"⚠️ 检测到缺少 {brace_count} 个右括号")
                    response = response + '}' * brace_count
                    print(f"✅ 尝试修复JSON，添加了 {brace_count} 个右括号")
            
            # 检查是否缺少引号或逗号
            # 简单的修复：确保所有对象都正确闭合
            response = response.strip()
            if not response.endswith('}'):
                response = response + '}'
                print(f"✅ 在末尾添加了右括号")
            
            timeline_data = json.loads(response)
            print(f"✅ JSON解析成功，包含 {len(timeline_data.get('timeline', []))} 轮数据")
        except json.JSONDecodeError as e:
            # 如果解析失败，返回原始响应
            print(f"❌ JSON解析失败: {e}")
            print(f"❌ 解析位置: {e.pos if hasattr(e, 'pos') else '未知'}")
            print(f"❌ 错误信息: {e.msg}")
            print(f"❌ 尝试解析的内容长度: {len(response)}")
            print(f"❌ 尝试解析的内容前1000字符:\n{response[:1000]}")
            print(f"❌ 尝试解析的内容后1000字符:\n{response[-1000:]}")
            
            # 尝试提取可用的部分数据
            try:
                # 尝试找到最后一个完整的轮次
                last_round_match = re.search(r'(\{[^{}]*"round"\s*:\s*\d+[^{}]*\}(?=[^{}]*\}\s*\]\s*,?\s*"overall_trend")', response)
                if last_round_match:
                    print(f"✅ 找到最后一个完整的轮次数据")
                    # 返回部分成功的数据
                    partial_json = response[:last_round_match.end() + 1]
                    partial_json = partial_json.rstrip(',') + '}'
                    timeline_data = json.loads(partial_json)
                    timeline_data['error'] = f"部分数据解析成功，但可能不完整。原始错误: {str(e)}"
                    print(f"✅ 部分数据解析成功")
                else:
                    raise e
            except:
                # 如果连部分数据都无法解析，返回原始响应
                timeline_data = {
                    "timeline": [],
                    "overall_trend": f"数据解析失败，无法生成时间线总结。\n\n错误信息: {str(e)}\n\n解析位置: {e.pos if hasattr(e, 'pos') else '未知'}\n\n原始响应（前2000字符）:\n{response[:2000]}",
                    "error": f"JSON解析失败: {str(e)}"
                }
        
        return timeline_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 生成时间线失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成时间线失败: {str(e)}")


async def run_analysis_task(task_id: str, event: Dict, max_rounds=1, start_round=1):
    """后台执行分析任务"""
    print(f"⚙️ 开始执行任务 {task_id} 的分析，最大轮数: {max_rounds}，起始轮次: {start_round}")
    try:
        # 强制设置API key到settings（只在用户提供了新的 key 时才更新）
        if event.get("llm_api_key"):
            settings.llm_api_key = event["llm_api_key"]
            print(f"✅ 使用用户提供的LLM API Key")
        else:
            print(f"✅ 使用默认LLM API Key（用户未提供）")
        
        if event.get("search_api_key"):
            settings.tavily_api_key = event["search_api_key"]
            print(f"✅ 使用用户提供的搜索API Key")
        else:
            print(f"✅ 使用默认搜索API Key（用户未提供）")
        
        # 初始化引擎
        await simulation_engine.initialize()
        
        # 注册进度回调（用于WebSocket通知）
        progress_callback = create_progress_callback(task_id)
        simulation_engine.register_progress_callback(progress_callback)
        print(f"✅ 进度回调已注册到引擎，任务ID: {task_id}")
        
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
        print(f"✅ 任务 {task_id} 分析完成，结果已发送")
        
    except Exception as e:
        print(f"❌ 任务 {task_id} 执行失败: {e}")
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


async def send_progress_update(task_id: str, update_data: Dict):
    """发送进度更新到WebSocket连接"""
    # 从全局WebSocket管理器获取连接
    try:
        # 先尝试发送到特定任务的WebSocket连接
        from app.main import task_websockets
        if task_id in task_websockets:
            ws = task_websockets[task_id]
            try:
                await ws.send_text(json.dumps(update_data, ensure_ascii=False))
                print(f"✅ 成功发送消息到任务 {task_id}: {update_data.get('status', 'unknown status')}")
                return  # 成功发送，返回
            except Exception as e:
                print(f"❌ 发送WebSocket消息到特定连接失败 {task_id}: {e}")
                # 移除无效连接
                if task_id in task_websockets:
                    del task_websockets[task_id]
        
        # 如果特定连接失败或不存在，尝试使用全局管理器
        print(f"⚠️ 未找到任务 {task_id} 的WebSocket连接，尝试使用全局管理器")
        from app.main import manager
        await manager.broadcast(json.dumps(update_data, ensure_ascii=False))
        print(f"✅ 已通过全局管理器发送消息到任务 {task_id}")
    except Exception as e:
        print(f"❌ 获取WebSocket连接失败: {e}")
        # 如果全局连接不可用，仅记录日志
        print(f"📝 本地记录进度更新: {update_data}")


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
        print(f"⚠️ 通过WebSocket服务发送失败，任务 {task_id}，尝试使用全局管理器")
        # 如果特定连接失败，尝试使用全局管理器
        try:
            from app.main import manager
            await manager.broadcast(json.dumps(update_data, ensure_ascii=False))
            print(f"✅ 已通过全局管理器发送消息到任务 {task_id}")
        except Exception as e:
            print(f"❌ 全局管理器发送也失败: {e}")
            # 如果全局连接也不行，仅记录日志
            print(f"📝 本地记录进度更新: {update_data}")


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
    
    print(f"分析结果已保存到: {filepath}")


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
            print(f"加载结果文件失败 {file_path}: {e}")
    
    return {"results": results}
