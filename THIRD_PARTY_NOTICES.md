# 来源、许可与分发边界

| 内容 | 固定来源 / 许可 |
|---|---|
| CleanYourTV 核心、选定工具 | Gathin23/cleanyourtv @ f592b6d2db0cfa0e28779660f25ff65386a5ff9b；根 LICENSE（MIT） |
| Aerial 定制迁移的基础 | pengchujin/aerial-tv @ 2f54aafa3aba8ba6f8d588b6983a45198cea12b4；LICENSE-AERIAL（MIT） |
| Outfit 字体 | launcher/FONT-LICENSE-OFL.txt；OFL-1.1 |
| 新增适配工具、文档、SVG功能示意与网络/Companion源码 | MIT；保留仓库及 companion/LICENSE 的署名 |
| SmartTube 源补丁涉及原代码 | integrations/smarttube/LICENSE；MIT；补丁不附带品牌替换图片或完整客户端 |
| Gradle wrapper / AndroidX / Android SDK / 测试工具 | 各自原许可证；不因本仓库 MIT 改变；随附 wrapper 内原许可证另见 [GRADLE-WRAPPER.txt](licenses/GRADLE-WRAPPER.txt) |
| Clash Meta for Android 与其他外部软件 | 仅来源链接和版本记录，未捆绑其二进制/源码；不把外部许可改成 MIT |

最初导入的文件、来源哈希见 [source-provenance.json](docs/source-provenance.json)。该记录对应公开化前输入；发布包内 SOURCE-MANIFEST.json 是最终逐文件哈希。未携带上游完整 addons/examples/themes/维护机器人，是聚焦核心的独立分发，不是全量上游镜像。

原项目：[CleanYourTV](https://github.com/Gathin23/cleanyourtv)、[Aerial](https://github.com/pengchujin/aerial-tv)、[SmartTube](https://github.com/yuliskov/SmartTube)。原始源文件注释中的上游文档/issue指向它们，不能解读为本分支已验证。

不分发作者的怪兽公司/其他电影图、Google YouTube 原包图标、私人壁纸视频、个人网络、账号、设备日志/快照、签名及 ADB 密钥。公开默认只有代码生成的深色界面与配置；docs/assets/hero.svg 为手工矢量功能示意，非实机截图，不含 App 品牌图形。

商标/品牌归各自所有。本项目没有厂商或 Google 官方认证/合作声明。参考官方资料：[Gradle license](https://github.com/gradle/gradle/blob/master/LICENSE)、[Android signing](https://developer.android.com/studio/publish/app-signing)。
