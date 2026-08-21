## 2. Header Trending Tags (`page_mode=popular`)

This endpoint returns dynamically aggregated trending tags based on the most popular articles over the last 23 hours. It uses advanced fuzzy matching to deduplicate similar tags (e.g., merging "jokowi" and "joko widodo") and actively filters out banned NSFW content.

> [!NOTE]
> For trending tags, the mode is designated as **`popular`**, not `latest`.

### Endpoint
`GET /api/v3/header/tag`

### Query Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `client_id` | `string` | **Yes** | Unique identifier for the user/device. |
| `page_mode` | `string` | **Yes** | Must be set exactly to `popular` for trending tags. |
| `num_recommendation` | `integer` | Optional | Number of tags to return (default: `20`, max: `20`). |
| `source_url` | `string` | Optional | Web domain. Should be omitted or left blank for Mobile App requests. |
| `similarity_score` | `float` | Optional | Fuzzy match threshold for tag deduplication (default: `60.0`). |

### cURL Test Script (Staging)

```bash
# Test Popular/Trending Tags
curl -s -H "X-API-Key: c2c32d37d870c155cfc9ee62d03db1dd38c980cde42f8cf20113719bf23a9e36" \
"https://stg-reco-app.tribundata.com/api/v3/header/tag?client_id=test-1235&page_mode=popular&num_recommendation=5"
```

### Automation & Continuous Testing

Jika Anda ingin menjalankan script automation test (`test_trending_tag_api.py`) secara berulang (misalnya 10x berturut-turut) untuk memantau masalah yang bersifat *intermiten* / tidak konsisten (seperti duplikasi gambar akibat fluktuasi trending data), gunakan Bash Loop berikut dari *root directory*:

```bash
for i in {1..10}; do PYTHONPATH=. uv run python header_tag/test_trending_tag_api.py; echo "--- Run $i Completed ---"; sleep 1; done
```

### Expected Response (Mobile App)

```json
{
  "status": true,
  "data": [
    {
      "tag_title": "piala-presiden-2026",
      "tag_url": "https://www.tribunnews.com/tag/piala-presiden-2026",
      "photo_url": "https://asset-2.tribunnews.com/..."
    },
    {
      "tag_title": "jokowi",
      "tag_url": "https://www.tribunnews.com/tag/jokowi",
      "photo_url": "https://asset-2.tribunnews.com/..."
    }
  ]
}
```

## Resilience Testing (QA)

Both of these endpoints are equipped with an ultra-fast, passive Redis fallback mechanism. If the core database (MongoDB/Qdrant) goes down or times out, the backend will automatically intercept the failure and return cached default articles/tags.

**How to verify:**
The fallback is completely transparent, but you can identify a fallback payload by inspecting the `type` field in the JSON response:
- **Normal state:** `"type": "latest_news"` or `"type": "popular"`
- **Fallback state:** `"type": "default-value"`
