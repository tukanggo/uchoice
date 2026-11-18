import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI(title="AI E-commerce Pricing & Copywriting API")

# 配置跨域，方便前端调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义请求数据模型
class PricingRequest(BaseModel):
    product_name: str
    cost: float
    fee_rate: float = 27.0  # 默认 Shopee 扣点 27%
    other_cost: float = 0.0
    api_key: str = None     # 用户可传入自己的 Gemini API Key

@app.post("/api/analyze-pricing")
def analyze_pricing(req: PricingRequest):
    total_cost = req.cost + req.other_cost
    fee_decimal = req.fee_rate / 100.0

    # 如果用户提供了 API Key，则动态配置；否则尝试从环境变量获取
    api_key = req.api_key or os.environ.get("GEMINI_API_KEY")
    
    ai_analysis_text = ""
    ai_title = ""
    ai_points = []
    ai_desc = ""

    if api_key:
        try:
            genai.configure(api_key=api_key)
            # 使用 gemini-1.5-flash 模型
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"""
            You are an expert e-commerce financial analyst and copywriter for Shopee Malaysia.
            Product Name: {req.product_name}
            Base Cost: {req.cost}
            Other Cost: {req.other_cost}
            Total Cost: {total_cost}
            Platform Fee Rate: {req.fee_rate}%

            Task:
            1. Suggest a realistic target net margin percentage (e.g., between 15% and 30%).
            2. Calculate the optimal custom selling price based on this target margin.
            3. Provide a brief financial reasoning/analysis (in Simplified Chinese).
            4. Generate an optimized Shopee product title, 3 key selling points, and a marketing description.

            Output MUST be strictly in valid JSON format with the following keys:
            - "suggested_margin_pct": float
            - "suggested_price": float
            - "reasoning": string (financial analysis and pricing reason in Chinese)
            - "title": string
            - "points": list of strings
            - "description": string
            """
            
            response = model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)
            
            return {
                "success": True,
                "ai_generated": True,
                "suggested_margin_pct": data.get("suggested_margin_pct", 18.8),
                "suggested_price": data.get("suggested_price", round(total_cost / (1 - fee_decimal - 0.188), 2)),
                "reasoning": data.get("reasoning", "AI 分析完成"),
                "title": data.get("title", f"[Ready Stock] {req.product_name} - Best Value"),
                "points": data.get("points", ["高品质保障", "本地现货极速发货", "性价比首选"]),
                "description": data.get("description", f"欢迎光临！这款 {req.product_name} 现货热卖中。")
            }
        except Exception as e:
            # 如果 API 调用失败，自动降级到本地智能计算
            pass

    # 本地兜底智能计算（若无 API Key 或调用异常）
    target_margin = 18.8
    suggested_price = round(total_cost / (1 - fee_decimal - (target_margin / 100.0)), 2)
    
    return {
        "success": True,
        "ai_generated": False,
        "suggested_margin_pct": target_margin,
        "suggested_price": suggested_price,
        "reasoning": f"基于总成本 {total_cost:.2f} 及平台扣点 {req.fee_rate}%，推荐设定 18.8% 的净利润率以确保健康的盈利空间，同时具备市场竞争力。",
        "title": f"🔥 [Ready Stock] {req.product_name} - High Quality Gadget | Fast Shipping",
        "points": [
            "⚡ 高效实用：精选高品质材质，专为日常生活设计。",
            "🛡️ 品质保障：严格质检，经久耐用。",
            "🇲🇾 本地现货：马来西亚仓库闪电发货，售后无忧！"
        ],
        "description": f"📦 【产品详情】\n欢迎光临！这款 {req.product_name} 是您提升生活品质的必备好物。现货供应，下单后 24 小时内极速发出！"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
