# 图书馆自动预约与状态刷新脚本

这是一个图书馆预约系统的自动化 Python 脚本。支持一键分段预约全天座位；智能识别当前状态，在不干扰已签到座位的前提下，通过“断开重连”逻辑刷新预约状态。

## 🌟 核心功能

*   **全自动登录**：基于 Playwright 模拟真人登录 CAS 统一认证系统，自动抓取 `JSESSIONID`、`ic-cookie` 和 `token`。
*   **智能时区处理**：强制锁定北京时间 (UTC+8)，无论服务器在何处（如 GitHub Actions 的海外服务器），时间计算均准确无误。
*   **分段预约逻辑**：支持单次最高 4 小时预约，段与段之间自动预留 10 分钟容错间隔（Gap）。
*   **状态刷新 (Keep-alive)**：针对已开始但未签到的预约，执行“提前结束并立即续约”，防止因未签到导致的违规或失效。
*   **签到保护**：检测到 `resvStatus: 1093` (已签到) 时，自动跳过刷新逻辑，确保座位安全。

## 🛠️ 核心逻辑说明

脚本根据图书馆系统的实时返回，自动切换以下三种场景：

| 场景 | 触发条件 | 执行动作 |
| :--- | :--- | :--- |
| **场景 1: 冷启动** | 无任何进行中或未来的预约 | 从 `max(现在, 08:30)` 开始，按 4 小时一段向后铺满预约，直到 21:45。 |
| **场景 2: 静默期** | 当前无预约，但未来有预约 | 判定为处于 10 分钟 Gap 时间或等待下一次预约开始，脚本**保持静默**。 |
| **场景 3: 刷新期** | 存在进行中的预约 | 若**未签到**，则记录原结束时间，执行“提前结束”并立即重新预约到原定时间点。若**已签到**，则跳过。 |

## ⚙️ 环境变量配置

为了安全起见，所有敏感信息均通过环境变量读取：

| 变量名 | 说明           | 示例                    |
| :--- |:-------------|:----------------------|
| `LIB_USER` | 统一认证学号 (必填)  | `32206300066`         |
| `LIB_PASS` | 统一认证密码 (必填)  | `your_password`       |
| `LIB_SEAT_ID` | 目标座位 ID (必填) | `101267800`           |
| `MOCK_NOW` | 模拟当前时间 (调试用) | `2026-03-12 08:00:00` |

## 🚀 快速开始

### 1. 本地运行
```bash
# 安装依赖
pip install requests playwright
python -m playwright install chromium
```

### 2. GitHub Actions 部署
1.  新建一个 **public** 仓库并上传代码。
2.  进入仓库 **Settings -> Secrets and variables -> Actions**。
3.  添加 `LIB_USER` 和 `LIB_PASS` 到 **Repository secrets**。
4.  脚本支持两种触发方式：
    *   **手动触发**：在 Actions 页面手动点击 `Run workflow`。
    *   **远程触发**：通过阿里云函数计算 (FC) 发送 `repository_dispatch` 事件（类型为 `fc-timer-trigger`）进行高精度定时调度。

## 全过程生命周期

```mermaid
graph TD
    %% Main Flow Initiation
    Start["main()"] --> Auth["get_library_credentials()"]
    
    %% Authentication Subgraph
    subgraph Authentication [Playwright SSO Flow]
        Auth --> L1["Launch Headless Browser"]
        L1 --> L2["Intercept /auth/token"]
        L2 --> L3["Goto Library Homepage"]
        L3 --> L4{"Auto Redirect to CAS?"}
        L4 -- "No" --> L5["Click Login Button"]
        L4 -- "Yes" --> L6["Wait for CAS Page"]
        L5 --> L6
        L6 --> L7["Fill Credentials & Submit"]
        L7 --> L8["Wait for Redirect Back"]
        L8 --> L9["Extract JSESSIONID, ic-cookie & token"]
    end
    
    %% Post-Auth Flow
    L9 --> CheckAuth{"Auth Success?"}
    CheckAuth -- "No" --> End["Terminate"]
    CheckAuth -- "Yes" --> GetID["get_acc_no()"]
    GetID --> SmartLogic["smart_refresh_logic()"]

    %% Smart Logic Subgraph
    subgraph State Machine [Smart Refresh Logic]
        SmartLogic --> FetchStatus["Fetch Status (8450, 8452)"]
        FetchStatus --> ScenarioEval{"Evaluate Current State"}
        
        %% Scenario 1
        ScenarioEval -- "No active/future reservations" --> S1["Scenario 1: Full Day Reservation"]
        S1 --> S1_TimeCheck{"Is Time < 08:30?"}
        S1_TimeCheck -- "Yes" --> S1_Set830["Start = 08:30"]
        S1_TimeCheck -- "No" --> S1_SetNow["Start = Now + 1min"]
        S1_Set830 --> S1_Loop
        S1_SetNow --> S1_Loop
        S1_Loop["Loop: Reserve (Start to End)"] --> S1_Advance["Advance Time + Gap"]
        S1_Advance --> S1_LoopLimit{"End > Limit Time?"}
        S1_LoopLimit -- "No" --> S1_Loop
        S1_LoopLimit -- "Yes" --> S1_End["Finish Allocation"]

        %% Scenario 2
        ScenarioEval -- "Future reservations exist (8450)" --> S2["Scenario 2: Wait (Gap Time)"]
        
        %% Scenario 3
        ScenarioEval -- "Active reservation exists (8452)" --> S3["Scenario 3: Refresh Active"]
        S3 --> S3_Loop{"For each active resv:"}
        S3_Loop -- "Status == 1093 (Checked In)" --> S3_Skip["Skip (Keep status)"]
        S3_Loop -- "Not Checked In" --> S3_Cancel["Cancel Current (endAhaed)"]
        S3_Cancel --> S3_Rebook["Re-book: Now+1m to Old_End"]
    end

    %% Final
    S1_End --> Done["End Task"]
    S2 --> Done
    S3_Rebook --> Done
    S3_Skip --> Done
```

## ⚠️ 免责声明
本脚本仅供学习交流使用，请遵守图书馆相关管理规定。




