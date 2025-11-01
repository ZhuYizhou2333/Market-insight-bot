import os
import re
import smtplib
import ssl
import urllib.parse
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import markdown
import requests

# 从环境变量或.env文件读取邮件配置
def load_email_config():
    # 尝试从.env文件加载配置（如果存在）
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip()
    
    return {
        "sender": os.getenv("EMAIL_SENDER", "your_email@qq.com"),
        "password": os.getenv("EMAIL_PASSWORD", "your_smtp_password"), 
        "receiver": "2135378845@qq.com,2373034690@qq.com,huxian518@gmail.com,zzjianhust@gmail.com",
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.qq.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "use_tls": os.getenv("USE_TLS", "True").lower() == "true",
    }

EMAIL_CONFIG = load_email_config()


class MarkdownEmailSender:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or EMAIL_CONFIG
        self.md = markdown.Markdown(
            extensions=[
                "tables",
                "fenced_code",
                "codehilite",
                "toc",
                "nl2br",
                "sane_lists",
            ]
        )

    def _extract_images_from_markdown(self, markdown_text: str) -> List[Dict[str, str]]:
        """提取Markdown中的图片信息"""
        image_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
        images = []

        for match in re.finditer(image_pattern, markdown_text):
            alt_text = match.group(1)
            image_path = match.group(2)
            images.append(
                {
                    "alt_text": alt_text,
                    "path": image_path,
                    "cid": f"image_{len(images)}",
                }
            )

        return images

    def _process_image(self, image_info: Dict[str, str]) -> Optional[MIMEImage]:
        """处理单个图片，支持本地文件和URL"""
        try:
            path = image_info["path"]

            if path.startswith(("http://", "https://")):
                # 处理网络图片
                response = requests.get(path)
                response.raise_for_status()
                image_data = response.content
                content_type = response.headers.get("content-type", "image/jpeg")
            else:
                # 处理本地图片
                if not os.path.exists(path):
                    print(f"警告: 图片文件不存在: {path}")
                    return None

                with open(path, "rb") as f:
                    image_data = f.read()

                # 根据文件扩展名确定content type
                ext = os.path.splitext(path)[1].lower()
                content_type = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".gif": "image/gif",
                    ".bmp": "image/bmp",
                    ".webp": "image/webp",
                }.get(ext, "image/jpeg")

            image = MIMEImage(image_data)
            image.add_header("Content-ID", f"<{image_info['cid']}>")
            image.add_header("Content-Type", content_type)
            return image

        except Exception as e:
            print(f"处理图片失败 {image_info['path']}: {e}")
            return None

    def _convert_markdown_to_html(
        self, markdown_text: str
    ) -> tuple[str, List[Dict[str, str]]]:
        """将Markdown转换为HTML，并处理图片"""
        # 提取图片信息
        images = self._extract_images_from_markdown(markdown_text)

        # 在Markdown文本中，用CID替换图片路径
        processed_markdown = markdown_text
        for image_info in images:
            processed_markdown = processed_markdown.replace(
                image_info["path"], f"cid:{image_info['cid']}"
            )

        # 转换Markdown为HTML
        html_content = self.md.convert(processed_markdown)

        # 添加HTML邮件样式
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                    margin-top: 24px;
                    margin-bottom: 16px;
                }}
                code {{
                    background-color: #f4f4f4;
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                }}
                pre {{
                    background-color: #f4f4f4;
                    padding: 16px;
                    border-radius: 5px;
                    overflow-x: auto;
                    font-family: 'Courier New', monospace;
                }}
                blockquote {{
                    border-left: 4px solid #ddd;
                    margin: 0;
                    padding-left: 16px;
                    color: #666;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 16px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                ul, ol {{
                    padding-left: 20px;
                }}
                li {{
                    margin: 4px 0;
                }}
                a {{
                    color: #3498db;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        return styled_html, images

    def send_email(
        self,
        subject: str,
        markdown_content: str,
        receivers: str = None,
        cc: str = None,
        bcc: str = None,
    ) -> bool:
        """发送邮件

        Args:
            subject: 邮件主题
            markdown_content: Markdown格式的内容
            receivers: 收件人（逗号分隔），默认使用配置中的收件人
            cc: 抄送（逗号分隔）
            bcc: 密送（逗号分隔）

        Returns:
            bool: 发送是否成功
        """
        server = None
        try:
            # 转换Markdown为HTML
            html_content, image_infos = self._convert_markdown_to_html(markdown_content)

            # 创建邮件对象
            if image_infos:
                # 如果有图片，使用mixed类型来支持附件
                msg = MIMEMultipart("mixed")

                # 创建related部分来包含HTML和内嵌图片
                related_msg = MIMEMultipart("related")
                html_part = MIMEText(html_content, "html", "utf-8")
                related_msg.attach(html_part)

                # 添加图片附件
                for image_info in image_infos:
                    image_part = self._process_image(image_info)
                    if image_part:
                        related_msg.attach(image_part)

                msg.attach(related_msg)
            else:
                # 没有图片，直接使用alternative
                msg = MIMEMultipart("alternative")
                html_part = MIMEText(html_content, "html", "utf-8")
                msg.attach(html_part)

            msg["Subject"] = subject
            msg["From"] = self.config["sender"]
            msg["To"] = receivers or self.config["receiver"]

            if cc:
                msg["Cc"] = cc
            if bcc:
                msg["Bcc"] = bcc

            # 发送邮件
            context = ssl.create_default_context()
            server = smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"])

            if self.config.get("use_tls", True):
                server.starttls(context=context)

            server.login(self.config["sender"], self.config["password"])

            all_receivers = []
            for receiver_list in [msg["To"], msg.get("Cc", ""), msg.get("Bcc", "")]:
                if receiver_list:
                    all_receivers.extend(
                        [email.strip() for email in receiver_list.split(",")]
                    )

            server.sendmail(self.config["sender"], all_receivers, msg.as_string())
            print(f"邮件发送成功: {subject}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"SMTP认证失败: {e}")
            print("请检查QQ邮箱的SMTP密码是否正确，或者是否开启了SMTP服务")
            return False
        except smtplib.SMTPException as e:
            print(f"SMTP发送失败: {e}")
            return False
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False
        finally:
            if server:
                try:
                    server.quit()
                except smtplib.SMTPException as e:
                    print(f"警告: SMTP QUIT 命令失败，但邮件已发送: {e}")

    def send_plain_email(
        self,
        subject: str,
        content: str,
        receivers: str = None,
        cc: str = None,
        bcc: str = None,
        is_html: bool = False,
    ) -> bool:
        """发送纯文本邮件

        Args:
            subject: 邮件主题
            content: 邮件内容
            receivers: 收件人（逗号分隔）
            cc: 抄送（逗号分隔）
            bcc: 密送（逗号分隔）
            is_html: 是否为HTML格式

        Returns:
            bool: 发送是否成功
        """
        server = None
        try:
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = self.config["sender"]
            msg["To"] = receivers or self.config["receiver"]

            if cc:
                msg["Cc"] = cc
            if bcc:
                msg["Bcc"] = bcc

            # 添加内容
            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(content, content_type, "utf-8"))

            # 发送邮件
            context = ssl.create_default_context()
            server = smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"])

            if self.config.get("use_tls", True):
                server.starttls(context=context)

            server.login(self.config["sender"], self.config["password"])

            all_receivers = []
            for receiver_list in [msg["To"], msg.get("Cc", ""), msg.get("Bcc", "")]:
                if receiver_list:
                    all_receivers.extend(
                        [email.strip() for email in receiver_list.split(",")]
                    )

            server.sendmail(self.config["sender"], all_receivers, msg.as_string())

            print(f"邮件发送成功: {subject}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            print(f"SMTP认证失败: {e}")
            print("请检查QQ邮箱的SMTP密码是否正确，或者是否开启了SMTP服务")
            return False
        except smtplib.SMTPException as e:
            print(f"SMTP发送失败: {e}")
            return False
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False
        finally:
            if server:
                try:
                    server.quit()
                except smtplib.SMTPException as e:
                    print(f"警告: SMTP QUIT 命令失败，但邮件已发送: {e}")


# 全局邮件发送器实例
email_sender = MarkdownEmailSender()


def send_markdown_email(
    subject: str, markdown_content: str, receivers: str = None
) -> bool:
    """发送Markdown格式邮件的便捷函数

    Args:
        subject: 邮件主题
        markdown_content: Markdown格式的内容
        receivers: 收件人（逗号分隔）

    Returns:
        bool: 发送是否成功
    """
    return email_sender.send_email(subject, markdown_content, receivers)


def send_plain_email(subject: str, content: str, receivers: str = None) -> bool:
    """发送纯文本邮件的便捷函数

    Args:
        subject: 邮件主题
        content: 邮件内容
        receivers: 收件人（逗号分隔）

    Returns:
        bool: 发送是否成功
    """
    return email_sender.send_plain_email(subject, content, receivers)


if __name__ == "__main__":
    test_simple = """
# 测试邮件

这是一个测试邮件，包含 **Markdown** 格式的内容。

## 功能特性

- 支持 **粗体** 和 *斜体*
- 支持代码高亮：`print("Hello World")`
- 支持表格

| 功能 | 状态 |
|------|------|
| Markdown转HTML | ✅ |
| 表格支持 | ✅ |

## 代码示例

```python
def hello():
    print("Hello, World!")
```
## 交易结果图表

![BTC交易结果](/usr/home/yzzhu/HFT-Research/log/results/08/16/crypto_level100_25-0407_ave15+top10_earlystop_rollval_mixed/simulated_trading/symbol_binance_spot_btc_usdt_label_number_3_max_depth_8_threshold_0.76_position_limit_20_mixed.png)


> 这是一个引用块

1. 有序列表项1
2. 有序列表项2
3. 有序列表项3

[链接示例](https://www.example.com)
    """

    print("测试邮件")
    success = send_markdown_email("测试邮件", test_simple)
    if success:
        print("测试邮件发送成功")
    else:
        print("测试邮件发送失败")
