from playwright.sync_api import sync_playwright
import time
from config import Config

def get_library_credentials(username, password):
    """
    通过 Playwright 模拟真实用户流程获取凭据
    """
    with sync_playwright() as p:
        print("正在启动浏览器...")
        # GitHub Actions 必须使用 headless=True
        browser = p.chromium.launch(headless=True) 
        
        context = browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        captured_token = None
        def handle_response(response):
            nonlocal captured_token
            if "ic-web/auth/userInfo" in response.url and response.status == 200:
                try:
                    data = response.json()
                    captured_token = data.get("data", {}).get("token")
                    if captured_token:
                        print(f"[Network] 成功截获 Token")
                except Exception:
                    pass
        page.on("response", handle_response)

        try:
            print("正在访问图书馆首页...")
            page.goto(Config.LOGIN_URL, wait_until="networkidle")
            
            if "newcas.gzhu.edu.cn" not in page.url:
                print("未自动跳转，尝试点击登录按钮...")
                try:
                    page.wait_for_selector("text=登录", timeout=5000)
                    page.click("text=登录")
                except:
                    print("未找到登录按钮，尝试直接跳转认证接口...")
                    page.goto("https://libbooking.gzhu.edu.cn/authcenter/doAuth/fdbb015893c74659bfc4ba356807817a")

            print("等待 CAS 统一认证页面加载...")
            page.wait_for_url("**/cas/login**", timeout=20000)

            print(f"正在输入账号...")
            page.wait_for_selector("#un", state="visible")
            page.fill("#un", username)
            page.fill("#pd", password)

            print("提交登录...")
            page.click("#index_login_btn")

            print("等待认证成功并跳回图书馆系统...")
            page.wait_for_url(lambda url: "libbooking.gzhu.edu.cn" in url and "errorMsg" not in url, timeout=30000)
            
            print("登录成功！正在采集凭据...")
            page.wait_for_load_state("networkidle")
            time.sleep(3) 

            cookies = context.cookies()
            jsessionid = next((c["value"] for c in cookies if c["name"] == "JSESSIONID"), "")
            ic_cookie = next((c["value"] for c in cookies if c["name"] == "ic-cookie"), "")

            if not captured_token:
                captured_token = page.evaluate("window.localStorage.getItem('token')")

            return jsessionid, ic_cookie, captured_token

        except Exception as e:
            print(f"[Fatal Error] {e}")
            return None, None, None
        finally:
            browser.close()
