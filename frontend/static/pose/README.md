# 画面计数所用文件来源

这套文件只用于本机画面中的人体位置计算，不会把相机画面上传给模型提供方。当前实现统计举臂或移动次数，不判断羽毛球击球是否正确。

运行文件：来自 `@mediapipe/tasks-vision` 0.10.32 的 `wasm` 目录。该包声明 Apache-2.0；本目录保留官方项目的许可原文 `LICENSE-mediapipe.txt`。

- 项目：https://github.com/google-ai-edge/mediapipe
- 包：https://www.npmjs.com/package/@mediapipe/tasks-vision/v/0.10.32
- 许可原文：https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE

人体位置模型：`pose_landmarker_lite.task`，取自官方存储地址：
https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task

模型说明：https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
模型的使用条款应以官方模型页面当时的说明为准，不能仅凭程序包的许可推定所有模型和训练数据的权利。正式发布前应复核。

以下为本项目当前文件的SHA-256，后续更新时一并更新并重新检查计数：

```text
6f6b86509cf9e163ea1cfec7edc8cf53732699c04781e4c21c557c1ba402310e  vision_wasm_internal.js
cb3ec20026a9aecc2a81a93c25630ceb5389297ddb7a5f0bd61dd09cde606b9b  vision_wasm_internal.wasm
9f8fc960e363f0fb2f42f7937b97ae9cf9a5630490f71031fa90caa9bb121938  vision_wasm_nosimd_internal.js
924274fcd5ac8985f6570a8573e7971b7bd2d580ba1b8f3beb0ba8f95db6347c  vision_wasm_nosimd_internal.wasm
59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a  pose_landmarker_lite.task
```
