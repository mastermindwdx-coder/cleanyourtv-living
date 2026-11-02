# 源码公开与后续发布

维护者已于2026-11-02明确授权将 `mastermindwdx-coder/cleanyourtv-living` 从Private改为Public，源码现已开放。首次公开仅覆盖经过允许清单检查的源码与文档，上传凭据和私人核对记录保存在维护者本地。

本次公开授权不自动扩展为发布个人APK、公共Pages或向其他人发送消息。后续代码修改、安装包与Release按相应明确指令执行。

- 本仓库根由 `git rev-parse --show-toplevel` 核实为独立目录。不要在 Creator_OS 根执行全量 git add。
- 检查 public-files.json / 导出包，运行 scripts/check_public.py；更新 VERIFICATION.md，阅读 KNOWN-LIMITATIONS.md。
- 首次发布采用源码，不上传作者个人 APK、电影壁纸、Google图标改包、配置/备份或私钥。若另发可安装正式 APK，须建立维护者私有签名、校验来源与记录 SHA。
- 操作前核实GitHub账号、目标仓库和授权范围；完成后从未登录的访问方式核对仓库及README可读，记录实际提交和Public状态。浏览器与连接器若是不同账号，以维护者指定的所有者为准。
- 检查 Actions 权限；当前工作流仅读代码和产出构建报告，无自动发布权限。公开后再按平台支持情况配置私密漏洞报告；不为此提前公开。
- GitHub 第一次 CI 必须真实跑完才能挂 passing 徽章；本地结果不等于云端绿灯。
- 需要实机宣传图时，用可公开主题在实际电视录制并遮掉账户/设备信息。现有hero是明确标注的功能示意。
