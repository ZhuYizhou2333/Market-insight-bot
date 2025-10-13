"""
AI Analyzer for News Data
使用阿里云 DashScope (Qwen) 分析新闻消息
"""
import json
import os
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

from dashscope import Generation
from dashscope.api_entities.dashscope_response import GenerationResponse

from utils.logger import logger
from utils.email_sender import send_markdown_email


class NewsAnalyzer:
    """
    分析 Telegram 新闻消息，提供摘要和市场波动率判断
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen-plus-latest",
        message_buffer_size: int = 1000,
        analysis_interval: int = 1000,
    ):
        """
        初始化新闻分析器

        Args:
            api_key: 阿里云 DashScope API Key，默认从环境变量读取
            model: 使用的模型名称
            message_buffer_size: 消息缓冲区大小
            analysis_interval: 分析间隔（消息数量）
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "DASHSCOPE_API_KEY not found in environment variables or parameters"
            )

        self.model = model
        self.message_buffer_size = message_buffer_size
        self.analysis_interval = analysis_interval

        # 消息缓冲区
        self.message_buffer = deque(maxlen=message_buffer_size)
        self.message_count = 0
        self.last_analysis_count = 0

        logger.info(f"NewsAnalyzer initialized with model: {model}")

    def add_message(self, message_data: Dict) -> None:
        """
        添加新消息到缓冲区

        Args:
            message_data: 消息数据字典，包含 channel, text, date 等字段
        """
        self.message_buffer.append(message_data)
        self.message_count += 1

        # 检查是否需要进行分析
        if self.message_count - self.last_analysis_count >= self.analysis_interval:
            self.analyze_messages()
            self.last_analysis_count = self.message_count

    def _call_qwen_api(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """
        调用千问 API

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词

        Returns:
            API 返回的文本内容
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response: GenerationResponse = Generation.call(
                api_key=self.api_key,
                model=self.model,
                messages=messages,
                result_format="message",
            )

            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                logger.error(
                    f"Qwen API call failed: {response.code} - {response.message}"
                )
                return None

        except Exception as e:
            logger.error(f"Error calling Qwen API: {e}")
            return None

    def summarize_recent_messages(self, num_messages: int = 100) -> Optional[str]:
        """
        对最近 N 条消息进行摘要

        Args:
            num_messages: 要摘要的消息数量

        Returns:
            摘要文本
        """
        if len(self.message_buffer) == 0:
            logger.warning("No messages in buffer to summarize")
            return None

        # 获取最近的 N 条消息
        recent_messages = list(self.message_buffer)[-num_messages:]

        # 构建消息文本
        message_texts = []
        for msg in recent_messages:
            channel = msg.get("channel", "Unknown")
            text = msg.get("text", "")
            date = msg.get("date", "")
            if text:
                message_texts.append(f"[{channel} - {date}]: {text}")

        combined_text = "\n\n".join(message_texts)

        system_prompt = """你是一个加密货币市场分析专家。你的任务是分析 Telegram 频道的消息，提供简洁准确的摘要。
摘要应包含：
1. 主要讨论的币种和项目
2. 重要的市场事件或新闻
3. 社区关注的热点话题
4. 重要的价格走势或技术分析观点

请用中文回答，保持专业和客观。"""

        user_prompt = f"""请对以下 {len(recent_messages)} 条加密货币相关的 Telegram 消息进行摘要分析：

{combined_text}

请提供一个简洁的摘要（200-300字）。"""

        summary = self._call_qwen_api(user_prompt, system_prompt)
        return summary

    def analyze_market_volatility(
        self, num_messages: int = 500
    ) -> Optional[Dict[str, any]]:
        """
        判断市场波动率和社群活跃度

        Args:
            num_messages: 分析的消息数量

        Returns:
            包含分析结果的字典，格式：
            {
                "volatility_increased": bool,
                "activity_increased": bool,
                "summary": str,
                "hot_topics": List[str],
                "confidence": float
            }
        """
        if len(self.message_buffer) == 0:
            logger.warning("No messages in buffer to analyze")
            return None

        # 获取最近的 N 条消息
        recent_messages = list(self.message_buffer)[-num_messages:]

        # 构建消息文本
        message_texts = []
        for msg in recent_messages:
            channel = msg.get("channel", "Unknown")
            text = msg.get("text", "")
            date = msg.get("date", "")
            if text:
                message_texts.append(f"[{channel} - {date}]: {text}")

        combined_text = "\n\n".join(message_texts)

        system_prompt = """你是一个加密货币市场情绪分析专家。你需要分析 Telegram 消息，判断市场波动率和社群活跃度。

你需要判断：
1. 市场波动率是否上升（基于价格讨论频率、紧急词汇、情绪强度）
2. 社群活跃度是否上升（基于消息频率、讨论热度、互动性）
3. 当前的热点话题

请严格按照以下 JSON 格式返回，不要有其他文字：
{
    "volatility_increased": true/false,
    "activity_increased": true/false,
    "summary": "简短说明原因和市场状况",
    "hot_topics": ["话题1", "话题2", "话题3"],
    "confidence": 0.0-1.0
}"""

        user_prompt = f"""请分析以下 {len(recent_messages)} 条加密货币 Telegram 消息，判断市场波动率和社群活跃度是否上升：

{combined_text}

请严格按照 JSON 格式返回分析结果。"""

        response = self._call_qwen_api(user_prompt, system_prompt)

        if not response:
            return None

        try:
            # 尝试提取 JSON（处理可能的 markdown 代码块）
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            result = json.loads(response.strip())
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {response}")
            return None

    def analyze_messages(self) -> None:
        """
        执行定期分析：每 N 条消息进行一次摘要和波动率判断
        """
        logger.info(
            f"Starting analysis at message count: {self.message_count} "
            f"(buffer size: {len(self.message_buffer)})"
        )

        # 1. 生成消息摘要
        summary = self.summarize_recent_messages(num_messages=100)
        if summary:
            logger.success(f"Message Summary:\n{summary}")
        else:
            logger.warning("Failed to generate summary")

        # 2. 分析市场波动率
        volatility_result = self.analyze_market_volatility(num_messages=500)

        if volatility_result:
            logger.info(f"Volatility Analysis Result: {json.dumps(volatility_result, ensure_ascii=False, indent=2)}")

            # 3. 如果波动率或活跃度上升，发送邮件
            if volatility_result.get("volatility_increased") or volatility_result.get(
                "activity_increased"
            ):
                self._send_alert_email(volatility_result, summary)
            else:
                logger.info("No significant market volatility or activity increase detected")
        else:
            logger.warning("Failed to analyze market volatility")

    def _send_alert_email(
        self, volatility_result: Dict, summary: Optional[str]
    ) -> None:
        """
        发送市场波动警报邮件

        Args:
            volatility_result: 波动率分析结果
            summary: 消息摘要
        """
        # 构建邮件内容
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        volatility_status = (
            "📈 **上升**" if volatility_result.get("volatility_increased") else "📊 正常"
        )
        activity_status = (
            "🔥 **上升**" if volatility_result.get("activity_increased") else "💤 正常"
        )

        hot_topics = volatility_result.get("hot_topics", [])
        hot_topics_md = (
            "\n".join([f"- {topic}" for topic in hot_topics])
            if hot_topics
            else "暂无明显热点"
        )

        confidence = volatility_result.get("confidence", 0.0)
        confidence_bar = "🟢" * int(confidence * 10) + "⚪" * (10 - int(confidence * 10))

        email_content = f"""# 🚨 市场波动率警报

**分析时间**: {timestamp}
**分析消息数**: {len(self.message_buffer)} 条
**累计消息数**: {self.message_count} 条

---

## 📊 分析结果

### 市场波动率
{volatility_status}

### 社群活跃度
{activity_status}

### 置信度
{confidence_bar} {confidence:.1%}

---

## 🔥 当前热点话题

{hot_topics_md}

---

## 📝 市场状况说明

{volatility_result.get('summary', '暂无详细说明')}

---

## 📰 最近消息摘要

{summary or '暂无摘要'}

---

*本邮件由 Market Insight Bot 自动生成*
*AI 模型: {self.model}*
"""

        subject = f"[Market Alert] 市场波动率上升 - {timestamp}"

        try:
            success = send_markdown_email(subject, email_content)
            if success:
                logger.success(f"Alert email sent successfully: {subject}")
            else:
                logger.error("Failed to send alert email")
        except Exception as e:
            logger.error(f"Error sending alert email: {e}")

    def get_stats(self) -> Dict[str, int]:
        """
        获取统计信息

        Returns:
            包含统计信息的字典
        """
        return {
            "total_messages": self.message_count,
            "buffer_size": len(self.message_buffer),
            "last_analysis_count": self.last_analysis_count,
            "next_analysis_at": self.last_analysis_count + self.analysis_interval,
        }


# 全局分析器实例（可选）
_analyzer_instance = None


def get_analyzer(**kwargs) -> NewsAnalyzer:
    """
    获取全局分析器实例（单例模式）

    Args:
        **kwargs: NewsAnalyzer 初始化参数

    Returns:
        NewsAnalyzer 实例
    """
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = NewsAnalyzer(**kwargs)
    return _analyzer_instance


if __name__ == "__main__":
    # 测试代码
    import time

    analyzer = NewsAnalyzer()

    # 模拟添加消息
    test_messages = [
        {
            "channel": "CryptoNews",
            "text": "BTC突破45000美元，市场情绪高涨！",
            "date": datetime.now().isoformat(),
            "message_id": 1,
        },
        {
            "channel": "TechFlow",
            "text": "以太坊即将完成上海升级，质押提款功能开启",
            "date": datetime.now().isoformat(),
            "message_id": 2,
        },
        {
            "channel": "BlockBeats",
            "text": "Binance宣布支持新的质押产品",
            "date": datetime.now().isoformat(),
            "message_id": 3,
        },
    ]

    for msg in test_messages:
        analyzer.add_message(msg)

    # 测试摘要功能
    print("\n=== 测试摘要功能 ===")
    summary = analyzer.summarize_recent_messages(num_messages=3)
    print(f"Summary: {summary}")

    # 测试波动率分析
    print("\n=== 测试波动率分析 ===")
    volatility = analyzer.analyze_market_volatility(num_messages=3)
    print(f"Volatility: {json.dumps(volatility, ensure_ascii=False, indent=2)}")

    # 打印统计信息
    print("\n=== 统计信息 ===")
    stats = analyzer.get_stats()
    print(json.dumps(stats, indent=2))
