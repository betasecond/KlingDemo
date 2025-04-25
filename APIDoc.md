```apidoc
@apiDefine KlingAuth

@apiHeader {String} Content-Type=application/json 数据交换格式。
@apiHeader {String} Authorization 鉴权信息，格式为 `Bearer xxx`，请参考官方接口鉴权文档获取 `xxx`。
```

```apidoc
@apiDefine KlingErrorResponse

@apiSuccess {Number} code 错误码，0 表示成功，其他值表示失败。具体定义见官方错误码文档。
@apiSuccess {String} message 错误信息描述。
@apiSuccess {String} request_id 请求 ID，系统生成，用于跟踪请求和排查问题。
```

```apidoc
@apiDefine KlingTaskStatus
@apiSuccess {String} data.task_status 任务状态。
枚举值:
<ul>
    <li><code>submitted</code>: 已提交</li>
    <li><code>processing</code>: 处理中</li>
    <li><code>succeed</code>: 成功</li>
    <li><code>failed</code>: 失败</li>
</ul>
```

---

# Kling AI API - 视频生成 (图生视频)

## 概述

本部分 API 提供基于图像输入生成视频的能力。

## 模型与能力概览

**不同模型版本、模式和时长支持的能力有所不同，请参考下表或官方最新能力地图选择合适的参数。**

| 功能         | 模型/模式/时长         | kling-v1 (std 5s) | kling-v1 (std 10s) | kling-v1 (pro 5s) | kling-v1 (pro 10s) | kling-v1-5 (std 5s) | kling-v1-5 (std 10s) | kling-v1-5 (pro 5s) | kling-v1-5 (pro 10s) | kling-v1-6 (std 5s) | kling-v1-6 (std 10s) | kling-v1-6 (pro 5s) | kling-v1-6 (pro 10s) |
| :----------- | :--------------------- | :----------------: | :-----------------: | :----------------: | :-----------------: | :-----------------: | :------------------: | :-----------------: | :------------------: | :-----------------: | :------------------: | :-----------------: | :------------------: |
| **分辨率**    |                        | 720p               | 720p                | 720p               | 720p                | 720p                | 720p                 | 1080p               | 1080p                | 720p                | 720p                 | 1080p               | 1080p                |
| **帧率**      |                        | 30fps              | 30fps               | 30fps              | 30fps               | 30fps               | 30fps                | 30fps               | 30fps                | 30fps               | 30fps                | 30fps               | 30fps                |
| **图生视频** | **视频生成**           | ✅                 | ✅                  | ✅                 | ✅                  | ✅                  | ✅                   | ✅                  | ✅                   | ✅                  | ✅                   | ✅                  | ✅                   |
|              | **首尾帧 (image_tail)** | ✅                 | -                   | ✅                 | -                   | -                   | -                    | ✅                  | ✅                   | -                   | -                    | ✅                  | ✅                   |
|              | **仅尾帧 (image_tail only)** | -                  | -                   | -                  | -                   | -                   | -                    | ✅                  | ✅                   | -                   | -                    | ✅                  | ✅                   |
|              | **运动笔刷 (masks)**   | ✅                 | -                   | ✅                 | -                   | -                   | -                    | ✅                  | -                    | -                   | -                    | -                   | -                    |
|              | **运镜控制 (camera_control)** | ✅                 | -                   | -                   | -                   | -                   | -                    | ✅ (仅simple)      | -                    | -                   | -                    | -                   | -                    |

*注意：上表为简化概览，具体支持情况请以官方文档为准。视频续写、对口型、视频特效等能力未在此处详述。*
*注意：包含尾帧 (`image_tail`) 和运动笔刷 (`dynamic_masks` / `static_mask`) 的请求目前通常仅支持生成 5s 的视频。*

---

## 1. 创建图生视频任务

```apidoc
@api {post} /v1/videos/image2video 创建图生视频任务
@apiVersion 1.0.0
@apiName CreateImageToVideoTask
@apiGroup ImageToVideo
@apiDescription 提交一个基于输入图像生成视频的任务。

@apiUse KlingAuth

@apiBody {String} [model_name="kling-v1"] 模型名称。 <br/> 枚举值: `kling-v1`, `kling-v1-5`, `kling-v1-6`。 <br/> *注意：为了保持命名统一，原 `model` 字段变更为 `model_name` 字段。继续使用 `model` 字段等价于 `model_name` 为空时的默认行为 (即调用 `kling-v1` 模型)。*
@apiBody {String} image **必须。** 参考图像。支持传入图片 Base64 编码或图片 URL（需确保可公开访问）。
    <ul>
        <li>格式: `.jpg`, `.jpeg`, `.png`。</li>
        <li>大小: 不超过 10MB。</li>
        <li>分辨率: 不小于 300x300px。</li>
        <li>宽高比: 在 1:2.5 到 2.5:1 之间。</li>
        <li>**重要提示 (Base64):** 若使用 Base64，请确保**不要**包含任何前缀 (如 `data:image/png;base64,`)，直接提供编码后的字符串。</li>
        <li>**重要提示 (互斥):** `image` 参数与 `image_tail` 参数至少二选一，二者不能同时为空。同时，`image` + `image_tail` 参数组合、`dynamic_masks`/`static_mask` 参数组合、`camera_control` 参数三者互斥，只能选择其中一种方式使用。</li>
        <li>**重要提示 (能力):** 不同模型版本、视频模式支持范围不同，详见能力地图。</li>
    </ul>
@apiBody {String} [image_tail] 参考图像 - 尾帧控制。用于指定视频的结束帧。格式、大小、分辨率、Base64 要求同 `image` 字段。
    <ul>
        <li>**重要提示 (互斥):** `image` 参数与 `image_tail` 参数至少二选一。`image` + `image_tail` 参数组合、`dynamic_masks`/`static_mask` 参数组合、`camera_control` 参数三者互斥。</li>
        <li>**重要提示 (能力):** 不同模型版本、视频模式支持范围不同，详见能力地图。通常需要 Pro 模式支持。</li>
    </ul>
@apiBody {String} [prompt] 正向文本提示词。描述期望视频的内容或动作。不能超过 2500 个字符。
@apiBody {String} [negative_prompt] 负向文本提示词。描述不希望出现在视频中的内容。不能超过 2500 个字符。（*注意：部分模型或功能（如视频续写）可能不支持此参数*）
@apiBody {Float} [cfg_scale=0.5] 生成视频的自由度。值越大，模型自由度越小，与用户输入的提示词相关性越强。取值范围：[0, 1]。
@apiBody {String} [mode="std"] 生成视频的模式。
    <ul>
        <li>`std`: 标准模式，基础模式，性价比高。</li>
        <li>`pro`: 专家模式，高表现模式，生成视频质量更佳。</li>
    </ul>
    不同模型版本、视频模式支持范围不同，详见能力地图。
@apiBody {String} [static_mask] 静态笔刷涂抹区域。用于指定视频中保持静止的区域。值为 Mask 图片的 URL 或 Base64 编码 (要求同 `image`)。
    <ul>
        <li>图片格式: `.jpg`, `.jpeg`, `.png`。</li>
        <li>**重要提示:** Mask 图片的**长宽比必须与输入图片 `image` 相同**，否则任务失败。</li>
        <li>**重要提示:** `static_mask` 和 `dynamic_masks.mask` (如果使用) 的**分辨率必须一致**，否则任务失败。</li>
        <li>**重要提示 (互斥):** `image` + `image_tail` 参数组合、`dynamic_masks`/`static_mask` 参数组合、`camera_control` 参数三者互斥。</li>
        <li>**重要提示 (能力):** 不同模型版本、视频模式支持范围不同，详见能力地图。通常需要 Pro 模式支持。</li>
    </ul>
@apiBody {Object[]} [dynamic_masks] 动态笔刷配置列表。用于指定图像中特定区域的运动轨迹。最多可配置 6 组。
    <ul>
        <li>**重要提示 (互斥):** `image` + `image_tail` 参数组合、`dynamic_masks`/`static_mask` 参数组合、`camera_control` 参数三者互斥。</li>
        <li>**重要提示 (能力):** 不同模型版本、视频模式支持范围不同，详见能力地图。通常需要 Pro 模式支持。</li>
    </ul>
@apiBody {String} dynamic_masks.mask 动态笔刷涂抹区域。值为 Mask 图片的 URL 或 Base64 编码 (要求同 `image`)。
    <ul>
        <li>图片格式: `.jpg`, `.jpeg`, `.png`。</li>
        <li>**重要提示:** Mask 图片的**长宽比必须与输入图片 `image` 相同**，否则任务失败。</li>
        <li>**重要提示:** `static_mask` (如果使用) 和 `dynamic_masks.mask` 的**分辨率必须一致**，否则任务失败。</li>
    </ul>
@apiBody {Object[]} dynamic_masks.trajectories 运动轨迹坐标序列。
    <ul>
        <li>长度限制: 生成 5s 视频时，轨迹点个数取值范围：[2, 77]。</li>
        <li>坐标系: 以输入图片 `image` 的**左下角**为坐标原点 (0,0) 的像素坐标系。</li>
        <li>说明: 坐标点个数越多轨迹刻画越准确。轨迹方向以传入顺序为指向，依次连接形成运动轨迹。</li>
    </ul>
@apiBody {Integer} dynamic_masks.trajectories.x 轨迹点的横坐标 (X)。
@apiBody {Integer} dynamic_masks.trajectories.y 轨迹点的纵坐标 (Y)。
@apiBody {Object} [camera_control] 控制摄像机运动的配置。如未指定，模型将根据输入智能匹配。
    <ul>
        <li>**重要提示 (互斥):** `image` + `image_tail` 参数组合、`dynamic_masks`/`static_mask` 参数组合、`camera_control` 参数三者互斥。</li>
        <li>**重要提示 (能力):** 不同模型版本、视频模式支持范围不同，详见能力地图。</li>
    </ul>
@apiBody {String} camera_control.type 预定义的运镜类型。
    <ul>
        <li><code>simple</code>: 简单运镜，此类型下需在 `config` 中六选一指定具体运动。</li>
        <li><code>down_back</code>: 镜头下压并后退 (下移拉远)。此类型下 `config` 无需填写。</li>
        <li><code>forward_up</code>: 镜头前进并上仰 (推进上移)。此类型下 `config` 无需填写。</li>
        <li><code>right_turn_forward</code>: 先右旋转后前进 (右旋推进)。此类型下 `config` 无需填写。</li>
        <li><code>left_turn_forward</code>: 先左旋后前进 (左旋推进)。此类型下 `config` 无需填写。</li>
    </ul>
@apiBody {Object} [camera_control.config] 详细运镜参数配置。**当 `camera_control.type` 为 `simple` 时必填**，其他类型时不填。**以下参数必须六选一**，即只有一个参数非零，其余为零。
@apiBody {Float} [camera_control.config.horizontal=0] 水平运镜 (沿 X 轴平移)。取值范围: [-10, 10]。负值向左，正值向右。
@apiBody {Float} [camera_control.config.vertical=0] 垂直运镜 (沿 Y 轴平移)。取值范围: [-10, 10]。负值向下，正值向上。
@apiBody {Float} [camera_control.config.pan=0] 水平摇镜 (绕 Y 轴旋转)。取值范围: [-10, 10]。负值向左转，正值向右转。
@apiBody {Float} [camera_control.config.tilt=0] 垂直摇镜 (绕 X 轴旋转)。取值范围: [-10, 10]。负值向下转，正值向上转。
@apiBody {Float} [camera_control.config.roll=0] 旋转运镜 (绕 Z 轴旋转)。取值范围: [-10, 10]。负值逆时针，正值顺时针。
@apiBody {Float} [camera_control.config.zoom=0] 变焦 (视野远近)。取值范围: [-10, 10]。负值拉近 (视野变小)，正值推远 (视野变大)。
@apiBody {String} [duration="5"] 生成视频时长，单位秒 (s)。
    <ul>
        <li>枚举值: `5`, `10`。</li>
        <li>**重要提示:** 包含尾帧 (`image_tail`) 或运动笔刷 (`dynamic_masks` / `static_mask`) 的请求目前仅支持生成 `5`s 的视频。</li>
    </ul>
@apiBody {String} [callback_url] 任务结果回调通知地址。如果配置，服务端会在任务状态变更时主动向此 URL 发送 POST 请求通知。具体通知消息 Schema 见官方“Callback 协议”文档。
@apiBody {String} [external_task_id] 用户自定义的任务 ID。传入不会覆盖系统生成的 `task_id`，但支持后续通过此 ID 查询任务。**请注意，在您的账户下需要保证此 ID 的唯一性。**

@apiExample {curl} 请求示例 (使用运动笔刷):
 curl --location --request POST 'https://api.klingai.com/v1/videos/image2video' \
 --header 'Authorization: Bearer YOUR_API_KEY' \
 --header 'Content-Type: application/json' \
 --data-raw '{
     "model_name": "kling-v1",
     "mode": "pro",
     "duration": "5",
     "image": "https://h2.inkwai.com/bs2/upload-ylab-stunt/se/ai_portal_queue_mmu_image_upscale_aiweb/3214b798-e1b4-4b00-b7af-72b5b0417420_raw_image_0.jpg",
     "prompt": "宇航员站起身走了",
     "cfg_scale": 0.5,
     "static_mask": "https://h2.inkwai.com/bs2/upload-ylab-stunt/ai_portal/1732888177/cOLNrShrSO/static_mask.png",
     "dynamic_masks": [
       {
         "mask": "https://h2.inkwai.com/bs2/upload-ylab-stunt/ai_portal/1732888130/WU8spl23dA/dynamic_mask_1.png",
         "trajectories": [
           {"x":279,"y":219},{"x":417,"y":65}
         ]
       }
     ]
 }'

@apiSuccessExample {json} 成功响应 (任务已提交):
 HTTP/1.1 200 OK
 {
   "code": 0,
   "message": "Success",
   "request_id": "req_abc123xyz789",
   "data": {
     "task_id": "task_def456uvw123",
     "task_info": {
       "external_task_id": "my_custom_task_001"
     },
     "task_status": "submitted",
     "created_at": 1722769557708,
     "updated_at": 1722769557708
   }
 }

@apiUse KlingErrorResponse

```



## 2. 查询单个图生视频任务
```apidoc
@api {get} /v1/videos/image2video/:id 查询单个任务 (按 Task ID)
@apiVersion 1.0.0
@apiName GetImageToVideoTaskById
@apiGroup ImageToVideo
@apiDescription 根据系统生成的 `task_id` 查询指定图生视频任务的状态和结果。

@apiUse KlingAuth

@apiParam {String} id 任务 ID (Path Parameter)。在 URL 路径中填入要查询的任务 `task_id`。

@apiExample {curl} 请求示例:
 curl --location --request GET 'https://api.klingai.com/v1/videos/image2video/task_def456uvw123' \
 --header 'Authorization: Bearer YOUR_API_KEY' \
 --header 'Content-Type: application/json'

@apiSuccessExample {json} 成功响应 (任务成功):
 HTTP/1.1 200 OK
 {
   "code": 0,
   "message": "Success",
   "request_id": "req_ghi456jkl012",
   "data":{
     "task_id": "task_def456uvw123",
     "task_status": "succeed",
     "task_status_msg": "Task completed successfully",
     "task_info": {
       "external_task_id": "my_custom_task_001"
     },
     "task_result":{
       "videos":[
         {
           "id": "video_ghi789mno456",
           "url": "https://p1.a.kwimgs.com/bs2/upload-ylab-stunt/special-effect/output/HB1_PROD_ai_web_46554461/-2878350957757294165/output.mp4",
           "duration": "5"
         }
       ]
     },
     "created_at": 1722769557708,
     "updated_at": 1722769618345
   }
 }

@apiSuccessExample {json} 成功响应 (任务处理中):
 HTTP/1.1 200 OK
 {
   "code": 0,
   "message": "Success",
   "request_id": "req_pqr789stu345",
   "data":{
     "task_id": "task_def456uvw123",
     "task_status": "processing",
     "task_status_msg": null,
     "task_info": {
       "external_task_id": "my_custom_task_001"
     },
     "task_result": null,
     "created_at": 1722769557708,
     "updated_at": 1722769590123
   }
 }

@apiSuccessExample {json} 成功响应 (任务失败):
 HTTP/1.1 200 OK
 {
   "code": 0,
   "message": "Success",
   "request_id": "req_vwx012yza678",
   "data":{
     "task_id": "task_jkl123pqr789",
     "task_status": "failed",
     "task_status_msg": "Content moderation review failed.", // 失败原因示例
     "task_info": {
       "external_task_id": "my_custom_task_002"
     },
     "task_result": null,
     "created_at": 1722769701234,
     "updated_at": 1722769755678
   }
 }

@apiSuccess {Object} data 任务详情数据。
@apiSuccess {String} data.task_id 任务 ID (系统生成)。
@apiUse KlingTaskStatus
@apiSuccess {String} [data.task_status_msg] 任务状态信息。当任务失败时，通常会展示失败原因 (如触发平台内容风控等)。
@apiSuccess {Object} data.task_info 任务创建时的参数信息。
@apiSuccess {String} [data.task_info.external_task_id] 用户自定义的任务 ID (如果创建时传入)。
@apiSuccess {Object} [data.task_result] 任务结果。仅当 `task_status` 为 `succeed` 时存在。
@apiSuccess {Object[]} data.task_result.videos 生成的视频列表 (通常只有一个)。
@apiSuccess {String} data.task_result.videos.id 生成的视频 ID (全局唯一)。
@apiSuccess {String} data.task_result.videos.url 生成视频的 URL 地址。**请注意：为保障信息安全，生成的图片/视频会在 30 天后被清理，请及时转存。**
@apiSuccess {String} data.task_result.videos.duration 视频总时长，单位秒 (s)。
@apiSuccess {Number} data.created_at 任务创建时间 (Unix 时间戳，单位 ms)。
@apiSuccess {Number} data.updated_at 任务最后更新时间 (Unix 时间戳，单位 ms)。

@apiUse KlingErrorResponse

@apiError (Error 4xx/5xx) TaskNotFound 如果提供的 `task_id` 不存在，可能会返回 404 或其他错误码。

---

@api {get} /v1/videos/image2video?external_task_id=:external_task_id 查询单个任务 (按 External Task ID)
@apiVersion 1.0.0
@apiName GetImageToVideoTaskByExternalId
@apiGroup ImageToVideo
@apiDescription 根据创建时用户自定义的 `external_task_id` 查询指定图生视频任务的状态和结果。
@apiUse KlingAuth

@apiParam {String} external_task_id 用户自定义的任务 ID (Query Parameter)。

@apiExample {curl} 请求示例:
 curl --location --request GET 'https://api.klingai.com/v1/videos/image2video?external_task_id=my_custom_task_001' \
 --header 'Authorization: Bearer YOUR_API_KEY' \
 --header 'Content-Type: application/json'

@apiSuccessExample同上接口 "查询单个任务 (按 Task ID)"

@apiSuccess同上接口 "查询单个任务 (按 Task ID)"

@apiUse KlingErrorResponse

@apiError (Error 4xx/5xx) TaskNotFound 如果提供的 `external_task_id` 不存在或不唯一，可能会返回错误。
---

## 3. 查询图生视频任务列表

@api {get} /v1/videos/image2video 查询任务列表 (分页)
@apiVersion 1.0.0
@apiName ListImageToVideoTasks
@apiGroup ImageToVideo
@apiDescription 查询用户账户下的图生视频任务列表，支持分页。

@apiUse KlingAuth

@apiParam {Number} [pageNum=1] 页码。取值范围：[1, 1000]。
@apiParam {Number} [pageSize=30] 每页数据量。取值范围：[1, 500]。

@apiExample {curl} 请求示例 (查询第1页，每页10条):
 curl --location --request GET 'https://api.klingai.com/v1/videos/image2video?pageNum=1&pageSize=10' \
 --header 'Authorization: Bearer YOUR_API_KEY' \
 --header 'Content-Type: application/json'

@apiSuccessExample {json} 成功响应:
 HTTP/1.1 200 OK
 {
   "code": 0,
   "message": "Success",
   "request_id": "req_mno890pqr123",
   "data":[
     {
       "task_id": "task_def456uvw123",
       "task_status": "succeed",
       "task_status_msg": "Task completed successfully",
       "task_info": {
         "external_task_id": "my_custom_task_001"
       },
       "task_result":{
         "videos":[
           {
             "id": "video_ghi789mno456",
             "url": "https://p1.a.kwimgs.com/bs2/upload-ylab-stunt/.../output.mp4",
             "duration": "5"
           }
         ]
       },
       "created_at": 1722769557708,
       "updated_at": 1722769618345
     },
     {
       "task_id": "task_jkl123pqr789",
       "task_status": "failed",
       "task_status_msg": "Content moderation review failed.",
       "task_info": {
         "external_task_id": "my_custom_task_002"
       },
       "task_result": null,
       "created_at": 1722769701234,
       "updated_at": 1722769755678
     }
     // ... more tasks ...
   ]
 }

@apiSuccess {Object[]} data 任务对象列表。每个对象的结构与 "查询单个任务" 响应中的 `data` 字段相同。
@apiSuccess {String} data.task_id 任务 ID (系统生成)。
@apiUse KlingTaskStatus
@apiSuccess {String} [data.task_status_msg] 任务状态信息。
@apiSuccess {Object} data.task_info 任务创建时的参数信息。
@apiSuccess {String} [data.task_info.external_task_id] 用户自定义的任务 ID。
@apiSuccess {Object} [data.task_result] 任务结果 (如果成功)。
@apiSuccess {Object[]} data.task_result.videos 生成的视频列表。
@apiSuccess {String} data.task_result.videos.id 视频 ID。
@apiSuccess {String} data.task_result.videos.url 视频 URL。
@apiSuccess {String} data.task_result.videos.duration 视频时长。
@apiSuccess {Number} data.created_at 任务创建时间 (Unix 时间戳，单位 ms)。
@apiSuccess {Number} data.updated_at 任务最后更新时间 (Unix 时间戳，单位 ms)。

@apiUse KlingErrorResponse
```


---
```apidoc
# Kling AI API - 图像生成 (Image Generation)

## 概述

本部分 API 提供基于文本提示 (文生图) 或结合参考图像 (图生图) 生成高质量静态图像的能力。

## 模型与能力概览

**不同模型版本支持的图像生成能力和宽高比有所不同，请参考下表或官方最新能力地图选择合适的参数。**

| 功能        | 模型        | 1:1 | 16:9 | 4:3 | 3:2 | 2:3 | 3:4 | 9:16 | 21:9 |
| :---------- | :---------- | :-: | :--: | :-: | :-: | :-: | :-: | :--: | :--: |
| **文生图**  | kling-v1    | ✅  | ✅   | ✅  | ✅  | ✅  | ✅  | ✅   | -    |
|             | kling-v1-5  | ✅  | ✅   | ✅  | ✅  | ✅  | ✅  | ✅   | ✅   |
|             | kling-v2    | ✅  | ✅   | ✅  | ✅  | ✅  | ✅  | ✅   | ✅   |
| **图生图**  |             |     |      |     |     |     |     |      |      |
|             | kling-v1    | ✅  | ✅   | ✅  | ✅  | ✅  | ✅  | ✅   | -    |
|             |  *(通用垫图)* |     |      |     |     |     |     |      |      |
|             | kling-v1-5  | ✅  | ✅   | ✅  | ✅  | ✅  | ✅  | ✅   | ✅   |
|             |  *(角色特征)*|     |      |     |     |     |     |      |      |
|             | kling-v1-5  | ✅  | ✅   | ✅  | ✅  | ✅  | ✅  | ✅   | ✅   |
|             |  *(人物长相)*|     |      |     |     |     |     |      |      |
|             | kling-v2    | -   | -    | -   | -   | -   | -   | -    | -    |
|             |  *(全部能力)*|     |      |     |     |     |     |      |      |

```
---

## 3. 创建图像生成任务
```apidoc
@api {post} /v1/images/generations 创建图像生成任务
@apiVersion 1.0.0
@apiName CreateImageGenerationTask
@apiGroup ImageGeneration
@apiDescription 提交一个基于文本提示（文生图）或结合参考图（图生图）生成图像的任务。

@apiUse KlingAuth

@apiBody {String} [model_name="kling-v1"] 模型名称。 <br/> 枚举值: `kling-v1`, `kling-v1-5`, `kling-v2`。 <br/> *注意：为了保持命名统一，原 `model` 字段变更为 `model_name` 字段。继续使用 `model` 字段等价于 `model_name` 为空时的默认行为 (即调用 `kling-v1` 模型)。*
@apiBody {String} prompt **必须。** 正向文本提示词。描述期望生成的图像内容。不能超过 500 个字符。
@apiBody {String} [negative_prompt] 负向文本提示词。描述不希望出现在图像中的内容。不能超过 200 个字符。**注意：在图生图场景下（即提供了 `image` 参数时），不支持此参数。**
@apiBody {String} [image] 参考图像 (用于图生图)。支持传入图片 Base64 编码或图片 URL（需确保可公开访问）。
    <ul>
        <li>格式: `.jpg`, `.jpeg`, `.png`。</li>
        <li>大小: 不超过 10MB。</li>
        <li>分辨率: 不小于 300x300px。</li>
        <li>宽高比: 在 1:2.5 到 2.5:1 之间。</li>
        <li>**重要提示 (Base64):** 若使用 Base64，请确保**不要**包含任何前缀 (如 `data:image/png;base64,`)，直接提供编码后的字符串。</li>
    </ul>
@apiBody {String} [image_reference] 图片参考类型。指定参考图 `image` 的用途。
    <ul>
        <li>枚举值: `subject` (角色特征参考), `face` (人物长相参考)。</li>
        <li>**条件必填:** 使用 `kling-v1-5` 模型且提供了 `image` 参数时，此参数**必须**填写。</li>
        <li>**模型限制:** 仅 `kling-v1-5` 支持此参数。</li>
        <li>**使用提示:** 使用 `face` 时，上传的 `image` 图片中应仅包含 1 张清晰的人脸。</li>
    </ul>
@apiBody {Float} [image_fidelity=0.5] 图片参考强度。控制生成图像对参考图 `image` 的遵循程度。取值范围：[0, 1]，数值越大参考强度越大。
@apiBody {Float} [human_fidelity=0.45] 面部参考强度。控制生成图像对参考图 `image` 中人物五官的相似度。
    <ul>
        <li>**生效条件:** 仅当 `image_reference` 参数为 `face` 时生效。</li>
        <li>取值范围：[0, 1]，数值越大参考强度越大。</li>
    </ul>
@apiBody {Integer} [n=1] 生成图片数量。取值范围：[1, 9]。
@apiBody {String} [aspect_ratio="16:9"] 生成图片的画面纵横比 (宽:高)。
    <ul>
        <li>枚举值: `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `3:2`, `2:3`, `21:9`。</li>
        <li>**模型限制:** 不同模型版本支持的范围不同，详见能力地图。</li>
    </ul>
@apiBody {String} [callback_url] 任务结果回调通知地址。如果配置，服务端会在任务状态变更时主动向此 URL 发送 POST 请求通知。具体通知消息 Schema 见官方“Callback 协议”文档。

@apiExample {curl} 请求示例 (文生图):
 curl --location --request POST 'https://api.klingai.com/v1/images/generations' \
 --header 'Authorization: Bearer YOUR_API_KEY' \
 --header 'Content-Type: application/json' \
 --data-raw '{
     "model_name": "kling-v1-5",
     "prompt": "一只可爱的猫咪在草地上玩耍，阳光明媚",
     "negative_prompt": "模糊, 低质量, 多余肢体",
     "n": 2,
     "aspect_ratio": "1:1"
 }'

@apiExample {curl} 请求示例 (图生图 - 人物长相参考):
 curl --location --request POST 'https://api.klingai.com/v1/images/generations' \
 --header 'Authorization: Bearer YOUR_API_KEY' \
 --header 'Content-Type: application/json' \
 --data-raw '{
     "model_name": "kling-v1-5",
     "prompt": "一个宇航员站在月球表面，望向远方的地球",
     "image": "https://example.com/path/to/face_image.jpg",
     "image_reference": "face",
     "image_fidelity": 0.6,
     "human_fidelity": 0.7,
     "n": 1,
     "aspect_ratio": "16:9"
 }'


@apiSuccessExample {json} 成功响应 (任务已提交):
 HTTP/1.1 200 OK
 {
   "code": 0,
   "message": "Success",
   "request_id": "req_stu678vwx901",
   "data": {
     "task_id": "task_pqr123abc456",
     "task_status": "submitted",
     "created_at": 1722769557708,
     "updated_at": 1722769557708
   }
 }

@apiUse KlingErrorResponse

```

---

## 4. 查询单个图像生成任务

```apidoc
@api {get} /v1/images/generations/:id 查询单个图像生成任务
@apiVersion 1.0.0
@apiName GetImageGenerationTask
@apiGroup ImageGeneration
@apiDescription 根据任务 ID 查询指定图像生成任务的状态和结果。

@apiUse KlingAuth

@apiParam {String} id **必须。** 图像生成的任务 ID (Path Parameter)。在 URL 路径中填入要查询的任务 `task_id`。

@apiExample {curl} 请求示例:
 curl --location --request GET 'https://api.klingai.com/v1/images/generations/task_pqr123abc456' \
 --header 'Authorization: Bearer YOUR_API_KEY' \
 --header 'Content-Type: application/json'

@apiSuccessExample {json} 成功响应 (任务成功):
 HTTP/1.1 200 OK
 {
   "code": 0,
   "message": "Success",
   "request_id": "req_yza234bcd567",
   "data":{
     "task_id": "task_pqr123abc456",
     "task_status": "succeed",
     "task_status_msg": "Task completed successfully",
     "created_at": 1722769557708,
     "updated_at": 1722769598123,
     "task_result":{
       "images":[
         {
           "index": 0,
           "url": "https://h1.inkwai.com/bs2/upload-ylab-stunt/1fa0ac67d8ce6cd55b50d68b967b3a59.png"
         },
         {
           "index": 1,
           "url": "https://h1.inkwai.com/bs2/upload-ylab-stunt/abcdef1234567890abcdef1234567890.png"
         }
       ]
     }
   }
 }

@apiSuccessExample {json} 成功响应 (任务处理中):
 HTTP/1.1 200 OK
 {
   "code": 0,
   "message": "Success",
   "request_id": "req_efg890hij123",
   "data":{
     "task_id": "task_pqr123abc456",
     "task_status": "processing",
     "task_status_msg": null,
     "created_at": 1722769557708,
     "updated_at": 1722769570456,
     "task_result": null
   }
 }

@apiSuccessExample {json} 成功响应 (任务失败):
 HTTP/1.1 200 OK
 {
   "code": 0,
   "message": "Success",
   "request_id": "req_klm456nop789",
   "data":{
     "task_id": "task_stu789def012",
     "task_status": "failed",
     "task_status_msg": "Input prompt triggered content safety policy.", // 失败原因示例
     "created_at": 1722769801234,
     "updated_at": 1722769825678,
     "task_result": null
   }
 }

@apiSuccess {Object} data 任务详情数据。
@apiSuccess {String} data.task_id 任务 ID (系统生成)。
@apiUse KlingTaskStatus
@apiSuccess {String} [data.task_status_msg] 任务状态信息。当任务失败时，通常会展示失败原因 (如触发平台内容风控等)。
@apiSuccess {Number} data.created_at 任务创建时间 (Unix 时间戳，单位 ms)。
@apiSuccess {Number} data.updated_at 任务最后更新时间 (Unix 时间戳，单位 ms)。
@apiSuccess {Object} [data.task_result] 任务结果。仅当 `task_status` 为 `succeed` 时存在。
@apiSuccess {Object[]} data.task_result.images 生成的图像列表。
@apiSuccess {Integer} data.task_result.images.index 图片编号，从 0 开始，对应请求参数 `n` 生成的数量。
@apiSuccess {String} data.task_result.images.url 生成图像的 URL 地址。**请注意：为保障信息安全，生成的图片/视频会在 30 天后被清理，请及时转存。**

@apiUse KlingErrorResponse

@apiError (Error 4xx/5xx) TaskNotFound 如果提供的 `task_id` 不存在，可能会返回 404 或其他错误码。

```