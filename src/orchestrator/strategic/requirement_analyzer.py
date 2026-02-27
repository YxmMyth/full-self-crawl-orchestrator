"""[需求分析模块] - [通过] Chatbox [与用户交互，精确化需求]"""

import json
from typing import List, Optional, Tuple

from ..models import RefinedRequirement
from ..utils import get_llm_client


class RequirementAnalyzer:
    """[需求分析器] - [通过] Chatbox [与用户交互]"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()

    async def analyze(self, user_input: str) -> RefinedRequirement:
        """
        [分析用户输入，提取精确化需求]

        Args:
            user_input: [用户的自然语言输入]

        Returns:
            RefinedRequirement: [结构化的需求规格]
        """
        system_prompt = """[你是一个专业的数据需求分析师。你的任务是将用户的自然语言输入转换为结构化的需求规格。]

[请从用户输入中提取以下信息：]
1. **[调研主题]** (topic): [用户想要调研的核心主题]
2. **[目标字段]** (target_fields): [需要采集的数据字段，如标题、作者、时间等]
3. **[范围限制]** (scope): [地域或其他范围限制，如]"[国内]"[、]"[国外]"[、]"[全球]"[等]
4. **[时间范围]** (time_range): [数据的时间范围，如]"[近一年]"[、]"[近三个月]"[等]
5. **[期望数量]** (quantity): [期望获取的数据量，默认为]1000
6. **[其他约束]** (constraints): [任何其他特殊要求]

[请以]JSON[格式输出，格式如下：]
{
    "topic": "[主题]",
    "target_fields": ["[字段]1", "[字段]2", ...],
    "scope": "[范围]",
    "time_range": "[时间范围]",
    "quantity": 1000,
    "constraints": {}
}

[注意：]
- [如果用户没有明确指定某些字段，请根据上下文合理推断]
- target_fields [应该包含用户明确提到的字段]
- quantity [如果用户未指定，默认为]1000
"""

        user_prompt = f"[用户输入]: {user_input}"

        try:
            response = await self.llm_client.complete(
                system=system_prompt,
                user=user_prompt,
                temperature=0.3
            )

            # [解析]JSON[响应]
            result = json.loads(response)
            return RefinedRequirement(**result)

        except json.JSONDecodeError as e:
            # [如果]JSON[解析失败，使用默认值]
            print(f"Warning: Failed to parse LLM response as JSON: {e}")
            return RefinedRequirement(
                topic=user_input,
                target_fields=["[标题]", "[内容]", "[时间]"],
                scope="",
                time_range="[近一年]",
                quantity=1000,
                constraints={}
            )

    async def confirm(self, requirement: RefinedRequirement) -> Tuple[str, bool]:
        """
        [生成需求确认消息，等待用户确认]

        Args:
            requirement: [解析后的需求规格]

        Returns:
            Tuple[str, bool]: ([确认消息], [是否可以直接确认])
        """
        # [构建确认消息]
        confirm_message = f"""[我理解你想要]:

[📋] **[主题]**: {requirement.topic}
[📊] **[目标字段]**: {', '.join(requirement.target_fields)}
[🌍] **[范围]**: {requirement.scope or '[不限]'}
⏰ **[时间范围]**: {requirement.time_range or '[不限]'}
[📈] **[期望数量]**: {requirement.quantity}
"""

        if requirement.constraints:
            confirm_message += f"[🔒] **[其他约束]**: {requirement.constraints}\n"

        confirm_message += "\n[确认吗？](Y/N/[修改])"

        return confirm_message, False

    async def refine(self, user_input: str, current_requirement: RefinedRequirement) -> RefinedRequirement:
        """
        [根据用户的修改意见，精化需求]

        Args:
            user_input: [用户的修改意见]
            current_requirement: [当前的需求规格]

        Returns:
            RefinedRequirement: [精化后的需求规格]
        """
        system_prompt = """[你是一个专业的数据需求分析师。用户想要修改已解析的需求。]

[请根据用户的修改意见，更新需求规格。]
[当前需求规格以]JSON[格式提供。]
[请以]JSON[格式输出更新后的需求规格。]
"""

        user_prompt = f"""[当前需求规格]:
{json.dumps(current_requirement.model_dump(), ensure_ascii=False, indent=2)}

[用户修改意见]: {user_input}

[请输出更新后的需求规格](JSON[格式]):
"""

        try:
            response = await self.llm_client.complete(
                system=system_prompt,
                user=user_prompt,
                temperature=0.3
            )

            result = json.loads(response)
            return RefinedRequirement(**result)

        except (json.JSONDecodeError, Exception) as e:
            print(f"Warning: Failed to refine requirement: {e}")
            return current_requirement

    async def suggest_fields(self, topic: str) -> List[str]:
        """
        [根据主题建议常见的目标字段]

        Args:
            topic: [调研主题]

        Returns:
            List[str]: [建议的字段列表]
        """
        field_suggestions = {
            "[新闻]": ["[标题]", "[正文]", "[发布时间]", "[作者]", "[来源]", "[标签]", "[阅读量]"],
            "[媒体]": ["[标题]", "[正文]", "[发布时间]", "[作者]", "[来源]", "[标签]", "[阅读量]"],
            "[电商]": ["[商品名称]", "[价格]", "[销量]", "[评价]", "[店铺]", "[品牌]", "[分类]"],
            "[社交]": ["[内容]", "[发布时间]", "[作者]", "[点赞数]", "[评论数]", "[转发数]"],
            "[科技]": ["[标题]", "[正文]", "[发布时间]", "[作者]", "[来源]", "[标签]", "[阅读量]"],
            "[金融]": ["[股票代码]", "[价格]", "[涨跌幅]", "[成交量]", "[时间]", "[板块]"],
            "[房产]": ["[小区名称]", "[价格]", "[面积]", "[户型]", "[位置]", "[发布时间]"],
        }

        # [查找匹配的建议]
        for key, fields in field_suggestions.items():
            if key in topic:
                return fields

        # [默认字段]
        return ["[标题]", "[正文]", "[发布时间]", "[作者]"]
