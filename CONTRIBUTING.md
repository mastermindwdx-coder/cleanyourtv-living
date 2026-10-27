# 参与贡献

欢迎完善逐机适配、中文体验、复现步骤与恢复方法。先读 AGENTS.md 和 docs/LOCAL-FORK-AGENT-GUIDE.md。

先在自己设备只读识别，之后保存私有备份；使用 docs/DEVICE-REPORT-TEMPLATE.md，逐项标记 passed/failed/not_tested/not_applicable。提供型号/固件、可复现步骤、预期/实际、针对性改动、验证与回退。真实遥控器、HDMI、断电重启不能用命令成功替代。

改动集中在必要路径，新设备分支默认不影响旧基线。不自动更改 power 模式，不把 root/刷机/工厂菜单作为常规适配。构建/测试见 docs/BUILD.md；新增公共文件需更新 public-files.json 并通过公开预检。截图分享前核对账号、Wi-Fi、位置、设备标识及素材授权。

目前只有一台作者设备；社区测试是新兼容结论的来源。维护者没有完成所有机型实测的承诺。提交到本仓库，不自动替作者向原项目发 PR。上游内容保留版权来源；本分支新增贡献按 MIT。
