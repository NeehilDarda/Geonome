from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import requests
import json
import httpx
import math
from datetime import datetime
import uuid
import motor.motor_asyncio
from pymongo import MongoClient

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = MongoClient(MONGO_URL)
db = client['location_intelligence']
searches_collection = db['searches']
comparisons_collection = db['comparisons']

# Create geospatial index for advanced queries
searches_collection.create_index([("center_location", "2dsphere")])

# API Keys
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', 'AIzaSyABOBWi8rAH8sdr2AYCfuVtg0ZxrdjrBR8')
GOOGLE_PLACES_BASE_URL = "https://maps.googleapis.com/maps/api/place"

class LocationSearchRequest(BaseModel):
    business_type: str
    location: str
    radius: int = 5000

class ComparisonRequest(BaseModel):
    locations: List[LocationSearchRequest]

class CompetitorInfo(BaseModel):
    name: str
    address: str
    rating: Optional[float] = None
    price_level: Optional[str] = None
    lat: float
    lng: float
    place_id: str

class DemographicsData(BaseModel):
    population_density: Optional[float] = None
    estimated_population: Optional[int] = None
    urban_rural_index: Optional[float] = None
    economic_activity_score: Optional[float] = None
    air_quality_index: Optional[int] = None
    air_quality_level: Optional[str] = None
    # Enhanced US Census data
    median_household_income: Optional[float] = None
    median_age: Optional[float] = None
    education_bachelor_plus: Optional[float] = None
    average_spending_retail: Optional[float] = None
    consumer_spending_index: Optional[float] = None
    foot_traffic_multiplier: Optional[float] = None
    # New detailed zip code metrics
    zip_code: Optional[str] = None
    per_capita_income: Optional[float] = None
    household_income_distribution: Optional[dict] = None
    poverty_rate: Optional[float] = None
    unemployment_rate: Optional[float] = None
    average_home_value: Optional[float] = None
    rent_burden_percentage: Optional[float] = None
    commute_time_minutes: Optional[float] = None
    spending_categories: Optional[dict] = None  # Food, retail, entertainment, etc.

class RentalEstimate(BaseModel):
    estimated_rent_per_sqft: Optional[float] = None
    rental_index: Optional[str] = None
    market_tier: Optional[str] = None

class BreakEvenAnalysis(BaseModel):
    estimated_monthly_revenue: Optional[float] = None
    monthly_costs: Optional[float] = None
    break_even_months: Optional[float] = None
    roi_percentage: Optional[float] = None
    profit_projection_year1: Optional[float] = None

class AdvancedLocationAnalysis(BaseModel):
    search_id: str
    business_type: str
    location: str
    competitors: List[CompetitorInfo]
    competitor_count: int
    saturation_score: float
    demographics: DemographicsData
    rental_estimates: RentalEstimate
    break_even_analysis: BreakEvenAnalysis
    foot_traffic_score: Optional[float] = None
    analysis_date: datetime

def geocode_location(location: str):
    """Convert address to coordinates using Google Geocoding API"""
    try:
        geocoding_url = f"https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': location,
            'key': GOOGLE_API_KEY
        }
        
        response = requests.get(geocoding_url, params=params)
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            location_data = data['results'][0]['geometry']['location']
            return location_data['lat'], location_data['lng']
        else:
            print(f"Geocoding failed: {data.get('status')} - {data.get('error_message', 'Unknown error')}")
    except Exception as e:
        print(f"Geocoding API error: {e}")
    
    # Fallback to known city coordinates if API fails
    city_coords = {
        "delhi": (28.6139, 77.2090),
        "mumbai": (19.0760, 72.8777),
        "pune": (18.5204, 73.8567),
        "bangalore": (12.9716, 77.5946),
        "chennai": (13.0827, 80.2707),
        "kolkata": (22.5726, 88.3639),
        "hyderabad": (17.3850, 78.4867),
        "london": (51.5074, -0.1278),
        "new york": (40.7128, -74.0060),
        "paris": (48.8566, 2.3522),
        "connaught place": (28.6304, 77.2177),
        "bandra": (19.0596, 72.8295)
    }
    
    # Try to match location to known cities
    location_lower = location.lower()
    for city, coords in city_coords.items():
        if city in location_lower:
            print(f"Using fallback coordinates for: {location}")
            return coords
    
    # Default to Mumbai if no match found
    print(f"Using default coordinates (Mumbai) for: {location}")
    return city_coords["mumbai"]

async def get_air_quality_data(lat: float, lng: float):
    """Get Air Quality Index data using Google AQI API"""
    try:
        aqi_url = "https://airquality.googleapis.com/v1/currentConditions:lookup"
        headers = {
            'Content-Type': 'application/json',
        }
        params = {
            'key': GOOGLE_API_KEY
        }
        
        data = {
            "location": {
                "latitude": lat,
                "longitude": lng
            }
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(aqi_url, json=data, headers=headers, params=params)
            
            if response.status_code == 200:
                aqi_data = response.json()
                
                # Extract AQI information
                if 'indexes' in aqi_data and len(aqi_data['indexes']) > 0:
                    universal_aqi = None
                    for index in aqi_data['indexes']:
                        if index.get('code') == 'uaqi':  # Universal AQI
                            universal_aqi = index
                            break
                    
                    if universal_aqi:
                        aqi_value = universal_aqi.get('aqi', 0)
                        category = universal_aqi.get('category', 'Unknown')
                        
                        # Convert category to readable format
                        aqi_levels = {
                            'EXCELLENT': 'Excellent',
                            'GOOD': 'Good', 
                            'MODERATE': 'Moderate',
                            'UNHEALTHY_FOR_SENSITIVE_GROUPS': 'Unhealthy for Sensitive Groups',
                            'UNHEALTHY': 'Unhealthy',
                            'VERY_UNHEALTHY': 'Very Unhealthy',
                            'HAZARDOUS': 'Hazardous'
                        }
                        
                        return {
                            'aqi': aqi_value,
                            'level': aqi_levels.get(category, category)
                        }
                        
    except Exception as e:
        print(f"AQI API error: {e}")
    
async def get_us_census_data(lat: float, lng: float):
    """Get comprehensive US Census demographics and economic data by zip code"""
    try:
        # US Census API endpoints (free, no key required for basic data)
        census_base = "https://api.census.gov/data"
        
        # First, get the FIPS code AND ZIP code for the location
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Get FIPS codes and ZIP code
            fips_response = await client.get(
                f"https://geo.fcc.gov/api/census/area",
                params={
                    'lat': lat,
                    'lon': lng,
                    'format': 'json'
                }
            )
            
            zip_code = None
            if fips_response.status_code == 200:
                fips_data = fips_response.json()
                if 'results' in fips_data and len(fips_data['results']) > 0:
                    result = fips_data['results'][0]
                    state_fips = result.get('state_fips')
                    county_fips = result.get('county_fips')
                    
                    # Get ZIP code from reverse geocoding
                    try:
                        zip_response = await client.get(
                            f"https://maps.googleapis.com/maps/api/geocode/json",
                            params={
                                'latlng': f"{lat},{lng}",
                                'key': GOOGLE_API_KEY,
                                'result_type': 'postal_code'
                            }
                        )
                        if zip_response.status_code == 200:
                            zip_data = zip_response.json()
                            if zip_data.get('status') == 'OK' and zip_data.get('results'):
                                for component in zip_data['results'][0]['address_components']:
                                    if 'postal_code' in component['types']:
                                        zip_code = component['long_name']
                                        break
                    except Exception as e:
                        print(f"ZIP code lookup error: {e}")
                    
                    if state_fips and county_fips:
                        # Enhanced ACS variables for detailed demographics
                        acs_variables = [
                            'B01003_001E',  # Total population
                            'B19013_001E',  # Median household income
                            'B01002_001E',  # Median age
                            'B15003_022E',  # Bachelor's degree
                            'B15003_001E',  # Total education
                            'B08303_001E',  # Commute time
                            'B19301_001E',  # Per capita income
                            'B25077_001E',  # Median home value
                            'B25064_001E',  # Median gross rent
                            'B17001_002E',  # Poverty count
                            'B23025_005E',  # Unemployed
                            'B23025_002E',  # Labor force
                            'B19001_002E',  # Income under $10k
                            'B19001_003E',  # Income $10k-15k
                            'B19001_004E',  # Income $15k-20k
                            'B19001_005E',  # Income $20k-25k
                            'B19001_006E',  # Income $25k-30k
                            'B19001_007E',  # Income $30k-35k
                            'B19001_008E',  # Income $35k-40k
                            'B19001_009E',  # Income $40k-45k
                            'B19001_010E',  # Income $45k-50k
                            'B19001_011E',  # Income $50k-60k
                            'B19001_012E',  # Income $60k-75k
                            'B19001_013E',  # Income $75k-100k
                            'B19001_014E',  # Income $100k-125k
                            'B19001_015E',  # Income $125k-150k
                            'B19001_016E',  # Income $150k-200k
                            'B19001_017E',  # Income $200k+
                        ]
                        
                        acs_params = {
                            'get': ','.join(acs_variables),
                            'for': f'county:{county_fips}',
                            'in': f'state:{state_fips}'
                        }
                        
                        # Try ZIP Code Tabulation Area (ZCTA) data if we have ZIP code
                        zip_data_detailed = None
                        if zip_code:
                            try:
                                # ZCTA data for more precise ZIP code level data
                                zcta_params = {
                                    'get': 'B01003_001E,B19013_001E,B19301_001E,B25077_001E,B25064_001E',
                                    'for': f'zip code tabulation area:{zip_code}'
                                }
                                zcta_response = await client.get(
                                    f"{census_base}/2022/acs/acs5",
                                    params=zcta_params
                                )
                                if zcta_response.status_code == 200:
                                    zcta_data = zcta_response.json()
                                    if len(zcta_data) > 1:
                                        zip_data_detailed = zcta_data[1]
                            except Exception as e:
                                print(f"ZCTA lookup error: {e}")
                        
                        # ACS 5-year estimates (county level)
                        acs_response = await client.get(
                            f"{census_base}/2022/acs/acs5",
                            params=acs_params
                        )
                        
                        if acs_response.status_code == 200:
                            acs_data = acs_response.json()
                            if len(acs_data) > 1:  # Header + data row
                                data_row = acs_data[1]
                                
                                # Parse comprehensive Census data
                                def safe_float(val): 
                                    try:
                                        return float(val) if val and str(val).lower() not in ['null', '-', 'none', ''] else None
                                    except (ValueError, TypeError):
                                        return None
                                        
                                def safe_int(val):
                                    try: 
                                        return int(val) if val and str(val).lower() not in ['null', '-', 'none', ''] else None
                                    except (ValueError, TypeError):
                                        return None
                                
                                # Use ZIP code data if available, otherwise county data
                                if zip_data_detailed:
                                    total_pop = safe_int(zip_data_detailed[0])
                                    median_income = safe_float(zip_data_detailed[1])
                                    per_capita = safe_float(zip_data_detailed[2])
                                    home_value = safe_float(zip_data_detailed[3])
                                    median_rent = safe_float(zip_data_detailed[4])
                                else:
                                    total_pop = safe_int(data_row[0])
                                    median_income = safe_float(data_row[1])
                                    per_capita = safe_float(data_row[6])
                                    home_value = safe_float(data_row[7])
                                    median_rent = safe_float(data_row[8])
                                
                                # County-specific data
                                median_age = safe_float(data_row[2])
                                bachelor_count = safe_int(data_row[3]) or 0
                                total_education = safe_int(data_row[4]) or 1
                                commute_time = safe_float(data_row[5])
                                poverty_count = safe_int(data_row[9]) or 0
                                unemployed = safe_int(data_row[10]) or 0
                                labor_force = safe_int(data_row[11]) or 1
                                
                                # Calculate derived metrics
                                education_pct = (bachelor_count / total_education * 100) if total_education > 0 else 0
                                poverty_rate = (poverty_count / total_pop * 100) if total_pop and total_pop > 0 else 0
                                unemployment_rate = (unemployed / labor_force * 100) if labor_force > 0 else 0
                                
                                # Income distribution
                                income_brackets = {}
                                bracket_labels = [
                                    "under_10k", "10k_15k", "15k_20k", "20k_25k", "25k_30k",
                                    "30k_35k", "35k_40k", "40k_45k", "45k_50k", "50k_60k",
                                    "60k_75k", "75k_100k", "100k_125k", "125k_150k", "150k_200k", "200k_plus"
                                ]
                                
                                for i, label in enumerate(bracket_labels, 12):
                                    if i < len(data_row):
                                        count = safe_int(data_row[i]) or 0
                                        pct = (count / total_pop * 100) if total_pop and total_pop > 0 else 0
                                        income_brackets[label] = {"count": count, "percentage": round(pct, 1)}
                                
                                # Consumer spending estimates based on BLS Consumer Expenditure Survey
                                spending_categories = {}
                                if median_income:
                                    # BLS average spending percentages by income level
                                    annual_spending = median_income * 0.72  # Average 72% of income spent
                                    
                                    spending_categories = {
                                        "housing": round(annual_spending * 0.33, 2),  # 33% on housing
                                        "food": round(annual_spending * 0.13, 2),    # 13% on food
                                        "transportation": round(annual_spending * 0.16, 2),  # 16% on transport
                                        "healthcare": round(annual_spending * 0.08, 2),     # 8% on healthcare
                                        "entertainment": round(annual_spending * 0.05, 2),  # 5% on entertainment
                                        "retail_shopping": round(annual_spending * 0.12, 2), # 12% on retail
                                        "other": round(annual_spending * 0.13, 2)    # 13% other
                                    }
                                    
                                    # Monthly retail spending
                                    monthly_retail_spending = spending_categories["retail_shopping"] / 12
                                    
                                    # Consumer spending index (normalized to 100 = national average ~$60k)
                                    spending_index = (median_income / 60000) * 100
                                else:
                                    monthly_retail_spending = None
                                    spending_index = None
                                
                                # Enhanced foot traffic multiplier
                                foot_traffic_mult = 1.0
                                if median_income:
                                    if median_income > 80000:
                                        foot_traffic_mult += 0.4  # High income
                                    elif median_income > 60000:
                                        foot_traffic_mult += 0.25  # Above average income
                                    elif median_income < 35000:
                                        foot_traffic_mult -= 0.2   # Below average income
                                
                                if education_pct > 50:
                                    foot_traffic_mult += 0.3  # Highly educated area
                                elif education_pct > 30:
                                    foot_traffic_mult += 0.15  # Well educated
                                
                                if median_age and 25 <= median_age <= 45:
                                    foot_traffic_mult += 0.25  # Prime spending age
                                
                                if unemployment_rate and unemployment_rate < 5:
                                    foot_traffic_mult += 0.1  # Low unemployment
                                
                                # Rent burden (if rent > 30% of income, it's considered high burden)
                                rent_burden = None
                                if median_rent and median_income:
                                    annual_rent = median_rent * 12
                                    rent_burden = (annual_rent / median_income * 100) if median_income > 0 else None
                                
                                return {
                                    'zip_code': zip_code,
                                    'population': total_pop,
                                    'median_income': median_income,
                                    'per_capita_income': per_capita,
                                    'median_age': median_age,
                                    'education_bachelor_pct': education_pct,
                                    'monthly_retail_spending': monthly_retail_spending,
                                    'spending_index': spending_index,
                                    'foot_traffic_multiplier': foot_traffic_mult,
                                    'commute_time': commute_time,
                                    'poverty_rate': poverty_rate,
                                    'unemployment_rate': unemployment_rate,
                                    'home_value': home_value,
                                    'median_rent': median_rent,
                                    'rent_burden': rent_burden,
                                    'income_distribution': income_brackets,
                                    'spending_categories': spending_categories
                                }
                        
                        print("Successfully retrieved comprehensive US Census data")
                        
    except Exception as e:
        print(f"Enhanced US Census API error: {e}")
    
    return None

def search_competitors(lat: float, lng: float, business_type: str, radius: int):
    """Search for competitors using Google Places API (New) - WORKING VERSION"""
    search_url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': GOOGLE_API_KEY,
        'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.location,places.rating,places.priceLevel,places.id'
    }
    
    # Map business types to Google Places types (updated for new API)
    type_mapping = {
        'restaurant': ['restaurant'],
        'cafe': ['cafe'],
        'coffee': ['cafe'],
        'salon': ['beauty_salon'],
        'gym': ['gym'],
        'fitness': ['gym'],
        'store': ['store'],
        'shop': ['store'],
        'retail': ['store'],
        'default': ['restaurant']
    }
    
    # Get appropriate types based on business_type
    included_types = type_mapping.get(business_type.lower(), type_mapping['default'])
    
    data = {
        "includedTypes": included_types,
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lng
                },
                "radius": radius
            }
        }
    }
    
    try:
        response = requests.post(search_url, headers=headers, json=data)
        result = response.json()
        
        print(f"Places API response status: {response.status_code}")
        
        competitors = []
        if response.status_code == 200 and 'places' in result:
            for place in result['places']:
                # Handle new API response format
                display_name = place.get('displayName', {})
                name = display_name.get('text', 'Unknown') if isinstance(display_name, dict) else str(display_name)
                
                location = place.get('location', {})
                lat_val = location.get('latitude', 0) if isinstance(location, dict) else 0
                lng_val = location.get('longitude', 0) if isinstance(location, dict) else 0
                
                competitor = CompetitorInfo(
                    name=name,
                    address=place.get('formattedAddress', ''),
                    rating=place.get('rating'),
                    price_level=str(place.get('priceLevel', '')) if place.get('priceLevel') else None,
                    lat=lat_val,
                    lng=lng_val,
                    place_id=place.get('id', '')
                )
                competitors.append(competitor)
            
            print(f"✅ Successfully found {len(competitors)} competitors")
        elif response.status_code != 200:
            print(f"❌ API Error {response.status_code}: {result}")
        else:
            print("ℹ️ No competitors found in this area")
        
        return competitors
        
    except Exception as e:
        print(f"❌ Places API error: {e}")
        return []

async def get_population_demographics(lat: float, lng: float, radius: int = 5000):
    """Get comprehensive demographics using US Census API, WorldPop API, and Air Quality data"""
    try:
        # Get Air Quality data
        aqi_data = await get_air_quality_data(lat, lng)
        aqi_value = aqi_data['aqi'] if aqi_data else None
        aqi_level = aqi_data['level'] if aqi_data else None
        
        # Get US Census data (most accurate for US locations)
        census_data = await get_us_census_data(lat, lng)
        
        if census_data:
            # Use US Census data for US locations
            population = census_data.get('population', 0)
            area_km2 = (radius / 1000) ** 2 * math.pi
            density = population / area_km2 if area_km2 > 0 and population else 0
            
            # Enhanced economic activity based on income and education
            income = census_data.get('median_income') or 50000
            education = census_data.get('education_bachelor_pct') or 25
            economic_score = min(((income / 50000) * 0.6 + (education / 50) * 0.4) * 100, 100)
            
            return DemographicsData(
                population_density=round(density, 2) if density else None,
                estimated_population=population if population else None,
                urban_rural_index=min(density / 1000, 1.0) if density else None,
                economic_activity_score=round(economic_score, 1) if economic_score else None,
                air_quality_index=aqi_value,
                air_quality_level=aqi_level,
                # Enhanced US Census data with safe defaults
                zip_code=census_data.get('zip_code'),
                median_household_income=census_data.get('median_income'),
                per_capita_income=census_data.get('per_capita_income'),
                median_age=census_data.get('median_age'),
                education_bachelor_plus=census_data.get('education_bachelor_pct'),
                average_spending_retail=census_data.get('monthly_retail_spending'),
                consumer_spending_index=census_data.get('spending_index'),
                foot_traffic_multiplier=census_data.get('foot_traffic_multiplier'),
                household_income_distribution=census_data.get('income_distribution'),
                poverty_rate=census_data.get('poverty_rate'),
                unemployment_rate=census_data.get('unemployment_rate'),
                average_home_value=census_data.get('home_value'),
                rent_burden_percentage=census_data.get('rent_burden'),
                commute_time_minutes=census_data.get('commute_time'),
                spending_categories=census_data.get('spending_categories')
            )
        
        # Fallback to WorldPop API for international locations
        radius_deg = radius / 111000  # Approximately 111km per degree
        
        # Simple circular polygon approximation
        circle_points = []
        for i in range(36):  # 36 points for circle
            angle = i * 10 * math.pi / 180
            point_lat = lat + radius_deg * math.cos(angle)
            point_lng = lng + radius_deg * math.sin(angle)
            circle_points.append([point_lng, point_lat])
        
        circle_points.append(circle_points[0])  # Close the polygon
        
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [circle_points]
                }
            }]
        }
        
        # Try WorldPop API for international locations
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                worldpop_response = await client.post(
                    "https://api.worldpop.org/v1/services/stats",
                    params={
                        "dataset": "wpgppop",
                        "year": "2020",
                        "geojson": json.dumps(geojson)
                    }
                )
                
                if worldpop_response.status_code == 200:
                    worldpop_data = worldpop_response.json()
                    if 'data' in worldpop_data:
                        population = worldpop_data['data'].get('total_population', 0)
                        area_km2 = (radius / 1000) ** 2 * math.pi
                        density = population / area_km2 if area_km2 > 0 else 0
                        
                        return DemographicsData(
                            population_density=round(density, 2),
                            estimated_population=int(population),
                            urban_rural_index=min(density / 1000, 1.0),
                            economic_activity_score=min(density / 500, 1.0) * 100,
                            air_quality_index=aqi_value,
                            air_quality_level=aqi_level
                        )
            except Exception as e:
                print(f"WorldPop API error: {e}")
        
        # Final fallback: Estimate based on location with enhanced demo data
        estimated_population = estimate_population_fallback(lat, lng, radius)
        area_km2 = (radius / 1000) ** 2 * math.pi
        density = estimated_population / area_km2 if area_km2 > 0 else 0
        
        # Add realistic sample data based on location type for demonstration
        sample_data = get_sample_demographic_data(lat, lng)
        
        return DemographicsData(
            population_density=round(density, 2),
            estimated_population=estimated_population,
            urban_rural_index=0.5,
            economic_activity_score=50.0,
            air_quality_index=aqi_value or sample_data.get('aqi'),
            air_quality_level=aqi_level or sample_data.get('aqi_level'),
            # Enhanced sample data for features demonstration
            zip_code=sample_data.get('zip_code'),
            median_household_income=sample_data.get('median_income'),
            per_capita_income=sample_data.get('per_capita_income'),
            median_age=sample_data.get('median_age'),
            education_bachelor_plus=sample_data.get('education_pct'),
            average_spending_retail=sample_data.get('monthly_retail_spending'),
            consumer_spending_index=sample_data.get('spending_index'),
            foot_traffic_multiplier=sample_data.get('foot_traffic_multiplier'),
            household_income_distribution=sample_data.get('income_distribution'),
            poverty_rate=sample_data.get('poverty_rate'),
            unemployment_rate=sample_data.get('unemployment_rate'),
            average_home_value=sample_data.get('home_value'),
            rent_burden_percentage=sample_data.get('rent_burden'),
            commute_time_minutes=sample_data.get('commute_time'),
            spending_categories=sample_data.get('spending_categories')
        )
        
    except Exception as e:
        print(f"Demographics error: {e}")
        return DemographicsData(
            air_quality_index=aqi_value if 'aqi_value' in locals() else None,
            air_quality_level=aqi_level if 'aqi_level' in locals() else None
        )

def estimate_population_fallback(lat: float, lng: float, radius: int):
    """Fallback population estimation based on geographic heuristics"""
    # Major city coordinates and rough population densities (people per km²)
    major_cities = {
        "delhi": {"lat": 28.6, "lng": 77.2, "density": 11000},
        "mumbai": {"lat": 19.1, "lng": 72.9, "density": 20700},
        "bangalore": {"lat": 12.9, "lng": 77.6, "density": 4100},
        "kolkata": {"lat": 22.6, "lng": 88.4, "density": 24000},
        "chennai": {"lat": 13.1, "lng": 80.3, "density": 26000},
        "london": {"lat": 51.5, "lng": -0.1, "density": 5600},
        "newyork": {"lat": 40.7, "lng": -74.0, "density": 10900},
        "tokyo": {"lat": 35.7, "lng": 139.7, "density": 6200}
    }
    
    # Find closest major city
    min_distance = float('inf')
    closest_density = 2000  # Default suburban density
    
    for city_data in major_cities.values():
        distance = math.sqrt((lat - city_data["lat"])**2 + (lng - city_data["lng"])**2)
        if distance < min_distance:
            min_distance = distance
            # Density decreases with distance from city center
            density_factor = max(0.1, 1 - (distance * 50))  # Adjust factor
            closest_density = city_data["density"] * density_factor
    
    area_km2 = (radius / 1000) ** 2 * math.pi
    return int(closest_density * area_km2)

def get_sample_demographic_data(lat: float, lng: float):
    """Generate realistic sample demographic data based on location for demonstration purposes"""
    import random
    
    # Set seed based on coordinates for consistent results
    random.seed(int((lat + lng) * 1000))
    
    # Determine location type based on coordinates
    major_cities = {
        "mumbai": {"lat": 19.1, "lng": 72.9, "type": "metro"},
        "delhi": {"lat": 28.6, "lng": 77.2, "type": "metro"},
        "bangalore": {"lat": 12.9, "lng": 77.6, "type": "metro"},
        "london": {"lat": 51.5, "lng": -0.1, "type": "global"},
        "newyork": {"lat": 40.7, "lng": -74.0, "type": "global"},
    }
    
    # Find closest city type
    location_type = "suburban"  # default
    min_distance = float('inf')
    
    for city_data in major_cities.values():
        distance = abs(lat - city_data["lat"]) + abs(lng - city_data["lng"])
        if distance < min_distance:
            min_distance = distance
            if distance < 0.5:  # Close to major city
                location_type = city_data["type"]
    
    # Generate sample data based on location type
    if location_type == "global":
        base_income = random.randint(65000, 95000)
        zip_code = f"{random.randint(10000, 99999)}"
        aqi = random.randint(25, 65)
        education_pct = random.randint(45, 75)
    elif location_type == "metro":
        base_income = random.randint(45000, 75000)
        zip_code = f"{random.randint(100000, 999999)}"
        aqi = random.randint(80, 150)
        education_pct = random.randint(35, 60)
    else:  # suburban
        base_income = random.randint(35000, 55000)
        zip_code = f"{random.randint(10000, 99999)}"
        aqi = random.randint(40, 90)
        education_pct = random.randint(25, 45)
    
    # Generate derived metrics
    per_capita = int(base_income * random.uniform(0.6, 0.8))
    median_age = random.randint(28, 42)
    monthly_retail = base_income * 0.12 / 12  # 12% of income on retail monthly
    spending_index = (base_income / 60000) * 100
    foot_traffic_mult = random.uniform(0.8, 1.4)
    
    # Income distribution (simplified)
    income_distribution = {
        "under_50k": {"percentage": random.randint(20, 40)},
        "50k_100k": {"percentage": random.randint(35, 50)},
        "100k_plus": {"percentage": random.randint(15, 30)}
    }
    
    # Spending categories
    annual_spending = base_income * 0.72
    spending_categories = {
        "housing": round(annual_spending * 0.33, 2),
        "food": round(annual_spending * 0.13, 2),
        "transportation": round(annual_spending * 0.16, 2),
        "retail_shopping": round(annual_spending * 0.12, 2),
        "entertainment": round(annual_spending * 0.05, 2),
        "other": round(annual_spending * 0.21, 2)
    }
    
    # AQI level mapping
    if aqi <= 50:
        aqi_level = "Good"
    elif aqi <= 100:
        aqi_level = "Moderate"
    elif aqi <= 150:
        aqi_level = "Unhealthy for Sensitive Groups"
    else:
        aqi_level = "Unhealthy"
    
    return {
        'zip_code': zip_code,
        'median_income': base_income,
        'per_capita_income': per_capita,
        'median_age': median_age,
        'education_pct': education_pct,
        'monthly_retail_spending': round(monthly_retail, 2),
        'spending_index': round(spending_index, 1),
        'foot_traffic_multiplier': round(foot_traffic_mult, 2),
        'income_distribution': income_distribution,
        'poverty_rate': random.randint(8, 18),
        'unemployment_rate': random.randint(3, 8),
        'home_value': random.randint(200000, 800000),
        'rent_burden': random.randint(25, 45),
        'commute_time': random.randint(18, 35),
        'spending_categories': spending_categories,
        'aqi': aqi,
        'aqi_level': aqi_level
    }

def get_sample_demographic_data(lat: float, lng: float):
    """Generate realistic sample demographic data based on location for demonstration purposes"""
    import random
    
    # Set seed based on coordinates for consistent results
    random.seed(int((lat + lng) * 1000))
    
    # Determine location type based on coordinates
    major_cities = {
        "mumbai": {"lat": 19.1, "lng": 72.9, "type": "metro"},
        "delhi": {"lat": 28.6, "lng": 77.2, "type": "metro"},
        "bangalore": {"lat": 12.9, "lng": 77.6, "type": "metro"},
        "london": {"lat": 51.5, "lng": -0.1, "type": "global"},
        "newyork": {"lat": 40.7, "lng": -74.0, "type": "global"},
    }
    
    # Find closest city type
    location_type = "suburban"  # default
    min_distance = float('inf')
    
    for city_data in major_cities.values():
        distance = abs(lat - city_data["lat"]) + abs(lng - city_data["lng"])
        if distance < min_distance:
            min_distance = distance
            if distance < 0.5:  # Close to major city
                location_type = city_data["type"]
    
    # Generate sample data based on location type
    if location_type == "global":
        base_income = random.randint(65000, 95000)
        zip_code = f"{random.randint(10000, 99999)}"
        aqi = random.randint(25, 65)
        education_pct = random.randint(45, 75)
    elif location_type == "metro":
        base_income = random.randint(45000, 75000)
        zip_code = f"{random.randint(100000, 999999)}"
        aqi = random.randint(80, 150)
        education_pct = random.randint(35, 60)
    else:  # suburban
        base_income = random.randint(35000, 55000)
        zip_code = f"{random.randint(10000, 99999)}"
        aqi = random.randint(40, 90)
        education_pct = random.randint(25, 45)
    
    # Generate derived metrics
    per_capita = int(base_income * random.uniform(0.6, 0.8))
    median_age = random.randint(28, 42)
    monthly_retail = base_income * 0.12 / 12  # 12% of income on retail monthly
    spending_index = (base_income / 60000) * 100
    foot_traffic_mult = random.uniform(0.8, 1.4)
    
    # Income distribution (simplified)
    income_distribution = {
        "under_50k": {"percentage": random.randint(20, 40)},
        "50k_100k": {"percentage": random.randint(35, 50)},
        "100k_plus": {"percentage": random.randint(15, 30)}
    }
    
    # Spending categories
    annual_spending = base_income * 0.72
    spending_categories = {
        "housing": round(annual_spending * 0.33, 2),
        "food": round(annual_spending * 0.13, 2),
        "transportation": round(annual_spending * 0.16, 2),
        "retail_shopping": round(annual_spending * 0.12, 2),
        "entertainment": round(annual_spending * 0.05, 2),
        "other": round(annual_spending * 0.21, 2)
    }
    
    # AQI level mapping
    aqi_levels = {
        range(0, 51): "Good",
        range(51, 101): "Moderate", 
        range(101, 151): "Unhealthy for Sensitive Groups",
        range(151, 201): "Unhealthy"
    }
    
    aqi_level = "Moderate"
    for aqi_range, level in aqi_levels.items():
        if aqi in aqi_range:
            aqi_level = level
            break
    
    return {
        'zip_code': zip_code,
        'median_income': base_income,
        'per_capita_income': per_capita,
        'median_age': median_age,
        'education_pct': education_pct,
        'monthly_retail_spending': round(monthly_retail, 2),
        'spending_index': round(spending_index, 1),
        'foot_traffic_multiplier': round(foot_traffic_mult, 2),
        'income_distribution': income_distribution,
        'poverty_rate': random.randint(8, 18),
        'unemployment_rate': random.randint(3, 8),
        'home_value': random.randint(200000, 800000),
        'rent_burden': random.randint(25, 45),
        'commute_time': random.randint(18, 35),
        'spending_categories': spending_categories,
        'aqi': aqi,
        'aqi_level': aqi_level
    }

def estimate_rental_costs(lat: float, lng: float, business_type: str):
    """Estimate rental costs using free data sources and heuristics"""
    # Rough rental estimates per sqft per month in USD (can be localized)
    city_rental_indices = {
        "mumbai": {"commercial": 15, "retail": 20, "tier": "Tier 1"},
        "delhi": {"commercial": 12, "retail": 18, "tier": "Tier 1"},
        "bangalore": {"commercial": 10, "retail": 15, "tier": "Tier 1"},
        "pune": {"commercial": 8, "retail": 12, "tier": "Tier 2"},
        "london": {"commercial": 50, "retail": 70, "tier": "Global Tier 1"},
        "newyork": {"commercial": 60, "retail": 80, "tier": "Global Tier 1"},
        "default": {"commercial": 8, "retail": 12, "tier": "Tier 3"}
    }
    
    # Determine city based on coordinates (simplified)
    rental_data = city_rental_indices["default"]
    
    # Business type multipliers
    business_multipliers = {
        "restaurant": 1.3,
        "cafe": 1.1,
        "salon": 1.0,
        "gym": 0.8,
        "retail": 1.2,
        "store": 1.0
    }
    
    base_rate = rental_data["retail"]
    multiplier = business_multipliers.get(business_type.lower(), 1.0)
    estimated_rate = base_rate * multiplier
    
    return RentalEstimate(
        estimated_rent_per_sqft=round(estimated_rate, 2),
        rental_index=f"${estimated_rate}/sqft/month",
        market_tier=rental_data["tier"]
    )

def calculate_break_even_analysis(business_type: str, competitor_count: int, demographics: DemographicsData, rental: RentalEstimate):
    """Calculate break-even analysis with enhanced US Census demographic data"""
    try:
        # Business-specific revenue estimates (per sqft per month)
        revenue_models = {
            "restaurant": {"revenue_per_sqft": 25, "operating_margin": 0.15, "avg_space": 2000},
            "cafe": {"revenue_per_sqft": 30, "operating_margin": 0.20, "avg_space": 1000},
            "salon": {"revenue_per_sqft": 35, "operating_margin": 0.25, "avg_space": 800},
            "gym": {"revenue_per_sqft": 8, "operating_margin": 0.30, "avg_space": 5000},
            "retail": {"revenue_per_sqft": 20, "operating_margin": 0.18, "avg_space": 1500},
            "default": {"revenue_per_sqft": 20, "operating_margin": 0.20, "avg_space": 1500}
        }
        
        model = revenue_models.get(business_type.lower(), revenue_models["default"])
        
        # Enhanced adjustments using US Census data
        competition_factor = max(0.5, 1 - (competitor_count * 0.05))
        
        # Use enhanced demographic factors
        if demographics.consumer_spending_index:
            # Spending index factor (100 = national average)
            spending_factor = demographics.consumer_spending_index / 100
        elif demographics.economic_activity_score:
            spending_factor = demographics.economic_activity_score / 100
        else:
            spending_factor = 1.0
        
        # Foot traffic multiplier from Census data
        foot_traffic_mult = demographics.foot_traffic_multiplier or 1.0
        
        # Income-based adjustment
        if demographics.median_household_income:
            # Higher income areas support higher revenue per sqft
            income_factor = min(demographics.median_household_income / 50000, 2.0)  # Cap at 2x
        else:
            income_factor = 1.0
        
        # Education factor (higher education = more discretionary spending)
        if demographics.education_bachelor_plus:
            education_factor = 1 + (demographics.education_bachelor_plus / 100 * 0.3)  # Up to 30% boost
        else:
            education_factor = 1.0
        
        # Combined demographic multiplier
        demographic_multiplier = spending_factor * foot_traffic_mult * income_factor * education_factor
        
        adjusted_revenue_per_sqft = (model["revenue_per_sqft"] * 
                                   competition_factor * 
                                   demographic_multiplier)
        
        space_sqft = model["avg_space"]
        
        # Calculate monthly figures
        monthly_revenue = adjusted_revenue_per_sqft * space_sqft
        monthly_rent = (rental.estimated_rent_per_sqft or 10) * space_sqft
        monthly_operating_costs = monthly_revenue * (1 - model["operating_margin"])
        monthly_total_costs = monthly_rent + monthly_operating_costs
        
        monthly_profit = monthly_revenue - monthly_total_costs
        
        # Break-even calculation
        initial_investment = monthly_total_costs * 6  # 6 months of costs as initial investment
        break_even_months = initial_investment / max(monthly_profit, 1) if monthly_profit > 0 else float('inf')
        
        # ROI calculation
        annual_profit = monthly_profit * 12
        roi_percentage = (annual_profit / initial_investment) * 100 if initial_investment > 0 else 0
        
        return BreakEvenAnalysis(
            estimated_monthly_revenue=round(monthly_revenue, 2),
            monthly_costs=round(monthly_total_costs, 2),
            break_even_months=round(break_even_months, 1) if break_even_months != float('inf') else None,
            roi_percentage=round(roi_percentage, 1),
            profit_projection_year1=round(annual_profit, 2)
        )
        
    except Exception as e:
        print(f"Break-even calculation error: {e}")
        return BreakEvenAnalysis()

def calculate_saturation_score(competitor_count: int, radius: int):
    """Calculate business saturation score (0-100)"""
    area_km2 = (radius / 1000) ** 2 * 3.14159
    density = competitor_count / area_km2
    
    if density < 0.5:
        return 20
    elif density < 1:
        return 40
    elif density < 2:
        return 60
    elif density < 3:
        return 80
    else:
        return 100

def calculate_foot_traffic_score(competitors: List[CompetitorInfo], demographics: DemographicsData):
    """Estimate foot traffic score based on competitor ratings and demographics"""
    if not competitors:
        return 30.0
    
    # Average rating of nearby competitors (indicates area attractiveness)
    ratings = [c.rating for c in competitors if c.rating]
    avg_rating = sum(ratings) / len(ratings) if ratings else 3.5
    
    # Population density factor
    density_factor = min((demographics.population_density or 1000) / 5000, 1.0)
    
    # Combine factors
    traffic_score = (avg_rating / 5.0) * 0.6 + density_factor * 0.4
    return round(traffic_score * 100, 1)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "location-intelligence-advanced"}

@app.post("/api/search-competitors-advanced")
async def search_competitors_advanced(request: LocationSearchRequest):
    try:
        # Geocode the location
        lat, lng = geocode_location(request.location)
        
        # Search for competitors
        competitors = search_competitors(lat, lng, request.business_type, request.radius)
        
        # Get demographics data
        demographics = await get_population_demographics(lat, lng, request.radius)
        
        # Estimate rental costs
        rental_estimates = estimate_rental_costs(lat, lng, request.business_type)
        
        # Calculate break-even analysis
        break_even_analysis = calculate_break_even_analysis(
            request.business_type, len(competitors), demographics, rental_estimates
        )
        
        # Calculate scores
        competitor_count = len(competitors)
        saturation_score = calculate_saturation_score(competitor_count, request.radius)
        foot_traffic_score = calculate_foot_traffic_score(competitors, demographics)
        
        # Create analysis record
        search_id = str(uuid.uuid4())
        analysis = {
            "search_id": search_id,
            "business_type": request.business_type,
            "location": request.location,
            "center_lat": lat,
            "center_lng": lng,
            "center_location": {"type": "Point", "coordinates": [lng, lat]},
            "radius": request.radius,
            "competitors": [comp.dict() for comp in competitors],
            "competitor_count": competitor_count,
            "saturation_score": saturation_score,
            "demographics": demographics.dict(),
            "rental_estimates": rental_estimates.dict(),
            "break_even_analysis": break_even_analysis.dict(),
            "foot_traffic_score": foot_traffic_score,
            "analysis_date": datetime.now()
        }
        
        # Store in database
        searches_collection.insert_one(analysis)
        
        return {
            "search_id": search_id,
            "location": request.location,
            "center_coordinates": {"lat": lat, "lng": lng},
            "business_type": request.business_type,
            "competitors": competitors,
            "competitor_count": competitor_count,
            "saturation_score": saturation_score,
            "demographics": demographics,
            "rental_estimates": rental_estimates,
            "break_even_analysis": break_even_analysis,
            "foot_traffic_score": foot_traffic_score,
            "radius": request.radius
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compare-locations")
async def compare_locations(request: ComparisonRequest):
    try:
        if len(request.locations) < 2 or len(request.locations) > 4:
            raise HTTPException(status_code=400, detail="Please provide 2-4 locations for comparison")
        
        comparison_results = []
        
        for location_request in request.locations:
            # Get analysis for each location
            lat, lng = geocode_location(location_request.location)
            competitors = search_competitors(lat, lng, location_request.business_type, location_request.radius)
            demographics = await get_population_demographics(lat, lng, location_request.radius)
            rental_estimates = estimate_rental_costs(lat, lng, location_request.business_type)
            break_even_analysis = calculate_break_even_analysis(
                location_request.business_type, len(competitors), demographics, rental_estimates
            )
            
            competitor_count = len(competitors)
            saturation_score = calculate_saturation_score(competitor_count, location_request.radius)
            foot_traffic_score = calculate_foot_traffic_score(competitors, demographics)
            
            analysis_result = {
                "location": location_request.location,
                "business_type": location_request.business_type,
                "center_coordinates": {"lat": lat, "lng": lng},
                "competitors": [comp.dict() for comp in competitors],
                "competitor_count": competitor_count,
                "saturation_score": saturation_score,
                "demographics": demographics.dict(),
                "rental_estimates": rental_estimates.dict(),
                "break_even_analysis": break_even_analysis.dict(),
                "foot_traffic_score": foot_traffic_score,
                "radius": location_request.radius
            }
            
            comparison_results.append(analysis_result)
        
        # Generate comparison summary
        summary = {
            "best_for_low_competition": None,
            "best_for_roi": None,
            "best_for_foot_traffic": None,
            "best_for_demographics": None
        }
        
        if comparison_results:
            min_saturation = min(r["saturation_score"] for r in comparison_results)
            max_roi = max(r["break_even_analysis"]["roi_percentage"] or 0 for r in comparison_results)
            max_traffic = max(r["foot_traffic_score"] or 0 for r in comparison_results)
            max_population = max(r["demographics"]["estimated_population"] or 0 for r in comparison_results)
            
            for result in comparison_results:
                if result["saturation_score"] == min_saturation:
                    summary["best_for_low_competition"] = result["location"]
                if (result["break_even_analysis"]["roi_percentage"] or 0) == max_roi:
                    summary["best_for_roi"] = result["location"]
                if (result["foot_traffic_score"] or 0) == max_traffic:
                    summary["best_for_foot_traffic"] = result["location"]
                if (result["demographics"]["estimated_population"] or 0) == max_population:
                    summary["best_for_demographics"] = result["location"]
        
        # Create comparison record
        comparison_id = str(uuid.uuid4())
        comparison_data = {
            "comparison_id": comparison_id,
            "locations": comparison_results,
            "comparison_date": datetime.now(),
            "summary": summary
        }
        
        # Store comparison
        comparisons_collection.insert_one(comparison_data.copy())
        
        return comparison_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def generate_comparison_summary(results: List[Dict[str, Any]]):
    """Generate insights summary for location comparison"""
    summary = {
        "best_for_low_competition": None,
        "best_for_roi": None,
        "best_for_foot_traffic": None,
        "best_for_demographics": None,
        "recommendations": []
    }
    
    if not results:
        return summary
    
    # Find best locations for different criteria
    min_saturation = min(r["saturation_score"] for r in results)
    
    # Handle break_even_analysis which is a BreakEvenAnalysis object
    roi_values = []
    for r in results:
        roi = 0
        if hasattr(r["break_even_analysis"], 'roi_percentage'):
            roi = r["break_even_analysis"].roi_percentage or 0
        elif isinstance(r["break_even_analysis"], dict):
            roi = r["break_even_analysis"].get("roi_percentage", 0) or 0
        roi_values.append(roi)
    
    max_roi = max(roi_values) if roi_values else 0
    max_traffic = max((r.get("foot_traffic_score", 0) or 0) for r in results)
    
    # Handle demographics
    pop_values = []
    for r in results:
        pop = 0
        if hasattr(r["demographics"], 'estimated_population'):
            pop = r["demographics"].estimated_population or 0
        elif isinstance(r["demographics"], dict):
            pop = r["demographics"].get("estimated_population", 0) or 0
        pop_values.append(pop)
    
    max_population = max(pop_values) if pop_values else 0
    
    for i, result in enumerate(results):
        location_name = result["location"]
        
        if result["saturation_score"] == min_saturation:
            summary["best_for_low_competition"] = location_name
        
        if roi_values[i] == max_roi and max_roi > 0:
            summary["best_for_roi"] = location_name
            
        if (result.get("foot_traffic_score", 0) or 0) == max_traffic:
            summary["best_for_foot_traffic"] = location_name
            
        if pop_values[i] == max_population and max_population > 0:
            summary["best_for_demographics"] = location_name
    
    return summary

@app.get("/api/search/{search_id}")
async def get_search_analysis(search_id: str):
    try:
        analysis = searches_collection.find_one({"search_id": search_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        analysis['_id'] = str(analysis['_id'])
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/searches")
async def get_recent_searches():
    try:
        searches = list(searches_collection.find().sort("analysis_date", -1).limit(50))
        
        for search in searches:
            search['_id'] = str(search['_id'])
        
        return searches
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/comparisons")
async def get_recent_comparisons():
    try:
        comparisons = list(comparisons_collection.find().sort("comparison_date", -1).limit(20))
        
        for comparison in comparisons:
            comparison['_id'] = str(comparison['_id'])
        
        return comparisons
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)