"""AI 冰箱配餐 - 使用通义千问 API 根据冰箱食材生成菜谱"""
import json
import streamlit as st
from openai import OpenAI


def ai_generate_recipe(ingredients: list[str]) -> dict | None:
    """
    根据冰箱里现有的食材，让 AI 推荐一道可做的菜。
    
    Args:
        ingredients: 冰箱里现有的食材名称列表
    
    Returns:
        dict with keys: name (菜名), needed (所需食材), steps (烹饪步骤), missing (缺少的食材)
        失败返回 None
    """
    api_key = st.secrets.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        st.error("未配置 DASHSCOPE_API_KEY，请在 Streamlit Secrets 中添加")
        return None
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    ingredients_str = "、".join(ingredients)
    
    system_prompt = """你是一位经验丰富的家庭厨师。用户会告诉你冰箱里有什么食材，请根据这些食材推荐一道美味家常菜。

要求：
1. 优先使用冰箱里已有的食材，尽量不增加额外食材
2. 如果必须添加1-2种常见调料/食材（如盐、酱油、蒜、葱等），可以在 missing 中列出
3. 菜名要具体、有食欲
4. 烹饪步骤要简洁实用，3-6步即可
5. 必须以 JSON 格式回复，不要包含其他内容

JSON 格式：
{
  "name": "菜名",
  "needed": ["需要的食材1", "需要的食材2", ...],
  "steps": ["步骤1", "步骤2", ...],
  "missing": ["缺少的食材1", ...]
}"""
    
    user_prompt = f"我冰箱里有：{ingredients_str}\n\n请推荐一道我能做的菜。"
    
    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=800
        )
        
        content = response.choices[0].message.content.strip()
        
        # 清洗可能的 markdown 代码块标记
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        
        recipe = json.loads(content)
        
        # 验证必要字段
        if not all(k in recipe for k in ("name", "needed", "steps")):
            raise ValueError("AI 返回的数据缺少必要字段")
        
        recipe.setdefault("missing", [])
        return recipe
        
    except json.JSONDecodeError:
        st.error("AI 返回格式异常，请重试")
        return None
    except Exception as e:
        st.error(f"AI 配餐出错：{e}")
        return None
