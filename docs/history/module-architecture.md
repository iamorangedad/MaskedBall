# 假面舞会的模块划分

历史记录。写于 2026-09-30。一个网页进程加本机 Ollama。进程内部按职责拆开，模块之间只通过函数调用，不共用 JSON 文件，也不在请求线程里直接跑模型。

来源：[模块划分](/home/jetson/.cursor/projects/home-jetson-MaskedBall/canvases/module-architecture.canvas.tsx)

## 两条进程边界

网页进程负责账号、数据库、会话和推送。Ollama 单独进程负责生成。systemd 单元负责把网页进程拉起来，证书文件存在时才启用 HTTPS。

## 模块各自负责什么

| 模块 | 负责 | 不负责 |
| --- | --- | --- |
| store | SQLite 表结构、事务、定时备份 | 注册规则、谁能看聊天 |
| accounts | 注册、登录、可撤销会话、改密、重置码 | 画像文案、消息正文 |
| portraits | 公开名片和代聊用的私密背景 | 把背景发给浏览器上的别人 |
| moderation | 拉黑、举报 | 决定模型怎么写句子 |
| conversations | 消息、未读、双方才能读取 | 调用模型 |
| presence | 最近活跃时间、是否在线 | 画布怎么画 |
| notify | 把事件推给当前在线的连接 | 把事件写进数据库 |
| model | 队列、超时、每人限额、Ollama | HTTP 和 SQL |
| chat | 一次发送：检查拉黑、生成、落库、推送 | 解析 Cookie |
| space | 给当前用户组装节点和连线 | 生成回复 |
| http | 路由、Cookie、静态文件、SSE、TLS | 业务判断 |

## 开发顺序

顺序按依赖排：下面的模块不引用上面还没出现的能力。数据落在 `web/data/space.sqlite`。

| 顺序 | 交付 | 完成时可以验证 |
| --- | --- | --- |
| 1 | store | 重启后用户和消息还在，并留下备份文件 |
| 2 | accounts | 注册、登录、退出、改密、重置码 |
| 3 | portraits + moderation | 别人看不到背景；拉黑后不能发消息 |
| 4 | conversations + presence | 会话只有双方能读，未读和在线状态正确 |
| 5 | notify + model + chat | 真人消息立刻推送；模型调用排队并有限额 |
| 6 | space + http | 未登录不能拉空间；HTTPS 在有证书时开启 |
| 7 | 前端 | 登录注册、在线、未读、拉黑和举报能在页面上操作 |
| 8 | 部署 | systemd 单元和启动说明 |
| 9 | 规模化发现 | 人很多时再做服务端分页，这一轮不做 |
