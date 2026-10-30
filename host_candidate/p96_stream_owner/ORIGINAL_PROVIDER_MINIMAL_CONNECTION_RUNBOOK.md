# DSH → OmniGate：原版最小链路实机核查（不改既有引擎）

## 已确定的接线决策

保留原版 DSH 的 `dsh-llm-pi-ai`、`dsh-api-session-controller`、`dsh-client-ui-chat`、Cordis 会话投影和工具机制。用户唯一的消息输入在 DSH。原版模型适配器使用现有 OpenAI-compatible provider，不增加新的聊天 UI、SSE 客户端或云端中转。

候选连接：
`DSH 原版消息 → pi-ai 模型适配器 → http://127.0.0.1:8787/v1 → OmniGate → 原版 Native API`。

重要：P90 只适用于 OmniGate **网页气泡插入/发送**，不能作为 DSH 原版模型适配器是否准许发起 HTTP 请求的前置条件。**已在 P92 原候选类中纠正此混用**：网页气泡路径保留原 P90 输入框核验；原版模型路径使用 `P92DshRouteGate.forOriginalProviderTurn(turnId, trustedOriginalSessionCallback)`，要求来自原版会话控制器的当前有效用户 turn、在实际尝试发送前再次核验、以及现有原版 8787/Native owner 验证。原版 API 路径不做网页气泡点击，不因网页 `len=0` 被阻断。HTTP200 与已接受的用户 turn **仅证明请求初步接受，不证明模型已经回复**。`OriginalSessionTurn` 为待接入原版运行时的接口，当前仍只是在隔离源码里编译和测试，**未上线**；禁止把外部任意 boolean、JS 消息或模型输出伪装成可信会话回执。保留 P90 的网页虚假 SENT 防护。

## 使用当前可执行只读检查

在实际负责模型 HTTP 调用的 **原版 DSH Node 进程运行环境** 中执行：

```sh
node omnigate_local_preflight.mjs
```

文件位于本目录。需要先把文件放入该 Node 环境可读的路径。如果当前 DSH 仅允许受限制的工具或不存在终端，**不可假设上述命令能执行**，不得偷偷解除沙箱、修改原版引擎或私自启用高权限。

脚本只请求 `GET http://127.0.0.1:8787/health`；只有主/悬浮运行时所有者已被验证，才继续只读 `GET /v1/models`。固定占位符只用于本地模型列表读取，不读取或打印真实 API key、Cookie 或模型名称。永不 POST、发送用户提示词、自动重试、停止正在生成的模型或重启原版服务。CLI 的固定端口为 8787；代码里的端口参数只用于离线单元测试。

判读：
- `READONLY_LOCAL_API_READY_NOT_MODEL_TURN_PROOF`：只证明本次健康检查和模型列表读取成功；**不证明 DSH 已收到模型回复**。后续需单次、用户主动发起的 DSH 聊天及工具调用实机验证。
- `NATIVE_OWNER_UNVERIFIED_NO_POST`：预估后续 POST 可能被 409 拒绝；保留原版网页和端口，先核实 OmniGate 对主/悬浮 WebDriver 的真实归属，不绕过 409。
- `ISOLATED_LOOPBACK_DENIED`：本次运行 Node 无权限访问 loopback。已知 P31 隔离 UID 下 TCP 曾返回 EACCES；这不表示应放宽隔离网络权限。未来需要可信 Android 宿主进程的严格白名单本地 API Broker，且只转发经过授权、与当前原版会话关联的请求。当前尚未接线。
- `LOCAL_LISTENER_MISSING`、`LOCAL_LISTENER_TIMEOUT`：需要排查同设备监听器和应用存活；不得自行重启正在执行中的模型。
- `MODEL_CATALOG_EMPTY_OR_INVALID` 或 `MODELS_HTTP_NON200`：即使健康检查通过，模型配置仍不可用。此状态不许写成成功。
- `UPSTREAM_UNREACHABLE_OR_UNKNOWN`：原版 Native API 不可达；没有确认属于当前 MainActivity 或 OverlayService 的监听者。

## 原版 UI 的后续用户授权实验

仅在空闲、没有正在生成的对话时，使用 DSH **原有模型设置** 选择/验证 OpenAI 兼容协议及 `http://127.0.0.1:8787/v1` 的 baseURL；以 UI 所支持的模型选择及凭证机制为准，不能凭静态字符串推定 UI 字段一定可编辑。不要修改原版模型 ID、配置库、数据库、登录状态或已有会话以强行使协议通过。

用户手动发起一条非工具普通短消息，必须依次核实：原版 DSH 会话实际记录用户 turn → OmniGate GET/POST 时 owner 路由匹配 → `/v1/chat/completions` 实际流经原版 Native API → 正常内容增量回到 DSH 现有消息投影 → 同一模型 turn 标记完成。随后另测工具返回继续生成，特别是拒绝发布评论时仍能得到类型化失败结果，不重复发出未经批准的评论。

## 不得误报

当前仅验证只读 Node 检查器及归档静态接口：未安装新的 DSH APK、没有证明 DSH 与 OmniGate 的实机完整模型调用、没有完成严格沙箱内的本地 API Broker、B站登录/评论、WebView 隐藏或自动换对话实机验收。原始签名、原版模型、3080、Native API 监听端口及 8787、Cookie/session 均保持不变。禁止生成正式 v139 APK 或合并该 Draft PR，直至原版节点真实调用和授权发布链路经过手机端验证。


## 原版 Pi-AI 模型路由配置（源码验证，不自动写入）

原版签名 v138 的 `@deepseek-ai/dsh-llm-pi-ai/lib/index.js` 已按 APK SHA256 和包内源文件 SHA256 检查：其路由 schema 明确存在 `displayName`、`api`、`baseURL`、`models`、`apiKeyEnv`（凭证引用）、`defaultContextWindow`、`defaultMaxTokens` 和 `defaultInput`。每个自定义模型必须具备真实的 `id`；`maxTokens`、`contextWindow` 不可假冒远端能力。

运行已有的离线纯 Node 配置生成器：

```sh
node original_dsh_omnigate_profile.mjs \
  --model-id "REPLACE_WITH_ACTUAL_MODEL_ID" \
  --context-window ACTUAL_VERIFIED_CONTEXT_CAPACITY \
  --max-tokens ACTUAL_VERIFIED_OUTPUT_CAPACITY
```

命令中的模型 ID 与两项容量必须换成从正在使用的模型提供方、设备端模型清单或官方说明**实际核验**的值；任意缺项、负数、越界或伪造凭证参数均拒绝输出。若 DSH 实际需要凭证映射，仅允许追加 `--credential-env OMNIGATE_LOCAL_API_KEY`，并从 DSH 原有受信凭证机制设置该环境变量。**不是把 API Key 的真实内容作为参数、写入仓库或粘贴到聊天。**

输出是原版 Pi-AI 的一个候选 *provider profile 对象*，**不是整个 DSH 设置文件**。它不自动导入、不自动增删配置、不能保证当前版本的设置 UI 具有粘贴该对象的入口。正式应用前必须验证原版 `dsh-llm-pi-ai` 插件的配置存储键和实际模型选择/修改 UI，采用原版配置流程并备份原设置；禁止通过猜测文件目录和覆盖用户数据强行安装配置。

生成器只声明 `input:["text"]`；原版图片/文件发送和工具结果能力均需独立确认，不可用“支持 OpenAI 兼容协议”推断已经打通。

源码校验与生成器回归记录：P96 现有 CI；未在用户手机运行，未连接当前 DSH Node 实际会话，未自动改变模型、OmniGate、沙箱、B站浏览器或登录信息。

## 真实原版 pi-ai 模型适配器的合成 SSE 与工具结果验证

2026-10-30：在私有 GitHub Actions 中，校验签名 v138 APK 的精确 SHA256，并临时从 engine.bin 提取原版 @earendil-works/pi-ai 及声明依赖。执行测试前清除 GH_TOKEN、GITHUB_TOKEN 与 Actions OIDC 环境变量；仅启动本机 127.0.0.1 端口的合成 SSE 服务。执行后清理临时包，不发布提取后的原版代码。未安装或改动原版 DSH APK。

- p96_original_pi_ai_probe.mjs：真实加载原版 openai-completions.lazy，并调用 openAICompletionsApi() 工厂；其结果包含 stream 与 streamSimple。pi-ai 包根入口本身没有直接导出 streamSimple。
- p96_real_original_stream_fixture.mjs：原版 streamSimple 对临时本地模型接口恰好发送一次 streaming POST，真实接收 start、text_delta、done 等事件，重组合成文本与预期完全一致。
- p96_real_original_tool_fixture.mjs：通过原版上下文系统消息的 toolsAdded 声明无副作用工具，原版 SDK 真实发送 OpenAI function 工具定义；接受工具调用分片并生成 toolCall；把合成工具结果加入同一模型会话后，原版 SDK 第二次发送的请求包含 role=tool，并收到继续生成的回复。
- 先前把定义放在 context.tools 和 system.tools 的测试均失败。已通过阅读原版 pi-ai/dist/utils/transcript.js 的 resolveTranscriptTools/getDeclaredTools 确认：有效的内部工具注册字段是系统消息 toolsAdded。该字段不是用户公开授权接口，不得让模型或网页自行宣称获得权限。

以上证明原版 pi-ai 协议层真实文本流消费及无副作用工具结果往返；**不证明** DSH Cordis/agent-loop 已接入、真实 Android Native ApiServer 路由和 409 门禁通过、隔离 UID 可访问 8787、原版 WebView 登录保持、B站评论授权发布或 OmniGate 上限续接已在手机完成。

后续只有原版 DSH agent/session 与模型调用之间的现有事件接线、隔离进程的可信本机通信、真实设备逐步验收可解除正式 APK 发布阻断。禁止重新建立第二套聊天引擎、盲目放开隔离网络或触碰实际用户凭证。
## P92 传输成功不得冒充模型回复成功

2026-10-30 已修正 P92DshRouteGate：原版 DSH 用户 turn 与 HTTP 200 同时成立时，状态只允许进入 ORIGINAL_TRANSPORT_ACCEPTED_REPLY_UNVERIFIED，isConfirmed() 必须仍然为 false。若这之后连接断开，改为 UNKNOWN_AFTER_DISPATCH，禁止盲目重发。网页气泡路径 P90 的独立 readback/点击/用户 turn 验证及已确认状态不受影响。

已在 JVM 回归中验证 P92_ORIGINAL_HTTP200_NEVER_FAKE_ASSISTANT_COMPLETION=PASS。这只是候选组件的防虚假成功修复，尚未接入原版 Android DSH；接入后实际模型回复必须由原版会话投影和可信 assistant 完成事件确认，不能从 HTTP200、SSE [DONE] 或单独 UI 点击推断。
## 原版 AgentLoop、ToolRuntime 与 Cordis 真实运行时边界（2026-10-30）

原版签名 v138 的精确哈希锁定源码首先确认原版 `@deepseek-ai/dsh-agent-loop` 直接依赖 `@deepseek-ai/dsh-tools`、`dsh-llm`、`dsh-session`、`dsh-session-persistence` 等组件。进一步通过临时原版依赖闭包、实际 Node20 import 成功加载 `AgentLoop`、`ToolRuntime` 和 `SessionController`，不是只扫描源码，也不是测试替身。

对原版导出类的公开方法反射已确认：`AgentLoop.create/resume/resumeWith/prepare`；`ToolRuntime.register/execute/dispatchToolBody/notifyResult/createExecution/resolveExecution`；`SessionController.prompt/follow/liveProjections`。这些名称只证明原版模块表面，不代表调用参数、插件生命周期或生产环境受权接线已经验证。

关键已证实回调：`ToolRuntime.notifyResult(exec,result)` 通过 Cordis 事件派发 `tools/result`，其参数携带原版 execution 和 result。CI 中实际加载了原版 `ToolRuntime` 和原版 `@deepseek-ai/cordis` 的 `Context`，使用严格无副作用的内存执行对象，调用原版 `notifyResult`，**真实 Cordis 订阅器恰好收到一次事件**。所有断言 PASS；未实例化 Android EngineManager，未调用原版浏览器、用户账号或模型。

**原版运行链首选设计**：`AgentLoop → ToolRuntime.execute → 原版工具实现 / Android 可信宿主 Broker → ToolRuntime.notifyResult → 原版 agent/session 继续模型流`。现在已经验证的是事件派发接口，不是 AgentLoop 的后续消费。不能让 P94 独立转发器在同一原版调用中另行注入第二份 OpenAI `role=tool`：必须防止重复结果、重试副作用及跨会话串结果。P94 现为独立隔离候选，不是生产接线。

接下来的实机验收必须使用原版 DSH 发起一条**无副作用的浏览器读取**，观察原版 ToolRuntime 是否调用真实浏览器执行器、P85 是否得到单次可信终态、原版 `tools/result` 是否触发、AgentLoop 是否在同一会话发起下一次模型请求，以及原版 WebView 聊天 UI 是否更新。只可在用户明确确认后执行评论发布、输入提交等外部副作用。原版模型所有者 409、隔离 UID 的 TCP EACCES、登录持久化和隐藏 WebView 保活均仍独立阻断。

现阶段没有原版 Android EngineManager 可写原生源码，也没有手机实际调用验证，因此该 PR 保留 Draft，**不得生成或宣布正式升级 APK**。无需再写第二套 SSE 消费器、Model Tool Dispatcher 或 Session Store。
## 原版真实 ToolRuntime 执行和 Pi-AI 双轮往返（2026-10-30）

使用 SHA-locked v138 APK 的原版 `@deepseek-ai/cordis`、`@deepseek-ai/dsh-tools`、`@earendil-works/pi-ai` 模块，在私有 GitHub Actions 临时 Node20 环境中完成。唯一测试替代项是无副作用的本机 HTTP SSE 服务器与最小 `systemPrompt.tools()` 内存注册服务。未安装 Android APK、未使用实际 DSH 用户配置或执行网页、命令、文件、外部网络。

首先按原版 Cordis 生命周期 `ctx.provide('systemPrompt',{tools(){...}})` → `await ctx.plugin(ToolRuntime,{mode:'native'})`，由真实 Cordis 提供 ToolRuntime 服务。直接 `new ToolRuntime(...)` 不成立；缺少 systemPrompt、缺少 `systemPrompt.tools()`、未等待插件初始化都曾产生真实阻断。**不得用这些简化试验替代 Android 宿主的可信注册与授权。**

原版 `ToolRuntime.register` 注册固定数据工具，调用真实 `ToolRuntime.execute` 后工具体恰好运行一次；原版 `tools/result` 事件恰好发出一次，结果 `isError=false`。输出 `output.render` 需返回 JSON 无损可序列化内容；最初返回包含 `undefined` 的字段时原版返回错误，已严格修正并保留回归。

进一步通过 `p96_original_model_toolruntime_roundtrip.mjs` 直接串联：原版 Pi-AI `streamSimple` 从本机模拟模型 SSE 中收到一次 `toolCall` → 原版 ToolRuntime 对应 callId 执行一次固定内存工具 → 原版 Cordis 触发一次 `tools/result` → 将该原版执行产生的 `result.content` 作为同一 callId 的 `toolResult` 交给原版 Pi-AI → 第二轮实际 OpenAI Completions POST 含 `role=tool` 并生成终止回复。**CI 中双轮原版模块真实运行通过，调用与通知均为一次，没有在 test 侧手工伪造 ToolRuntime 的执行回执。**

门禁精确为 `P96_ORIGINAL_TOOL_RUNTIME_REGISTER_EXECUTE_NOTIFY=PASS`、`P96_ORIGINAL_PI_AI_TOOLRUNTIME_TWO_TURN_ROUNDTRIP=PASS`、`P96_ORIGINAL_TOOL_RUNTIME_EXECUTIONS=1` 和 `P96_ORIGINAL_TOOL_RESULT_NOTIFICATIONS=1`。临时原版方法体源码调试脚本已删除，不作为项目代码或 Action 输出保留。

**发布阻断依然存在**：这不是 `dsh-agent-loop.AgentLoop` 的真实驱动。测试用已经验明的 Pi-AI 格式构造模型上下文与调用，与 Android DSH EngineManager、实际 ToolRuntime 注册表、授权 native Broker、WebView 浏览器实际操作及 409 runtime owner 校验均未连接。严禁将该原版模块合成闭环声称为手机端 B站读取/评论、自动上限续接或后台浏览器隐藏功能完成。下一步只能在原版 EngineManager 的真实启动环境中注册可信受限浏览器工具，再验证模型产生调用、Native Terminal、会话持久化和 AgentLoop 自己的自动续接；不得额外注入重复 `role=tool`。
## 原版 AgentLoop：Node22 真实服务就绪，非手机自动续接（2026-10-30）

锁定原版 v138 APK SHA256，隔离 CI 中加载真正原版 `@deepseek-ai/dsh-agent-loop` 与六个插件服务：`@deepseek-ai/dsh-agent.AgentRegistry`、`@deepseek-ai/dsh-session.SessionStore`、`@deepseek-ai/dsh-llm.LlmRuntime`、`@deepseek-ai/dsh-tools.ToolRuntime`、`@deepseek-ai/dsh-system-prompt.SystemPrompt`、`@deepseek-ai/dsh-session-projection.SessionProjectionRegistry`。无伪造这些核心服务的注册。

原先 Node20 CI 下模块能 import，但 `AgentLoop` 激活抛出 `Promise.withResolvers is not a function`。Node22 CI 中所有六个原版服务均激活，`ctx.get('agentLoop')` 返回真实对象，`create()` 接口存在。现在 `p96_agentloop_original_services_boot.mjs` 会强制检查缺失依赖集合为空、真正 `AgentLoop.create` 函数存在以及 `Promise.withResolvers` 可用，失败必须终止 CI，不再以 `ctx.plugin` 返回句柄冒充 READY。保留既有原版 pi-ai 流式消息、ToolRuntime 一次执行 / 一次通知和两轮工具结果往返测试。

**注意**：此处测试运行时是 GitHub runner Node22，不证明用户手机原版 `assets/node-runtime.bin` 中实际 Node 版本，原版 Android `EngineManager` 启动路径未接到该测试。可直接判断的是此测试所经原版 AgentLoop 代码执行路径需要 `Promise.withResolvers`；手机运行时缺失此接口则不能直接运行相同路径。原版包 `engines.node` 声明与设备真机 `node --version` 必须分别确认，不能从 GitHub runner 推断。

**下一节点仅对真实原版执行器生效**：在受信的原版 `EngineManager` 中证明 Node 版本/特性、六服务依赖真实启动、实际 session 创建、`AgentLoop` 对 `tools/result` 的自动消费、Android Browser Broker 安全回传与原版聊天 UI 增量刷新；同时保留 409 所有者安全门禁和隔离 UID 拒绝回环直连。此前 `pi-ai ↔ ToolRuntime` 的显式二次调用是合成测试编排，不是 AgentLoop 自己的续接证明。没有此证据，PR 只能 Draft，不能合并或发布正式 APK。