"""[候选站挖掘模块] - [基于需求生成候选站点列表]"""

import json
from typing import List

from ..models import CandidateSite, RefinedRequirement
from ..utils import get_llm_client


class SiteDiscovery:
    """[候选站挖掘] - [使用] LLM [生成真实站点]"""

    def __init__(self, llm_client=None, min_sites: int = 10, max_sites: int = 30):
        self.llm_client = llm_client or get_llm_client()
        self.min_sites = min_sites
        self.max_sites = max_sites

    async def discover(self, requirement: RefinedRequirement) -> List[CandidateSite]:
        """
        [基于需求生成候选站点列表]

        Args:
            requirement: [精确化后的需求]

        Returns:
            List[CandidateSite]: [候选站点列表]
        """
        system_prompt = f"""[你是一个专业的数据源分析师。你的任务是基于用户的调研需求，推荐真实存在的候选数据源网站。]

[请遵循以下规则：]
1. [推荐的网站必须是真实存在的]
2. [优先推荐知名、稳定、高质量的数据源]
3. [考虑网站的可访问性和数据质量]
4. [推荐] {self.min_sites} [到] {self.max_sites} [个站点]
5. [按优先级排序（]1-10[，]1[为最高）]

[输出格式为]JSON[数组]:
[
    {{
        "site_name": "[网站名称]",
        "site_url": "https://example.com",
        "description": "[网站描述]",
        "priority": 1
    }},
    ...
]

[注意：]
- site_url [必须是完整的]URL[（包含] https://[）]
- priority [范围是] 1-10[，数字越小优先级越高]
- [确保推荐的网站与用户需求高度相关]
"""

        user_prompt = f"""[调研需求]:
- [主题]: {requirement.topic}
- [目标字段]: {', '.join(requirement.target_fields)}
- [范围]: {requirement.scope or '[不限]'}
- [时间范围]: {requirement.time_range or '[不限]'}

[请推荐候选数据源网站。]
"""

        try:
            response = await self.llm_client.complete(
                system=system_prompt,
                user=user_prompt,
                temperature=0.7
            )

            # [解析]JSON[响应]
            sites_data = json.loads(response)

            # [调试输出]
            print(f"Debug: sites_data type = {type(sites_data)}")
            print(f"Debug: sites_data = {sites_data[:2] if isinstance(sites_data, list) else sites_data}")

            sites = []
            for site_data in sites_data:
                print(f"Debug: site_data type = {type(site_data)}, value = {site_data}")
                try:
                    if isinstance(site_data, dict):
                        site = CandidateSite(**site_data)
                        sites.append(site)
                    else:
                        print(f"Warning: site_data is not a dict, it's {type(site_data)}")
                except Exception as e:
                    print(f"Warning: Failed to parse site data: {e}")
                    continue

            # [限制数量]
            return sites[:self.max_sites]

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse sites from LLM response: {e}")
            # [返回一些通用站点作为备选]
            return self._get_fallback_sites(requirement)
        except Exception as e:
            print(f"Error in site discovery: {e}")
            return self._get_fallback_sites(requirement)

    def _get_fallback_sites(self, requirement: RefinedRequirement) -> List[CandidateSite]:
        """
        [获取备选站点列表（当]LLM[失败时使用）]

        Args:
            requirement: [精确化后的需求]

        Returns:
            List[CandidateSite]: [备选站点列表]
        """
        topic = requirement.topic.lower()

        # [根据主题返回不同的备选站点]
        fallback_map = {
            "[科技]": [
                CandidateSite(site_name="36[氪]", site_url="https://36kr.com", description="[创投科技媒体]", priority=1),
                CandidateSite(site_name="[虎嗅]", site_url="https://www.huxiu.com", description="[商业科技媒体]", priority=2),
                CandidateSite(site_name="[钛媒体]", site_url="https://www.tmtpost.com", description="[科技财经媒体]", priority=3),
                CandidateSite(site_name="[爱范儿]", site_url="https://www.ifanr.com", description="[科技媒体]", priority=4),
                CandidateSite(site_name="[雷锋网]", site_url="https://www.leiphone.com", description="[人工智能与科技创新]", priority=5),
            ],
            "[新闻]": [
                CandidateSite(site_name="[新浪新闻]", site_url="https://news.sina.com.cn", description="[综合新闻门户]", priority=1),
                CandidateSite(site_name="[网易新闻]", site_url="https://news.163.com", description="[综合新闻门户]", priority=2),
                CandidateSite(site_name="[腾讯新闻]", site_url="https://news.qq.com", description="[综合新闻门户]", priority=3),
                CandidateSite(site_name="[搜狐新闻]", site_url="https://news.sohu.com", description="[综合新闻门户]", priority=4),
            ],
            "ppt": [
                CandidateSite(site_name="Slidesgo", site_url="https://slidesgo.com", description="[免费]Google Slides[和]PPT[模板]", priority=1),
                CandidateSite(site_name="Canva", site_url="https://www.canva.com/presentations/templates", description="[在线设计平台，海量]PPT[模板]", priority=2),
                CandidateSite(site_name="SlideModel", site_url="https://slidemodel.com", description="[专业]PPT[图表和模板]", priority=3),
                CandidateSite(site_name="SlidesCarnival", site_url="https://www.slidescarnival.com", description="[免费]PPT[模板和]Google Slides", priority=4),
                CandidateSite(site_name="Envato Elements", site_url="https://elements.envato.com/presentation-templates", description="[高质量付费]PPT[模板]", priority=5),
                CandidateSite(site_name="GraphicMama", site_url="https://www.graphicmama.com/presentation-templates", description="[创意]PPT[模板]", priority=6),
                CandidateSite(site_name="24Slides", site_url="https://24slides.com/templates", description="[免费和付费]PPT[模板]", priority=7),
                CandidateSite(site_name="PoweredTemplate", site_url="https://poweredtemplate.com", description="[商业]PPT[模板]", priority=8),
                CandidateSite(site_name="SlideGeeks", site_url="https://www.slidegeeks.com", description="[商业和技术]PPT[模板]", priority=9),
                CandidateSite(site_name="PresentationGO", site_url="https://www.presentationgo.com", description="[免费]PowerPoint[模板]", priority=10),
                CandidateSite(site_name="TemplateMonster", site_url="https://www.templatemonster.com/ppt-templates", description="[专业]PPT[模板市场]", priority=1),
                CandidateSite(site_name="SlideSalad", site_url="https://slidesalad.com", description="[创意]PPT[模板]", priority=2),
                CandidateSite(site_name="Creative Market", site_url="https://creativemarket.com/templates/presentations", description="[设计师]PPT[模板]", priority=3),
                CandidateSite(site_name="Slidesmash", site_url="https://slidesmash.com", description="[免费]PPT[模板]", priority=4),
                CandidateSite(site_name="FPPT", site_url="https://www.free-power-point-templates.com", description="[免费]PowerPoint[模板]", priority=5),
                CandidateSite(site_name="PPTMON", site_url="https://pptmon.com", description="[免费]Google Slides[和]PPT[模板]", priority=6),
                CandidateSite(site_name="Just Free Slides", site_url="https://justfreeslide.com", description="[高质量免费]PPT[模板]", priority=7),
                CandidateSite(site_name="Presentation Magazine", site_url="https://www.presentationmagazine.com", description="[免费]PPT[模板资源]", priority=8),
                CandidateSite(site_name="Showeet", site_url="https://www.showeet.com", description="[创意]PPT[模板和图表]", priority=9),
                CandidateSite(site_name="iSlide", site_url="https://www.islide.cc", description="[中文]PPT[插件和模板]", priority=10),
            ],
        }

        # [检查主题关键词]
        for key, sites in fallback_map.items():
            if key in topic:
                return sites

        # [默认返回科技媒体]
        return fallback_map.get("[科技]", [])

    def filter_sites(self, sites: List[CandidateSite], requirement: RefinedRequirement) -> List[CandidateSite]:
        """
        [根据需求过滤站点]

        Args:
            sites: [候选站点列表]
            requirement: [精确化后的需求]

        Returns:
            List[CandidateSite]: [过滤后的站点列表]
        """
        # [按优先级排序]
        sorted_sites = sorted(sites, key=lambda s: s.priority)

        # [限制数量]
        return sorted_sites[:self.max_sites]

    async def validate_site(self, site: CandidateSite) -> bool:
        """
        [验证站点是否可访问]

        Args:
            site: [候选站点]

        Returns:
            bool: [是否可访问]
        """
        # [这里可以实现实际的可达性验证]
        # [例如通过] HTTP HEAD [请求检查]
        # [暂时返回] True
        return True
