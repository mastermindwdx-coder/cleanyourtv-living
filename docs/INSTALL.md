# 安装、使用与恢复

先读 [兼容表](LOCAL-FORK-COMPATIBILITY.md)。Android 8+ 只表示可尝试普通应用运行，不表示 Home 守护或厂商屏保兼容。全流程使用你自己的电视地址，示例 TV_SERIAL 不是可直接运行的设备。

## 1. 准备

按 [BUILD](BUILD.md) 构建已签名 APK。开启电视 ADB 并在电视上确认电脑授权；`adb -s TV_SERIAL get-state` 应为 device。读型号/固件/ABI/原 Home 等，保存原包列表、禁用列表、无障碍、通知与屏保设置，详见 [Agent 指南](LOCAL-FORK-AGENT-GUIDE.md)。个人材料放仓库外或被忽略的 private/。

同包名已安装时先核对签名；安装冲突保留现有应用，不靠卸载解决。普通安装不关闭原桌面、不自动授权系统权限。

```text
python custom-tools/clean_install.py install --serial TV_SERIAL --apk PATH_TO_SIGNED_APK
```

先检查应用库、＋、长按移除、方向键与返回。桌面可以独立使用，不需要启动电脑助手常驻。

## 2. 按设备决定 Home 方案

仅 MiTV-MFTR0 / OS3.0.101.0.UFTMATV 的已验证路径：

```text
python custom-tools/clean_install.py setup-home --serial TV_SERIAL --state-dir private/backups
```

首次记录原状态后再配置 WRITE_SECURE_SETTINGS、悬浮/使用状态、无障碍与通知守护。原厂 Home 仍保留。实体遥控器约 2 秒内连按 3 下 Home，切过去再切回来，验证方向键单步、长按、音量、返回。需要暂时保持 ADB 时明确追加 --keep-adb；默认不保持，不修改省电待机。

其他机型停在普通应用阶段，交给 Agent 建自己的适配路径。不能删校验再重试。Aerial 等其他 Home 守护需先按自己的原记录暂停，禁止多个守护争抢。

## 3. 主题和应用

默认没有电影图片。按 [主题指南](THEMES.md) 导入自己的图集；公开静态预设包含下置 Dock、无背景色光晕、5 分钟顺序轮换和闲置时钟。应用用＋添加、长按 OK 移除快捷方式，不改变安装状态。

## 4. 可选广告体检

```text
python custom-tools/clean_tv.py scan --serial TV_SERIAL --state-dir private/backups
python custom-tools/clean_tv.py watch --serial TV_SERIAL --state-dir private/backups
```

scan 是只读状态核对；watch 让已授权电脑响应电视体检页的操作。当前白名单仅小米 com.xiaomi.mitv.hyper.screensaver；操作会连同该组件时钟/天气/照片功能一起停用，应先确认用途。电视页的确认保留。体检按钮不会变成通用一键清理。已提前禁用的组件不记作本工具新改动；旧记录独立保存。

## 5. 结束维护

```text
python custom-tools/clean_install.py end-maintenance --serial TV_SERIAL
```

先核对 keep_adb=false，再在电视设置关闭 USB/网络调试、按需撤销授权，用户方便时重启并用 `python tools/adb-closed.py TV_IP` 检查。可达且端口关闭才算关闭；连不上电视不等于端口安全。此流程明确断开调试，后续维护需本人重新开启。日常 Home 守护不依赖电脑在线，关闭 ADB 后行为仍需各自实机确认。

## 6. 恢复有范围

```text
python custom-tools/clean_install.py restore-home --serial TV_SERIAL --state-dir private/backups
```

按原快照恢复本次 Home 配置；不卸载 APK、不回滚应用数据、不自动恢复此前别人禁用的组件。屏保恢复使用同一次 watch 的日志及电视“恢复原状态”按钮。状态被外部改动时提示冲突，不覆盖；设备/固件不匹配停止。作者的完整实机回滚尚未执行，工具已有断连/冲突测试。

壁纸另行保留旧配置/原图，主题 reset 只恢复默认，不是恢复你上一套个人图集。安装签名、应用数据和网络配置各自备份，不把安装快照当作全机镜像。
