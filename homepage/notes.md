# API Testing Guide: Latest Feed & Popular Tags

This guide provides test scripts and payload documentation for the QA and Mobile Development teams to integrate and test the newly added recommendation features.

---

## 1. Homepage Latest Feed (`page_mode=latest`)

This endpoint returns a chronologically sorted feed of the latest articles, strictly filtered by the user's geolocation (city/province) with an intelligent fallback if no local articles are found. It includes visual deduplication to ensure articles with the exact same cover image are not displayed together.

### Endpoint
`GET /api/v3/homepage/recommendation`

### Query Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `client_id` | `string` | **Yes** | Unique identifier for the user/device. |
| `page_mode` | `string` | **Yes** | Must be set exactly to `latest`. |
| `localized` | `boolean\|string` | Optional | `true`, `"true"`, or `"local"`: Applies strict geo-filtering based on the user's IP. `false`, `"false"`, or `"global"`: Returns the global feed. `"mix"`: Returns a blended feed of local and global articles. |
| `num_recommendation` | `integer` | Optional | Number of articles to return (default: `20`, max: `20`). |
| `ip_address` | `string` | Optional | Explicit IP to test geo-filtering. If omitted, the backend natively resolves it from headers. |
| `source_url` | `string` | Optional | Web domain. Should be omitted or left blank for Mobile App requests. |

### cURL Test Script (Staging)

```bash
# Test Localized Latest Feed
curl -s -H "X-API-Key: c2c32d37d870c155cfc9ee62d03db1dd38c980cde42f8cf20113719bf23a9e36" \
"https://stg-reco-app.tribundata.com/api/v3/homepage/recommendation?client_id=test-1235&page_mode=latest&localized=true&num_recommendation=10"
```

### Expected Response (Mobile App)

```json
{
  "status": true,
  "data": [
    {
      "site": "tribunnews",
      "publish_date": "2026-07-21T09:14:27+07:00",
      "id": "7856850",
      "title": "KKP Buka 1000 Kuota Magang Nasional 2026 dan Diberi Uang Saku",
      "subtitle": "Energi",
      "section_title": "Bisnis",
      "alias": "bisnis/972609/aneka-promo-indomaret-hari-ini-dan-besok-ada-personal-care-deals-posh-men-rp-13900",
      "url": "https://www.tribunnews.com/...",
      "foto": "https://asset-2.tribunnews.com/...",
      "score": 16.109,
      "region": "Jawa",
      "city": "Jakarta",
      "province": "DKI Jakarta",
      "type": "latest_news"
    }
  ],
  "execution_time": 45.43,
  "user_location": "Jakarta",
}
```
## Resilience Testing (QA)

Both of these endpoints are equipped with an ultra-fast, passive Redis fallback mechanism. If the core database (MongoDB/Qdrant) goes down or times out, the backend will automatically intercept the failure and return cached default articles/tags.

**How to verify:**
The fallback is completely transparent, but you can identify a fallback payload by inspecting the `type` field in the JSON response:
- **Normal state:** `"type": "latest_news"` or `"type": "popular"`
- **Fallback state:** `"type": "default-value"`
---