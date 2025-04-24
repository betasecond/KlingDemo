@api {get} / General Information
@apiVersion 1.0.0
@apiName GeneralInfo
@apiGroup General
@apiDescription 本文档提供调用 Kling AI API 所需的通用信息，包括 API 域名、身份验证机制和通用错误代码。

---

# **1. API 域名**

所有 Kling AI API 的请求都应发送到以下基础 URL：

`https://api.klingai.com`

---

# **2. 接口鉴权 (Authentication)**

Kling AI API 使用基于 JWT (JSON Web Token, RFC 7519) 的 Bearer Token 进行身份验证。

## **步骤 1: 获取 AccessKey 和 SecretKey**

您需要首先从 Kling AI 平台获取您的 `AccessKey` (ak) 和 `SecretKey` (sk)。请妥善保管您的 SecretKey，不要泄露。

## **步骤 2: 生成 API Token (JWT)**

每次请求 API 时，您需要使用您的 `AccessKey` 和 `SecretKey` 动态生成一个有时效性的 JWT。

**JWT 结构:**

*   **Header:** 指定签名算法 (HS256) 和 Token 类型 (JWT)。
    ```json
    {
      "alg": "HS256",
      "typ": "JWT"
    }
    ```
*   **Payload:** 包含声明信息，如签发者、过期时间等。
    *   `iss`: (Issuer) 签发者，应填写您的 `AccessKey` (ak)。
    *   `exp`: (Expiration Time) 过期时间戳 (Unix Timestamp, 秒)。建议设置为当前时间戳 + 有效期 (例如 +1800 秒表示 30 分钟有效期)。Token 在此时间之后将失效。
    *   `nbf`: (Not Before) 生效时间戳 (Unix Timestamp, 秒)。Token 在此时间之前无效。通常可以设置为当前时间戳或略早几秒 (例如 -5 秒) 以防止时钟不同步问题。
*   **Signature:** 使用 Header 中指定的算法 (HS256) 和您的 `SecretKey` (sk) 对 `base64UrlEncode(header) + "." + base64UrlEncode(payload)` 进行签名。

**生成示例 (Python):**

@apiExample {python} 生成 JWT Token 示例
 import time
 import jwt

 # --- 请替换为您的真实 Key ---
 ak = "YOUR_ACCESS_KEY"  # 填写您的 AccessKey
 sk = "YOUR_SECRET_KEY"  # 填写您的 SecretKey
 # --------------------------

 def encode_jwt_token(ak, sk):
     headers = {
         "alg": "HS256",
         "typ": "JWT"
     }
     # 设置 Payload
     current_time = int(time.time())
     payload = {
         "iss": ak,
         # 有效期设置为 30 分钟 (1800 秒)
         "exp": current_time + 1800,
         # 生效时间设置为当前时间前 5 秒，以容忍轻微时钟误差
         "nbf": current_time - 5
     }
     # 使用 SecretKey 对 Payload 进行签名
     token = jwt.encode(payload, sk, algorithm="HS256", headers=headers)
     return token

 # 生成 API Token
 api_token = encode_jwt_token(ak, sk)
 print(f"Generated API Token: {api_token}")

## **步骤 3: 在请求头中包含 Authorization**

将步骤 2 生成的 `api_token` 添加到您每个 API 请求的 HTTP Header 中。

**格式:**

`Authorization: Bearer <api_token>`

**注意:** `Bearer` 和 `<api_token>` 之间必须有一个空格。

@apiHeader {String} Authorization Bearer Token 认证。格式: `Bearer <生成的JWT Token>`。

@apiHeaderExample {Header} Authorization Header 示例:
 Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJZ...

---

# **3. 错误码 (Error Codes)**

API 请求可能返回不同的 HTTP 状态码和业务错误码。

| HTTP Status | Business Code (业务码) | Definition (定义) | Explanation (解释)                 | Suggested Solution (建议解决方案)                                  |
| :---------- | :--------------------- | :---------------- | :--------------------------------- | :----------------------------------------------------------------- |
| **200**     | 0                      | 请求成功          | -                                  | -                                                                  |
| **401**     | 1000                   | 身份验证失败      | 身份验证失败                       | 检查 `Authorization` Header 是否正确，Token 是否有效。             |
| 401         | 1001                   | 身份验证失败      | `Authorization` Header 为空        | 在 Request Header 中填写正确的 `Authorization`。                     |
| 401         | 1002                   | 身份验证失败      | `Authorization` Header 值非法    | 检查 `Bearer` 格式和 Token 本身是否正确。                          |
| 401         | 1003                   | 身份验证失败      | Token 未到有效时间 (`nbf`)       | 检查 Token 的 `nbf` 声明，等待生效或重新生成 Token。               |
| 401         | 1004                   | 身份验证失败      | Token 已失效 (`exp`)             | 检查 Token 的 `exp` 声明，重新生成 Token。                         |
| **429**     | 1100                   | 账户异常          | 账户异常                           | 检查账户配置信息或联系客服。                                       |
| 429         | 1101                   | 账户异常          | 账户欠费 (后付费场景)              | 进行账户充值，确保余额充足。                                       |
| 429         | 1102                   | 账户异常          | 资源包已用完/已过期 (预付费场景)   | 购买额外的资源包，或开通后付费服务（如有）。                       |
| **403**     | 1103                   | 账户异常          | 请求的资源无权限 (如接口/模型)    | 检查账户权限，确认是否有权访问该接口或模型。                       |
| **400**     | 1200                   | 请求参数非法      | 请求参数非法                       | 检查请求参数是否符合 API 文档要求。                                |
| 400         | 1201                   | 请求参数非法      | 参数非法 (如 key 写错或 value 非法) | 参考响应体中的 `message` 字段，修改请求参数。                      |
| **404**     | 1202                   | 请求参数非法      | 请求的 HTTP Method 无效            | 查看接口文档，使用正确的 HTTP 请求方法 (GET, POST 等)。            |
| 404         | 1203                   | 请求参数非法      | 请求的资源不存在 (如模型/任务 ID)   | 参考响应体中的 `message` 字段，检查 URL 路径或参数是否正确。         |
| **400**     | 1300                   | 触发策略          | 触发平台策略                       | 检查请求内容或行为是否符合平台规定。                               |
| 400         | 1301                   | 触发策略          | 触发平台的内容安全策略             | 检查输入内容 (如 `prompt`)，修改后重新发起请求。                   |
| **429**     | 1302                   | 触发策略          | API 请求过快，超过平台速率限制     | 降低请求频率、使用指数退避策略稍后重试，或联系客服增加限额。         |
| 429         | 1303                   | 触发策略          | 并发或 QPS 超出预付费资源包限制    | 降低请求频率、稍后重试，或升级资源包/联系客服增加限额。            |
| 429         | 1304                   | 触发策略          | 触发平台的 IP 白名单策略           | 确认请求来源 IP 是否在允许的白名单内，或联系客服配置白名单。         |
| **500**     | 5000                   | 内部错误          | 服务器内部错误                     | 稍后重试。如果问题持续存在，请记录 `request_id` 并联系客服。         |
| **503**     | 5001                   | 内部错误          | 服务器暂时不可用 (通常是在维护)    | 稍后重试。关注官方维护公告。                                       |
| **504**     | 5002                   | 内部错误          | 服务器内部超时 (通常是发生积压)    | 稍后重试。如果问题持续存在，请记录 `request_id` 并联系客服。         |

@apiErrorStructure KlingErrorResponse