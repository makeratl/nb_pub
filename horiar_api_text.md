# Horiar API Documentation

## General Information

- Base URL: `https://api.horiar.com/enterprise`
- Authorization: All endpoints require an API key using the `Authorization` header.
  - Format: `Authorization: Bearer <your_api_key>`

## Status Queries

### Endpoint

- URL: `/query/<job_id>`
- Method: `GET`

### Example Outputs

- Output when your request is still on the queue:
  ```json
  {
      "job_id": ...,
      "message": "Your request has been queued"
  }
  ```

- Output when your request is completed:
  ```json
  {
      "JSON object specialized related to the query type"
  }
  ```

## Text to Image

Text to Image is a technology that automatically transforms a description or text you provide into an image. You describe the scene or idea in your mind with words, and the system generates a visual representation of your description.

### 1. Create Text to Image

#### Endpoint

- URL: `/text-to-image`
- Method: `POST`

#### Headers

- `Content-Type: application/json`
- `Authorization: Bearer <api_key>`

#### Request Body

```json
{
  "prompt": "Description of the image you want to create",
  "model_type": "Model type (optional)",
  "resolution": "Resolution (optional)"
}
```

- `prompt` (required): Description of the image to be generated.
- `resolution` (optional): The type of model to use. The default value is `1024x1024 | 1:1 (Square)`. Available options:
  - `"1024x1024 | 1:1 (Square)"`
  - `"1344x768 | 16:9 (Horizontal)"`
  - `"768x1344 | 9:16 (Vertical)"`
  - `"832x1216 | 2:3 (Classic Portrait)"`
  - `"1536x640 | 21:9 (Epic Ultrawide)"`
  - `"640x1536 | 9:21 (Ultra tall)"`
  - `"1472x704 | 19:9 (Cinematic Ultrawide)"`
  - `"1152x896 | 4:3 (Classic Landscape)"`
- `model_type` (optional): The resolution of the image. The default value is `normal`. Available options:
  - `"normal"`
  - `"ultra detailed"`

#### Response

Upon a successful request, the server returns a JSON containing the URL of the generated image and relevant details.

Example Response:
```json
{
    "job_id": ...,
    "message": "Your request has been queued"
}
```

### 2. Retrieve Text to Image Requests

#### Endpoint

- URL: `/text-to-image`
- Method: `GET`

#### Headers

- `Authorization: Bearer <api_key>`

#### Description

Retrieves all "text to image" requests made by the customer.

#### Response

Example Response:
```json
[
    {
        "created_at": "2024-10-12T23:05:25.513000",
        "id": "670b00b5af08fe5d39858750",
        "image": "<Image_URL>",
        "model_type": "normal",
        "prompt": "<your prompt>",
        "resolution": "1344x768 | 16:9 (Horizontal)",
        "seed": "495467664915050"
    },
    {
        "created_at": "2024-10-13T09:26:12.522000",
        "id": "670b9234fca0e312ce7fe1db",
        "image": "<Image_URL>",
        "model_type": "normal",
        "prompt": "<your prompt>",
        "resolution": "1344x768 | 16:9 (Horizontal)",
        "seed": "221051862432490"
    }
]
```

### 3. Retrieve a Specific Text to Image Request

#### Endpoint

- URL: `/text-to-image/<request_id>`
- Method: `GET`

#### Headers

- `Authorization: Bearer <api_key>`

#### Description

Retrieves the "text to image" request with the specified `request_id`.

#### Response

Example Response:
```json
{
    "created_at": "2024-10-12T23:05:25.513000",
    "id": "670b00b5af08fe5d39858750",
    "image": "<Image_URL>",
    "model_type": "normal",
    "prompt": "<your prompt>",
    "resolution": "1344x768 | 16:9 (Horizontal)",
    "seed": "495467664915050"
}
```

## Upscale Enhance

Upscale is a technology that transforms a low-resolution image into a higher resolution and sharper image. It enhances blurry or pixel-dense visuals into clearer, more detailed versions without losing quality.

### 1. Create Upscale Enhance

#### Endpoint

- URL: `/upscale-enhance`
- Method: `POST`

#### Headers

- `Content-Type: multipart/form-data`
- `Authorization: Bearer <api_key>`

#### Request Body

- `image` (file, optional): The low-resolution image file.
- `link` (optional): The image reference to use in link format.
- `base64` (optional): The image to use in base64 format.

#### Example cURL Request

For Image:
```bash
curl -X POST "https://api.horiar.com/enterprise/upscale-enhance" \
  -H "Authorization: your_api_key" \
  -F "image=@/path/to/your/image.png"
```

For link:
```bash
curl -X POST "https://api.horiar.com/enterprise/upscale-enhance" \
  -H "Authorization: your_api_key" \
  -d "link=https://example.com/path/to/image.jpg"
```

For base64:
```bash
curl -X POST "https://api.horiar.com/enterprise/upscale-enhance" \
  -H "Authorization: your_api_key" \
  -d "base64=$(base64 /path/to/your/image.jpg)"
```

#### Response

Example Response:
```json
{
    "job_id": ...,
    "message": "Your request has been queued"
}
```

### 2. Retrieve Upscale Enhance Requests

#### Endpoint

- URL: `/upscale-enhance`
- Method: `GET`

#### Headers

- `Authorization: Bearer <api_key>`

#### Description

Retrieves all "upscale enhance" requests made by the customer.

#### Response

Example Response:
```json
[
    {
        "created_at": "2024-10-12T23:19:13.348000",
        "id": "670b03f16d402bdaa64a888b",
        "image": "<image_URL>",
        "low_res_url": "<image_URL>"
    }
]
```

### 3. Retrieve a Specific Upscale Enhance Request

#### Endpoint

- URL: `/upscale-enhance/<request_id>`
- Method: `GET`

#### Headers

- `Authorization: Bearer <api_key>`

#### Description

Retrieves the "upscale enhance" request with the specified `request_id`.

#### Response

Example Response:
```json
{
    "created_at": "2024-10-12T23:19:13.348000",
    "id": "670b03f16d402bdaa64a888b",
    "image": "<image_URL>",
    "low_res_url": "<image_URL>"
}
```

## Text to Video

### 1. Text-to-Video Creation

#### Description

This endpoint allows users to generate a video from a given text prompt.

#### Endpoint

- URL: `POST /text-to-video`
- Method: `POST`

#### Headers

- `Authorization: Bearer <api_key>`

#### Request Body

```json
{
  "prompt": "A futuristic city skyline at sunset, with flying cars and tall buildings."
}
```

#### Response

```json
{
    "job_id": ...,
    "message": "Your request has been queued"
}
```

### 2. Retrieve Text-to-Video Requests

#### Description

This endpoint lists all text-to-video requests made by the user.

#### Request

- URL: `GET /text-to-video`

#### Headers

- `Authorization: Bearer <api_key>`

#### Response

```json
[
  {
    "id": "sync-abcdef12-1234-5678-9012-abcdef123456-e1",
    "prompt": "<your prompt>",
    "output_url": "<video_URL>",
    "status": "COMPLETED",
    "created_at": "2024-10-24T15:45:10Z"
  },
  {
    "id": "sync-1234abcd-5678-90ef-abcdef123456-e1",
    "prompt": "<your prompt>",
    "output_url": "<video_URL>",
    "status": "COMPLETED",
    "created_at": "2024-10-24T14:30:05Z"
  }
]
```

### 3. Retrieve a specific video request

#### Explanation

This endpoint retrieves a specific text-to-video request from the user.

#### Request

- URL: `GET /text-to-video/<request_id>`

#### Headers

- `Authorization: Bearer <api_key>`

#### Response

```json
[
  {
    "id": "sync-abcdef12-1234-5678-9012-abcdef123456-e1",
    "prompt": "<your prompt>",
    "output_url": "<video_URL>",
    "status": "COMPLETED",
    "created_at": "2024-10-24T15:45:10Z"
  }
]
```

## Image to Video

### 1. Image-to-Video Creation

#### Endpoint

- URL: `/image-to-video`
- Method: `POST`

#### Headers

- `Content-Type: multipart/form-data`
- `Authorization: Bearer <api_key>`

#### Request Body

- `image` (file, optional): The image input to refer from.
- `link` (optional): The image input to refer from as a link.
- `base64` (optional): The image input to refer from in base64 form.
- `prompt` (text, mandatory): Prompt for converting reference image to video.

#### Example cURL Requests

For image:
```bash
curl -X POST "https://api.horiar.com/enterprise/image-to-video" \
  -H "Authorization: your_api_key" \
  -F "image=@/path/to/your/image.png" \
  -d "prompt=<your_prompt>"
```

For link:
```bash
curl -X POST "https://api.horiar.com/enterprise/image-to-video" \
  -H "Authorization: your_api_key" \
  -d "link=https://example.com/path/to/image.jpg" \
  -d "prompt=<your_prompt>"
```

For base64:
```bash
curl -X POST "https://api.horiar.com/enterprise/image-to-video" \
  -H "Authorization: your_api_key" \
  -d "base64=$(base64 /path/to/your/image.jpg)" \
  -d "prompt=<your_prompt>"
```

#### Response

```json
{
    "job_id": ...,
    "message": "Your request has been queued"
}
```

### 2. Retrieve Image-to-Video Requests

#### Endpoint

- URL: `/image-to-video`
- Method: `GET`

#### Headers

- `Authorization: Bearer <api_key>`

#### Explanation

Allows user to retrieve all image-to-video requests.

#### Response

Example:
```json
[
    {
        "created_at": "2024-10-12T23:19:13.348000",
        "id": "670b03f16d402bdaa64a888b",
        "ref_image": "<image_URL>",
        "prompt": "<your_prompt>",
        "video": "<video_URL>"
    }
]
```

## Video to Video

⚠ This feature is under development and not available yet.

### 1. Video-to-Video Creation

#### Endpoint

- URL: `/video-to-video`
- Method: `POST`

#### Headers

- `Content-Type: multipart/form-data`
- `Authorization: Bearer <api_key>`

#### Request Body

- `video` (file, required): The video to be used as a reference.

#### Example cURL Request

```bash
curl -X POST "https://api.horiar.com/enterprise/video-to-video" \
  -H "Authorization: your_api_key" \
  -F "video=@/path/to/your/video.mp4"
```

#### Response

```json
{
    "job_id": ...,
    "message": "Your request has been queued"
}
```

### 2. Retrieve Video-to-Video Requests

#### Endpoint

- URL: `/video-to-video`
- Method: `GET`

#### Headers

- `Authorization: Bearer <api_key>`

#### Response

```json
[
    {
        "created_at": "2024-10-12T23:19:13.348000",
        "id": "670b03f16d402bdaa64a888b",
        "ref_video": "<video_URL>",
        "video": "<video_URL>"
    }
]
```

## Error Responses

- 400 Bad Request: Missing or invalid parameters.
  Example:
  ```json
  {
    "message": "Missing required fields"
  }
  ```

- 401 Unauthorized: Invalid or missing API key.
  Example:
  ```json
  {
    "message": "API key is missing"
  }
  ```

- 404 Not Found: Request or resource not found.
  Example:
  ```json
  {
    "message": "Request not found"
  }
  ```

- 500 Internal Server Error: Server error.
  Example:
  ```json
  {
    "message": "An unexpected error occurred"
  }
  ```

## Important Notes

- Authorization: The `Authorization` header must be correctly configured for all requests. The value will be provided via email.
- Data Types: Parameters such as `request_id` should reference actual ID values stored in the database.
- File Uploads: For endpoints such as `/upscale-enhance`, `/image-to-video`, and `/video-to-video`, the file format must be `multipart/form-data`.
- Optional Parameters: Parameters like `model_type` and `resolution` are optional. If not provided, default values will be used.
- 🚨 On Upscale and Image To Video tools, data upload in the form of `multipart/form-data` should not exceed 10MB.
- 🚨 Our video generation features are still under development. The input and output formats are subject to change, so please pay close attention to release notes and any email updates sent to you.

## Additional Information

- `delayTime` and `executionTime`: Provide information on the processing time of requests.
- `output`: Contains the URL of the generated video and the status of the operation.
- `workerId`: Identifies the server processing the request.

## Developer Notes

⚠ If you receive an error with a different format than the ones mentioned above, please report it to developer@horiar.com. We will provide a solution as quickly as possible and notify you.
