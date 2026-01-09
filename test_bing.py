"""测试Bing搜索"""
import asyncio
import aiohttp
from urllib.parse import quote
from bs4 import BeautifulSoup

async def test_bing():
    query = "2025年卫共流域水利工程"
    encoded_query = quote(query)
    url = f"https://www.bing.com/search?q={encoded_query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            print(f"Status: {response.status}")
            html = await response.text()
            print(f"HTML length: {len(html)}")

            # 保存HTML用于调试
            with open("bing_response.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("HTML saved to bing_response.html")

            soup = BeautifulSoup(html, 'html.parser')

            # 尝试不同的选择器
            selectors = ['.b_algo', '.b_results > li', '#b_results > li', '.b_ans', 'li.b_algo']
            for sel in selectors:
                items = soup.select(sel)
                print(f"Selector '{sel}': {len(items)} items")

            # 打印前几个搜索结果的结构
            results = soup.select('.b_algo')
            if results:
                print("\n--- First result structure ---")
                print(results[0].prettify()[:1000])

asyncio.run(test_bing())
