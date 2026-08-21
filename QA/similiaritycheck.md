import unittest
import requests
import json
import logging
from rapidfuzz import fuzz

# Set up logging for beautiful and clear output during test runs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestSimilarityRemoteAPI(unittest.TestCase):
    """
    Test suite for validating the similarity deduplication filtering 
    directly against the live remote deployment server.
    """
    BASE_URL = "[http://52.76.118.186:8203/homepage/recommendation](http://52.76.118.186:8203/homepage/recommendation)"
    
    def setUp(self):
        # Default query parameters based on the user's sample curl
        self.default_params = {
            "client_id": "test-1235",
            "ip_address": "1.2.3.4",
            "num_recommendation": 8,
            "page_mode": "homepage",
            "localized": "false",
            "lambda_param": 0.7,
            "similarity_threshold": 60
        }
        self.headers = {
            "accept": "application/json"
        }

    def test_remote_recommendation_basic(self):
        """
        Verify the remote endpoint responds successfully with HTTP 200
        using the user's exact sample curl parameters and returns a valid structure.
        """
        logger.info("Executing basic remote recommendation test with similarity_threshold=60...")
        try:
            response = requests.get(
                self.BASE_URL,
                params=self.default_params,
                headers=self.headers,
                timeout=10
            )
            
            logger.info(f"Response Code: {response.status_code}")
            logger.info(f"Latency: {response.elapsed.total_seconds()}s")
            
            self.assertEqual(response.status_code, 200, f"Expected 200 OK, got {response.status_code}. Response: {response.text}")
            
            res_json = response.json()
            self.assertIn("status", res_json, "Response missing 'status'")
            self.assertIn("data", res_json, "Response missing 'data'")
            
            data = res_json.get("data", {})
            self.assertIn("model_code", data, "Response 'data' missing 'model_code'")
            self.assertIn("recommended_article", data, "Response 'data' missing 'recommended_article'")
            
            articles = data.get("recommended_article", [])
            logger.info(f"Successfully retrieved {len(articles)} articles. Model code: {data.get('model_code')}")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"Remote API request failed: {e}")

    def test_remote_recommendation_threshold_comparison(self):
        """
        Test the remote endpoint with different similarity threshold values (e.g. 0, 60, 95)
        to verify that the similarity filtering works as expected and does not crash the server.
        """
        thresholds_to_test = [0, 50, 75, 95]
        
        for threshold in thresholds_to_test:
            logger.info(f"Testing remote API with similarity_threshold={threshold}...")
            params = self.default_params.copy()
            params["similarity_threshold"] = threshold
            
            try:
                response = requests.get(
                    self.BASE_URL,
                    params=params,
                    headers=self.headers,
                    timeout=10
                )
                
                self.assertEqual(
                    response.status_code, 200, 
                    f"Remote API failed for threshold {threshold} with status {response.status_code}"
                )
                
                res_json = response.json()
                data = res_json.get("data", {})
                articles = data.get("recommended_article", [])
                
                logger.info(
                    f"Threshold {threshold:2d} -> Status: {response.status_code} | "
                    f"Articles Returned: {len(articles)} | Model Code: {data.get('model_code')}"
                )
                
            except requests.exceptions.RequestException as e:
                self.fail(f"Remote API request failed for threshold {threshold}: {e}")

    def test_remote_recommendation_missing_optional_params(self):
        """
        Verify that the remote endpoint behaves robustly when some optional parameters
        are omitted or default values are utilized by the remote server.
        """
        logger.info("Testing remote API with minimized query parameters...")
        minimal_params = {
            "client_id": "test-minimal-1235",
            "page_mode": "homepage"
        }
        
        try:
            response = requests.get(
                self.BASE_URL,
                params=minimal_params,
                headers=self.headers,
                timeout=10
            )
            
            logger.info(f"Minimal Params Response Code: {response.status_code}")
            self.assertEqual(
                response.status_code, 200, 
                f"Minimal params request failed with status {response.status_code}. Response: {response.text}"
            )
            
            res_json = response.json()
            data = res_json.get("data", {})
            logger.info(f"Minimal params returned model: {data.get('model_code')} with {len(data.get('recommended_article', []))} articles.")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"Remote API request failed for minimal params: {e}")

    def test_remote_recommendation_fuzzing_50_clients(self):
        """
        Scenario: Test 50 distinct client requests (test-1 to test-50)
        asking for 20 recommendations with similarity_threshold=60.
        Performs a full pairwise similarity analysis within each client's response
        to verify if the DeduplicationManager correctly filtered out duplicate titles,
        and logs the similarity scores to prove why articles did/didn't filter.
        """
        logger.info("Starting live 50-client integration test scenario...")
        
        num_clients = 50
        num_recommendation = 20
        similarity_threshold = 60.0
        
        total_duplicates_found = 0
        total_articles_received = 0
        all_max_scores = []
        all_avg_scores = []
        
        for i in range(1, num_clients + 1):
            client_id = f"test-{i}"
            params = {
                "client_id": client_id,
                "ip_address": "1.2.3.4",
                "num_recommendation": num_recommendation,
                "page_mode": "homepage",
                "localized": "false",
                "lambda_param": 0.7,
                "similarity_threshold": similarity_threshold
            }
            
            try:
                response = requests.get(
                    self.BASE_URL,
                    params=params,
                    headers=self.headers,
                    timeout=10
                )
                
                self.assertEqual(
                    response.status_code, 200, 
                    f"Remote request failed for client {client_id} with status {response.status_code}"
                )
                
                res_json = response.json()
                data = res_json.get("data", {})
                articles = data.get("recommended_article", [])
                
                total_articles_received += len(articles)
                
                # Pairwise similarity check within the single feed response
                feed_duplicates = []
                feed_scores = []
                seen_titles = []
                
                for art in articles:
                    title = str(art.get("title", "")).lower().strip()
                    if not title:
                        continue
                    
                    for seen in seen_titles:
                        score = fuzz.ratio(title, seen)
                        feed_scores.append(score)
                        if score >= similarity_threshold:
                            feed_duplicates.append((title, seen, score))
                            
                    seen_titles.append(title)
                
                max_score = max(feed_scores) if feed_scores else 0.0
                avg_score = sum(feed_scores) / len(feed_scores) if feed_scores else 0.0
                
                all_max_scores.append(max_score)
                all_avg_scores.append(avg_score)
                total_duplicates_found += len(feed_duplicates)
                
                # Report duplicates if any found
                if feed_duplicates:
                    logger.warning(
                        f"[{client_id}] Found {len(feed_duplicates)} duplicates in returned feed of {len(articles)} articles! "
                        f"Max similarity score: {max_score:.1f}%"
                    )
                    for t1, t2, sc in feed_duplicates:
                        logger.warning(f"  -> Duplicate Pair ({sc:.1f}% similarity):\n     * Title 1: {t1}\n     * Title 2: {t2}")
                else:
                    logger.info(
                        f"[{client_id}] Checked {len(articles)} articles. No duplicates found. "
                        f"Max internal similarity: {max_score:.1f}%, Avg: {avg_score:.1f}%"
                    )
                    
            except requests.exceptions.RequestException as e:
                self.fail(f"Remote request failed for client {client_id}: {e}")
                
        # Gorgeous summary report printout
        logger.info("=" * 80)
        logger.info("50-CLIENT SIMILARITY INTEGRATION TEST SUMMARY REPORT")
        logger.info("=" * 80)
        logger.info(f"Total Requests Evaluated: {num_clients}")
        logger.info(f"Total Articles Received: {total_articles_received}")
        logger.info(f"Target Similarity Threshold: {similarity_threshold}%")
        logger.info(f"Total Duplicate Pairs Slipped Through (>= {similarity_threshold}%): {total_duplicates_found}")
        
        global_max = max(all_max_scores) if all_max_scores else 0.0
        global_avg = sum(all_avg_scores) / len(all_avg_scores) if all_avg_scores else 0.0
        logger.info(f"Global Max Pairwise Similarity Score: {global_max:.1f}%")
        logger.info(f"Global Average Pairwise Similarity Score: {global_avg:.1f}%")
        logger.info("=" * 80)
        
        # Verify that the deduplicator did its job: zero duplicates should slip through!
        self.assertEqual(
            total_duplicates_found, 0, 
            f"Expected 0 duplicates to slip through, but found {total_duplicates_found} duplicate pairs!"
        )

if __name__ == "__main__":
    unittest.main()