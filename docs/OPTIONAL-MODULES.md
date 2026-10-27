# 在 CleanYourTV 基础上，看 YouTube、登录自己的账号

在 CleanYourTV 简洁主页、应用管理、壁纸与闲置时钟等核心体验的基础上，我们进一步打通了指定小米电视观看 YouTube、登录本人账号的流程。实现路径为：**个人 Clash/Mihomo 配置 → 电视端 VPN → SmartTube 播放 YouTube 内容 → 本人授权登录 → 订阅、播放列表与历史加载**。桌面、网络与影音客户端仍按模块分别安装。

| 环节 | 本机结果 | 我们提供的改动或方法 |
|---|---|---|
| 个人 VPN | 电视端 VPN、规则模式及 HTTPS 连通已验证 | 转换本人配置为电视副本，去电脑控制接口，保留指定局域网直连；原电脑配置不改 |
| YouTube 观看 | 搜索、频道打开、1080p60 AVC 和 1440p24 VP9 实播通过 | 电视端入口、网络与播放分层排查、默认网络引擎持久化核验、常见错误中文提示 |
| 账号登录 | 用户完成正常 Google 授权并确认成功；订阅、播放列表/稍后观看、账号历史加载 | 重新获取有效连接码，按电视提示通过 Chrome/Firefox 授权，随后验证账号页面与登录后实播 |

实测设备为 MiTV-MFTR0 / Android 14 / OS3.0.101.0.UFTMATV。登录、频道和账号内容能力来自 SmartTube 上游，我们没有改 OAuth 或解决 Google 官方 YouTube App 的设备认证。此前登录拒绝和 403 的唯一根因均未确认，不能把成功流程写成永久修复保证。4K60、待机后 VPN 自动恢复和长期稳定仍保留原验证边界。

核心桌面不依赖这些客户端，也不包含它们的 APK、网络订阅或账号。每位使用者按自己的设备和个人配置接入。

## TV Companion

[源码](../companion) 为独立 org.cleantv.companion 0.1.3：首页、网络、设备检测；SmartTube 打开、VPN状态、连接/断开/刷新及按需 HTTPS 检测。包申请 INTERNET，和离线桌面的权限分开。Netflix 项只展示安装/检测结果，存在入口不代表可播放。旧电视 Codex 代码已移除；升级迁移会清理本应用旧配对项，不动其他 App 的账号。

构建见 [BUILD](BUILD.md)。不接管 Home，不改变待机；第三方应用分别按自己的 ABI 安装。

## SmartTube 中文补丁

见 [补丁说明](../integrations/smarttube/README.md)。保留 SmartTube 上游图标和身份；不含从 Google YouTube APK 提取的图片。中文提示、独立包名和升级边界是我们的改动，频道/订阅/收藏/历史/登录是上游能力。

作者使用 Chrome/Firefox 完成电视显示地址与新连接码的正常授权后登录成功；先前拒绝的具体根因没有确认。需要本人授权，不能要求把账号密码、验证码或令牌提交到 Issue。登录后选择本人允许的内容实播，观察画面及时间推进，不用列表加载替代播放验证。

## 个人 Clash / Mihomo 配置

客户端来源 [Clash Meta for Android](https://github.com/MetaCubeX/ClashMetaForAndroid)，本机记录版本 2.11.36；[dependencies.json](../companion/dependencies.json) 是曾验证的下载记录，不保证未来兼容或最新。

```text
python -m pip install -r companion/scripts/requirements.txt
python companion/scripts/prepare_network.py --input PRIVATE_INPUT.yaml --output private/tv-config.yaml --lan YOUR_LAN_CIDR
```

输入是本人可用的 Mihomo 配置，LAN 为自家私网网段。脚本拒绝同路径/覆盖现有输出，保留节点，移除电脑控制接口/监听等，默认关闭 LAN 代理监听，添加局域网直连；REALITY short-id 必须为引号字符串，避免数字解析损失。不会修改电脑 Clash。

输出仍含个人敏感信息，只在自己的电视端客户端导入；授权 VPN 由本人完成。配置为一次性快照，不自动同步电脑；带 providers 的情况还要确认电视能获取对应资源。先验证网络，再做同片同画质播放；4K、DRM、认证与网络问题分开。待机/重启自动恢复未完整验收，不作为发布承诺。
