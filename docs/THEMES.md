# 个人壁纸与公开主题

公开默认是无图片的深色界面，原生色彩与配置属于源码；不会分发作者个人电影图集。预设在 [personal-static/config.json](../themes/personal-static/config.json)。请把它复制到 private/my-theme/，在其 wallpapers/ 里放 01.jpg、02.jpg 等自己的图片。

预设 `rows_below_dock=0`、`ambient_glow=false`、`app_glow=false`、`wallpaper_rotation_minutes=5`、`wallpaper_order=sequential`、`clock_wallpaper=true`。这保留底栏下置与图片原色，让主页和闲置时钟共享图集。钟页是屏幕点亮时的闲置显示，真正省电待机仍熄屏。

使用上游主题工具需要独立 Python 环境：

```text
python -m venv tools/venv
tools/venv/Scripts/python.exe -m pip install -r tools/requirements.txt
```

Windows：`./tools/theme.ps1 -TvHost TV_IP private/my-theme`。Linux/macOS 对应环境路径 tools/venv/bin/python，设置 TV_HOST 后执行 `sh tools/theme.sh private/my-theme`。工具使用自己的授权 ADB 客户端，首次可能需在电视允许；不公开其 adbkey/。先保存原主题，应用会替换当前主题图集。reset 回到默认，不恢复旧文件。

图片源可为 4K，但本机静态 UI 合成分辨率为 1080p；不能把像素尺寸写成实显 4K 承诺。4 张每张 5 分钟的完整轮换目前未计时验收。没有个人图片时不伪造轮换成功。

可选“4K 动态壁纸”：本地横屏 MP4，主页/闲置时钟分别选，静音循环；页面离开释放，异常回退。当前验证素材限制由 VideoWallpaper.java 决定（3840×2160 至 4096×2304，最大 1 GiB），解码能力取决于设备。日常用户选择静态，仓库不带视频素材。

完整配置参考 [上游主题键说明](https://github.com/Gathin23/cleanyourtv/blob/f592b6d2db0cfa0e28779660f25ff65386a5ff9b/themes/README.md)。不要把来源未核实的图像提交为公共默认壁纸。
