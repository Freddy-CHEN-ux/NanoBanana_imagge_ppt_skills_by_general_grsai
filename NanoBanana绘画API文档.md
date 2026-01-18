
---

### **Grsai Nano Banana 绘画 API 文档**

这是一个用于生成图片的AI绘画接口，提供多种模型和灵活的响应方式。该API也兼容部分Gemini官方接口格式。

#### **1. API 概述**

*   **功能**: 提交文本提示词（Prompt）或参考图，生成高质量图片。
*   **核心特点**:
    *   支持多种绘画模型。
    *   支持三种结果获取方式：**流式响应 (Stream)**、**Webhook回调 (Callback)** 和 **轮询 (Polling)**。
    *   兼容Google Gemini的接口格式，方便迁移。

---

#### **2. 基础信息**

**主机地址 (Host)**
*   **海外节点**: `https://grsaiapi.com`
*   **国内直连节点**: `https://grsai.dakka.com.cn`

**认证方式 (Authentication)**
通过在请求头中设置 `Authorization` 字段进行 `Bearer` 认证。
```json
{
  "Authorization": "Bearer YOUR_API_KEY"
}
```

---

#### **3. 接口详情**

##### **3.1 核心绘画接口**

*   **路径**: `/v1/draw/nano-banana`
*   **请求方式**: `POST`
*   **请求头 (Headers)**:
    *   `Content-Type`: `application/json`
    *   `Authorization`: `Bearer YOUR_API_KEY`

**请求体参数 (Request Body - JSON)**

| 参数名 | 类型 | 是否必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `model` | string | **是** | **模型名称。** 可选值：`nano-banana-fast`, `nano-banana`, `nano-banana-pro`, `nano-banana-pro-vt`, `nano-banana-pro-cl`, `nano-banana-pro-vip`, `nano-banana-pro-4k-vip`。 |
| `prompt` | string | **是** | **提示词。** 描述你想要生成的图像内容，例如："一只可爱的猫咪在草地上玩耍"。 |
| `urls` | array | 否 | **参考图数组。** 元素可以是图片的URL或Base64编码字符串。用于图生图。 |
| `aspectRatio` | string | 否 | **图像宽高比。** 默认为 `auto`。可选值：`1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`, `5:4`, `4:5`, `21:9`。 |
| `imageSize` | string | 否 | **图像分辨率。** 默认为 `1K`。可选值：`1K`, `2K`, `4K`。<br>**注意**：此参数仅部分模型支持，且有特定限制：<br>- `nano-banana-pro` / `pro-vt` / `pro-cl`：支持 `1K`, `2K`, `4K`。<br>- `nano-banana-pro-vip`: 仅支持 `1K`, `2K`。<br>- `nano-banana-pro-4k-vip`: 仅支持 `4K`。 |
| `webHook` | string | 否 | **回调或轮询控制。**<br>1.  **Webhook模式**: 提供一个URL，例如 `https://example.com/callback`。服务器会将进度和结果通过POST请求发送到此URL。<br>2.  **轮询模式**: 传入 `"-1"`。接口会立即返回一个任务ID，你需要自行轮询结果接口（文档未提供结果接口，推测需另外查询）。 |
| `shutProgress` | boolean | 否 | **关闭进度回调。** 默认为 `false`。如果设为 `true`，则只在任务完成时发送最终结果，中间的进度更新将被省略。建议与`webHook`配合使用。 |

##### **3.2 Gemini 兼容格式**

API也支持类似Gemini的调用方式，只需替换基础地址和模型名称。

*   **URL 示例**: `https://grsai.dakka.com.cn/v1beta/models/nano-banana-fast:streamGenerateContent`

---

#### **4. 响应处理方式**

根据 `webHook` 参数的不同，有三种获取结果的方式：

1.  **流式响应 (Stream - 默认)**
    *   **触发条件**: 不提供 `webHook` 参数。
    *   **行为**: 接口会保持HTTP连接，并持续以数据流的形式推送包含进度和最终结果的JSON对象。

2.  **Webhook 回调 (Callback)**
    *   **触发条件**: `webHook` 参数为一个有效的URL。
    *   **行为**:
        1.  调用接口后，会**立即返回**一个包含任务ID的JSON对象（见下文`4.1`）。
        2.  任务的进度和最终结果会以 `POST` 请求的方式发送到你提供的 `webHook` URL上，请求体格式为最终响应参数（见下文`4.2`）。

3.  **轮询获取 (Polling)**
    *   **触发条件**: `webHook` 参数值为 `"-1"`。
    *   **行为**: 调用接口后，会**立即返回**一个包含任务ID的JSON对象（见下文`4.1`），你需要使用这个ID去轮询另一个专门获取结果的接口。

---

#### **5. 数据结构说明**

##### **5.1 Webhook/轮询模式的初始响应**

当使用Webhook或轮询模式时，绘画接口会立即返回以下结构，告知任务已创建。

**示例:**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "id": "f44bcf50-f2d0-4c26-a467-26f2014a771b"
  }
}
```

| 参数 | 类型 | 描述 |
| :--- | :--- | :--- |
| `code` | number | 状态码，`0` 表示成功。 |
| `msg` | string | 状态信息，例如 "success"。 |
| `data.id` | string | **任务ID**。用于关联后续的Webhook回调或用于轮询。 |

##### **5.2 最终/流式响应参数**

这是流式响应中的数据，也是Webhook回调时`POST`请求的Body。

**示例:**
```json
{
  "id": "f44bcf50-f2d0-4c26-a467-26f2014a771b",
  "results": [
    {
      "url": "https://example.com/generated-image.jpg",
      "content": "这是一只可爱的猫咪在草地上玩耍"
    }
  ],
  "progress": 100,
  "status": "succeeded",
  "failure_reason": "",
  "error": ""
}
```

| 参数 | 类型 | 描述 |
| :--- | :--- | :--- |
| `id` | string | **任务ID**，与初始响应中的ID对应。 |
| `results` | array | **结果数组。** 每个对象包含：<br>- `url`: 生成的图片URL (注意：**有效期为2小时**)。<br>- `content`: 对生成内容的描述或确认。 |
| `progress` | number | **任务进度**，范围从 0 到 100。 |
| `status` | string | **任务状态。**<br>- `"running"`: 进行中<br>- `"succeeded"`: 成功<br>- `"failed"`: 失败 |
| `failure_reason`| string | **失败原因分类。**<br>- `"output_moderation"`: 输出内容违规。<br>- `"input_moderation"`: 输入内容违规。<br>- `"error"`: 其他错误。 |
| `error` | string | **详细的失败信息**，例如 "Invalid input parameters"。 |

**重要提示**: 当 `failure_reason` 为 `"error"` 时，可以尝试重新提交任务，可能有助于解决临时性问题。