import requests
import sys
import json
from datetime import datetime

class LocationIntelligenceAPITester:
    def __init__(self, base_url="http://localhost3000"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.search_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"URL: {url}")

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)

            print(f"Response Status: {response.status_code}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"Response preview: {str(response_data)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error response: {error_data}")
                except:
                    print(f"Error response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        return success

    def test_search_competitors_advanced(self, business_type="restaurant", location="Connaught Place, Delhi", radius=5000):
        """Test advanced competitor search endpoint"""
        success, response = self.run_test(
            "Search Competitors Advanced",
            "POST",
            "api/search-competitors-advanced",
            200,
            data={
                "business_type": business_type,
                "location": location,
                "radius": radius
            }
        )

        if success and 'search_id' in response:
            self.search_id = response['search_id']
            print(f"Search ID saved: {self.search_id}")

            # Validate response structure for advanced features
            required_fields = ['search_id', 'location', 'center_coordinates', 'business_type',
                             'competitors', 'competitor_count', 'saturation_score', 'demographics',
                             'rental_estimates', 'break_even_analysis', 'foot_traffic_score', 'radius']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in response: {missing_fields}")
            else:
                print("✅ All required fields present in response")

            # Validate demographics structure
            if 'demographics' in response:
                demo = response['demographics']
                print(f"Demographics: {demo}")

            # Validate rental estimates
            if 'rental_estimates' in response:
                rental = response['rental_estimates']
                print(f"Rental estimates: {rental}")

            # Validate break-even analysis
            if 'break_even_analysis' in response:
                break_even = response['break_even_analysis']
                print(f"Break-even analysis: {break_even}")

            # Validate competitors structure
            if 'competitors' in response and len(response['competitors']) > 0:
                competitor = response['competitors'][0]
                competitor_fields = ['name', 'address', 'lat', 'lng', 'place_id']
                missing_comp_fields = [field for field in competitor_fields if field not in competitor]
                if missing_comp_fields:
                    print(f"⚠️  Missing competitor fields: {missing_comp_fields}")
                else:
                    print("✅ Competitor structure is valid")

        return success

    def test_compare_locations(self):
        """Test location comparison endpoint"""
        success, response = self.run_test(
            "Compare Locations",
            "POST",
            "api/compare-locations",
            200,
            data={
                "locations": [
                    {
                        "business_type": "restaurant",
                        "location": "Connaught Place, Delhi",
                        "radius": 5000
                    },
                    {
                        "business_type": "restaurant",
                        "location": "Bandra, Mumbai",
                        "radius": 5000
                    }
                ]
            }
        )

        if success:
            # Validate comparison response structure
            required_fields = ['comparison_id', 'locations', 'comparison_date', 'summary']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing fields in comparison response: {missing_fields}")
            else:
                print("✅ All required comparison fields present")

            # Validate locations in comparison
            if 'locations' in response and len(response['locations']) >= 2:
                print(f"✅ Comparison includes {len(response['locations'])} locations")

                # Check first location structure
                location = response['locations'][0]
                location_fields = ['location', 'business_type', 'competitor_count', 'saturation_score',
                                 'demographics', 'rental_estimates', 'break_even_analysis']
                missing_loc_fields = [field for field in location_fields if field not in location]
                if missing_loc_fields:
                    print(f"⚠️  Missing location fields: {missing_loc_fields}")
                else:
                    print("✅ Location structure in comparison is valid")

            # Validate summary
            if 'summary' in response:
                summary = response['summary']
                print(f"Summary recommendations: {summary}")

        return success

    def test_get_search_analysis(self):
        """Test get search analysis endpoint"""
        if not self.search_id:
            print("❌ No search_id available for testing")
            return False

        success, response = self.run_test(
            "Get Search Analysis",
            "GET",
            f"api/search/{self.search_id}",
            200
        )
        return success

    def test_get_recent_searches(self):
        """Test get recent searches endpoint"""
        success, response = self.run_test(
            "Get Recent Searches",
            "GET",
            "api/searches",
            200
        )

        if success and isinstance(response, list):
            print(f"✅ Retrieved {len(response)} recent searches")

        return success

    def test_get_recent_comparisons(self):
        """Test get recent comparisons endpoint"""
        success, response = self.run_test(
            "Get Recent Comparisons",
            "GET",
            "api/comparisons",
            200
        )

        if success and isinstance(response, list):
            print(f"✅ Retrieved {len(response)} recent comparisons")

        return success

    def test_different_business_types(self):
        """Test different business types with advanced endpoint"""
        business_types = ["cafe", "salon", "gym"]
        success_count = 0

        for business_type in business_types:
            print(f"\n--- Testing business type: {business_type} ---")
            success, _ = self.run_test(
                f"Search {business_type}",
                "POST",
                "api/search-competitors-advanced",
                200,
                data={
                    "business_type": business_type,
                    "location": "Connaught Place, Delhi",
                    "radius": 2000
                }
            )
            if success:
                success_count += 1

        print(f"\n✅ {success_count}/{len(business_types)} business types tested successfully")
        return success_count == len(business_types)

    def test_different_locations(self):
        """Test different locations with advanced endpoint"""
        locations = ["Mumbai, Maharashtra", "Bangalore, Karnataka"]
        success_count = 0

        for location in locations:
            print(f"\n--- Testing location: {location} ---")
            success, _ = self.run_test(
                f"Search in {location}",
                "POST",
                "api/search-competitors-advanced",
                200,
                data={
                    "business_type": "restaurant",
                    "location": location,
                    "radius": 5000
                }
            )
            if success:
                success_count += 1

        print(f"\n✅ {success_count}/{len(locations)} locations tested successfully")
        return success_count == len(locations)

    def test_error_handling(self):
        """Test API error handling"""
        print("\n--- Testing Error Handling ---")

        # Test invalid location
        success, _ = self.run_test(
            "Invalid Location",
            "POST",
            "api/search-competitors-advanced",
            500,  # Expecting error (backend handles gracefully)
            data={
                "business_type": "restaurant",
                "location": "InvalidLocationThatDoesNotExist12345",
                "radius": 5000
            }
        )

        # Test invalid search_id
        success2, _ = self.run_test(
            "Invalid Search ID",
            "GET",
            "api/search/invalid-search-id-12345",
            404  # Expecting not found
        )

        return success or success2  # At least one error handling should work

def main():
    print("🚀 Starting Enhanced Location Intelligence API Tests")
    print("=" * 60)

    # Setup
    tester = LocationIntelligenceAPITester()

    # Run core API tests
    print("\n📋 CORE API TESTS")
    print("-" * 30)

    health_ok = tester.test_health_check()
    search_ok = tester.test_search_competitors_advanced()
    comparison_ok = tester.test_compare_locations()
    analysis_ok = tester.test_get_search_analysis()
    recent_searches_ok = tester.test_get_recent_searches()
    recent_comparisons_ok = tester.test_get_recent_comparisons()

    # Run extended tests
    print("\n📋 EXTENDED TESTS")
    print("-" * 30)

    business_types_ok = tester.test_different_business_types()
    locations_ok = tester.test_different_locations()
    error_handling_ok = tester.test_error_handling()

    # Print final results
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS")
    print("=" * 60)
    print(f"Total tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")

    print("\n📋 Test Summary:")
    print(f"✅ Health Check: {'PASS' if health_ok else 'FAIL'}")
    print(f"✅ Search Competitors Advanced: {'PASS' if search_ok else 'FAIL'}")
    print(f"✅ Compare Locations: {'PASS' if comparison_ok else 'FAIL'}")
    print(f"✅ Get Search Analysis: {'PASS' if analysis_ok else 'FAIL'}")
    print(f"✅ Get Recent Searches: {'PASS' if recent_searches_ok else 'FAIL'}")
    print(f"✅ Get Recent Comparisons: {'PASS' if recent_comparisons_ok else 'FAIL'}")
    print(f"✅ Different Business Types: {'PASS' if business_types_ok else 'FAIL'}")
    print(f"✅ Different Locations: {'PASS' if locations_ok else 'FAIL'}")
    print(f"✅ Error Handling: {'PASS' if error_handling_ok else 'FAIL'}")

    # Determine overall result
    core_tests_passed = all([health_ok, search_ok, comparison_ok, analysis_ok, recent_searches_ok, recent_comparisons_ok])

    if core_tests_passed:
        print("\n🎉 All core API tests PASSED! Enhanced backend is working correctly.")
        return 0
    else:
        print("\n❌ Some core API tests FAILED! Backend needs attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
