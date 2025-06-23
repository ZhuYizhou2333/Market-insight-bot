import sys

from loguru import logger

# 移除默认的处理器，以便进行自定义配置
logger.remove()

# 定义日志格式，包含时间、级别、模块、函数、行号和消息，并添加颜色
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 添加一个新的控制台输出处理器
logger.add(
    sys.stdout,
    colorize=True,  # 启用颜色
    format=log_format,  # 应用自定义格式
    level="INFO",  # 设置日志级别
)
# 添加一个文件输出处理器，记录所有日志到文件
logger.add(
    "logs/app.log",  # 日志文件路径
    rotation="1 day",  # 每天轮换日志文件
    retention="7 days",  # 保留最近7天的日志文件
    encoding="utf-8",  # 设置文件编码为UTF-8
    format=log_format,  # 应用自定义格式
    level="DEBUG",  # 设置日志级别为DEBUG
)

# 导出配置好的logger实例
__all__ = ["logger"]
