import React, { useState, useEffect } from "react";
import "./App.css";

const BACKEND_URL =
  process.env.REACT_APP_BACKEND_URL || "http://localhost:8001";

function App() {
  const [showLandingPage, setShowLandingPage] = useState(true);
  const [singleLocation, setSingleLocation] = useState({
    businessType: "",
    location: "",
    radius: 5000,
  });
  const [loading, setLoading] = useState(false);
  const [singleAnalysis, setSingleAnalysis] = useState(null);
  const [error, setError] = useState("");
  const [map, setMap] = useState(null);
  const [markers, setMarkers] = useState([]);

  // Initialize Google Maps only when not on landing page
  useEffect(() => {
    if (showLandingPage) return;

    const initMap = () => {
      const mapElement = document.getElementById("map");
      if (!mapElement) return;

      const mapInstance = new window.google.maps.Map(mapElement, {
        center: { lat: 28.6139, lng: 77.209 },
        zoom: 12,
        styles: [
          {
            featureType: "poi",
            elementType: "labels",
            stylers: [{ visibility: "off" }],
          },
        ],
      });
      setMap(mapInstance);
    };

    if (window.google && window.google.maps) {
      initMap();
    } else {
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=AIzaSyABOBWi8rAH8sdr2AYCfuVtg0ZxrdjrBR8&libraries=places`;
      script.async = true;
      script.defer = true;
      script.onload = initMap;
      document.head.appendChild(script);
    }
  }, [showLandingPage]);

  const clearMarkers = () => {
    markers.forEach((marker) => marker.setMap(null));
    setMarkers([]);
  };

  const addMarkersToMap = (analyses) => {
    if (!map) return;

    clearMarkers();
    const newMarkers = [];
    const bounds = new window.google.maps.LatLngBounds();

    analyses.forEach((analysis, index) => {
      const centerCoords = analysis.center_coordinates;
      const competitors = analysis.competitors;

      // Colors for different locations in comparison
      const colors = ["#059669", "#dc2626", "#7c3aed", "#ea580c"];
      const color = colors[index % colors.length];

      // Add center marker
      const centerMarker = new window.google.maps.Marker({
        position: centerCoords,
        map: map,
        title: `${analysis.location} (${analysis.business_type})`,
        icon: {
          url: `data:image/svg+xml;charset=UTF-8,%3Csvg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24"%3E%3Cpath fill="${encodeURIComponent(color)}" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/%3E%3C/svg%3E`,
          scaledSize: new window.google.maps.Size(40, 40),
        },
      });
      newMarkers.push(centerMarker);
      bounds.extend(centerCoords);

      // Add competitor markers
      competitors.forEach((competitor) => {
        const marker = new window.google.maps.Marker({
          position: { lat: competitor.lat, lng: competitor.lng },
          map: map,
          title: competitor.name,
          icon: {
            url: 'data:image/svg+xml;charset=UTF-8,%3Csvg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"%3E%3Cpath fill="%23666" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/%3E%3C/svg%3E',
            scaledSize: new window.google.maps.Size(24, 24),
          },
        });

        const infoWindow = new window.google.maps.InfoWindow({
          content: `
            <div style="padding: 8px;">
              <h3 style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">${competitor.name}</h3>
              <p style="margin: 0; font-size: 12px; color: #666;">${competitor.address}</p>
              ${competitor.rating ? `<p style="margin: 4px 0 0 0; font-size: 12px;">⭐ ${competitor.rating}</p>` : ""}
            </div>
          `,
        });

        marker.addListener("click", () => {
          infoWindow.open(map, marker);
        });

        newMarkers.push(marker);
        bounds.extend({ lat: competitor.lat, lng: competitor.lng });
      });
    });

    setMarkers(newMarkers);
    if (analyses.length > 0) {
      map.fitBounds(bounds);
    }
  };

  const handleSingleSearch = async (e) => {
    e.preventDefault();
    if (!singleLocation.businessType || !singleLocation.location) {
      setError("Please fill in both business type and location");
      return;
    }

    setLoading(true);
    setError("");
    setSingleAnalysis(null);

    try {
      const response = await fetch(
        `${BACKEND_URL}/api/search-competitors-advanced`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            business_type: singleLocation.businessType,
            location: singleLocation.location,
            radius: singleLocation.radius,
          }),
        },
      );

      if (!response.ok) {
        throw new Error("Failed to search competitors");
      }

      const data = await response.json();
      setSingleAnalysis(data);
      addMarkersToMap([data]);
    } catch (err) {
      setError(err.message || "An error occurred while searching");
    } finally {
      setLoading(false);
    }
  };

  const getSaturationColor = (score) => {
    if (score <= 30) return "text-green-600";
    if (score <= 60) return "text-yellow-600";
    return "text-red-600";
  };

  const getSaturationLabel = (score) => {
    if (score <= 30) return "Low";
    if (score <= 60) return "Medium";
    return "High";
  };

  const getAQIColor = (aqi) => {
    if (aqi <= 50) return "text-green-600"; // Good
    if (aqi <= 100) return "text-yellow-600"; // Moderate
    if (aqi <= 150) return "text-orange-600"; // Unhealthy for Sensitive Groups
    if (aqi <= 200) return "text-red-600"; // Unhealthy
    if (aqi <= 300) return "text-purple-600"; // Very Unhealthy
    return "text-red-800"; // Hazardous
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount || 0);
  };

  // Landing Page Component
  if (showLandingPage) {
    return (
      <div className="min-h-screen" style={{ background: "#0a0a0a" }}>
        {/* Landing Header */}
        <header className="corporate-header" style={{ background: "#0a0a0a" }}>
          <div className="max-w-7xl mx-auto px-4 py-6 flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <img
                src="https://customer-assets.emergentagent.com/job_sitescout-1/artifacts/ixkexm8h_WhatsApp%20Image%201947-05-08%20at%2000.19.30.jpeg"
                alt="Geonome Logo"
                className="corporate-logo h-16 w-16 object-contain"
              />
              <div>
                <h1
                  className="text-4xl text-white font-bold"
                  style={{ color: "#ffffff" }}
                >
                  Geonome
                </h1>
                <p className="text-white text-opacity-90 mt-2 font-medium italic">
                  "Built on maps backed by insight"
                </p>
              </div>
            </div>
          </div>
        </header>

        {/* Landing Content */}
        <div className="max-w-7xl mx-auto px-4 py-12">
          {/* Hero Section */}
          <div className="text-center mb-16">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-5xl font-bold text-white mb-8 leading-tight">
                Pick the perfect business location with{" "}
                <span className="text-blue-400">data</span>, not guesswork
              </h2>
              <p className="text-xl text-white text-opacity-80 mb-12 leading-relaxed">
                Our tool gives real-time insights on competitors, rent, and
                spending trends—so you launch smarter, faster, and with
                confidence.
              </p>
              <button
                onClick={() => setShowLandingPage(false)}
                className="corporate-btn text-lg px-12 py-4 transform hover:scale-105"
              >
                <span className="mr-3">🚀</span>
                Get Started Now
              </button>
            </div>
          </div>

          {/* Features Grid with Images */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-16">
            {/* Data Analysis Feature */}
            <div className="corporate-card p-8 text-center">
              <img
                src="https://images.unsplash.com/photo-1563986768711-b3bde3dc821e"
                alt="Data Analysis"
                className="w-full h-48 object-cover rounded-lg mb-6"
              />
              <div className="corporate-icon mx-auto mb-4">📊</div>
              <h3 className="text-xl font-bold text-gray-800 mb-4">
                Real-Time Analytics
              </h3>
              <p className="text-gray-600">
                Get comprehensive insights on competitor density, market
                saturation, and local business trends with live data updates.
              </p>
            </div>

            {/* Strategic Planning Feature */}
            <div className="corporate-card p-8 text-center">
              <img
                src="https://images.unsplash.com/photo-1573167507387-6b4b98cb7c13"
                alt="Strategic Planning"
                className="w-full h-48 object-cover rounded-lg mb-6"
              />
              <div className="corporate-icon mx-auto mb-4">🎯</div>
              <h3 className="text-xl font-bold text-gray-800 mb-4">
                Strategic Insights
              </h3>
              <p className="text-gray-600">
                Make informed decisions with detailed demographics, spending
                patterns, and financial projections for any location.
              </p>
            </div>

            {/* Business Success Feature */}
            <div className="corporate-card p-8 text-center">
              <img
                src="https://images.pexels.com/photos/3810792/pexels-photo-3810792.jpeg"
                alt="Business Success"
                className="w-full h-48 object-cover rounded-lg mb-6"
              />
              <div className="corporate-icon mx-auto mb-4">💼</div>
              <h3 className="text-xl font-bold text-gray-800 mb-4">
                Business Success
              </h3>
              <p className="text-gray-600">
                Launch with confidence using our comprehensive location
                intelligence platform trusted by entrepreneurs worldwide.
              </p>
            </div>
          </div>

          {/* Call to Action Section */}
          <div className="corporate-card p-12 text-center">
            <h3 className="text-3xl font-bold text-gray-800 mb-6">
              Ready to find your perfect business location?
            </h3>
            <p className="text-lg text-gray-600 mb-8">
              Join thousands of entrepreneurs who have successfully launched
              their businesses using our platform.
            </p>
            <button
              onClick={() => setShowLandingPage(false)}
              className="corporate-btn text-lg px-12 py-4 transform hover:scale-105"
            >
              <span className="mr-3">⚡</span>
              Start Your Analysis
            </button>
          </div>
        </div>

        {/* Footer */}
        <footer className="border-t border-white border-opacity-20 py-8">
          <div className="max-w-7xl mx-auto px-4 text-center">
            <p className="text-white text-opacity-60">
              © 2025 Geonome. Professional Location Intelligence Platform.
            </p>
          </div>
        </footer>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "#0a0a0a" }}>
      <header className="corporate-header" style={{ background: "#0a0a0a" }}>
        <div className="max-w-7xl mx-auto px-4 py-6 flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <img
              src="https://customer-assets.emergentagent.com/job_sitescout-1/artifacts/ixkexm8h_WhatsApp%20Image%201947-05-08%20at%2000.19.30.jpeg"
              alt="Geonome Logo"
              className="corporate-logo h-16 w-16 object-contain"
            />
            <div>
              <h1
                className="text-4xl text-white font-bold"
                style={{ color: "#ffffff" }}
              >
                Geonome
              </h1>
              <p className="text-white text-opacity-90 mt-2 font-medium">
                Professional Location Intelligence Platform
              </p>
            </div>
          </div>
          <div className="hidden md:flex items-center space-x-8 text-white text-sm">
            <div className="flex items-center">
              <div
                className="corporate-icon-sm mr-3"
                style={{
                  background: "rgba(255, 255, 255, 0.2)",
                  color: "white",
                  border: "1px solid rgba(255, 255, 255, 0.3)",
                }}
              >
                📊
              </div>
              <span className="font-medium text-white">Advanced Analytics</span>
            </div>
            <div className="flex items-center">
              <div
                className="corporate-icon-sm mr-3"
                style={{
                  background: "rgba(255, 255, 255, 0.2)",
                  color: "white",
                  border: "1px solid rgba(255, 255, 255, 0.3)",
                }}
              >
                🏢
              </div>
              <span className="font-medium text-white">Enterprise Ready</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
          {/* Left Sidebar - Search Form */}
          <div className="xl:col-span-1">
            <div className="corporate-card p-6 sticky top-8">
              <div className="flex items-center mb-6">
                <div className="corporate-icon">🔍</div>
                <h2 className="corporate-title text-xl">Location Analysis</h2>
              </div>
              <form onSubmit={handleSingleSearch} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <div className="flex items-center">
                      <div className="corporate-icon-sm mr-2">🏪</div>
                      Business Type
                    </div>
                  </label>
                  <input
                    type="text"
                    value={singleLocation.businessType}
                    onChange={(e) =>
                      setSingleLocation({
                        ...singleLocation,
                        businessType: e.target.value,
                      })
                    }
                    placeholder="e.g., restaurant, café, salon, gym"
                    className="corporate-input w-full"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <div className="flex items-center">
                      <div className="corporate-icon-sm mr-2">📍</div>
                      Location
                    </div>
                  </label>
                  <input
                    type="text"
                    value={singleLocation.location}
                    onChange={(e) =>
                      setSingleLocation({
                        ...singleLocation,
                        location: e.target.value,
                      })
                    }
                    placeholder="e.g., Connaught Place, Delhi"
                    className="corporate-input w-full"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <div className="flex items-center">
                      <div className="corporate-icon-sm mr-2">📏</div>
                      Search Radius
                    </div>
                  </label>
                  <select
                    value={singleLocation.radius}
                    onChange={(e) =>
                      setSingleLocation({
                        ...singleLocation,
                        radius: Number(e.target.value),
                      })
                    }
                    className="corporate-select w-full"
                  >
                    <option value={1000}>1 km radius</option>
                    <option value={2000}>2 km radius</option>
                    <option value={5000}>5 km radius</option>
                    <option value={10000}>10 km radius</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="corporate-btn w-full"
                >
                  {loading ? (
                    <div className="flex items-center justify-center">
                      <div className="loading-spinner mr-2"></div>
                      Analyzing...
                    </div>
                  ) : (
                    <div className="flex items-center justify-center">
                      <span className="mr-2">⚡</span>
                      Analyze Location
                    </div>
                  )}
                </button>
              </form>

              {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center">
                    <div className="corporate-icon-sm corporate-icon-error mr-2">
                      ⚠️
                    </div>
                    <p className="text-sm text-red-600 font-medium">{error}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Center - Map and Competitors */}
          <div className="xl:col-span-2">
            <div className="space-y-6">
              {/* Map */}
              <div className="corporate-card p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center">
                    <div className="corporate-icon">🗺️</div>
                    <h2 className="corporate-title text-xl">
                      Interactive Location Map
                    </h2>
                  </div>
                  {singleAnalysis && (
                    <div className="flex items-center text-sm text-gray-600">
                      <div className="corporate-icon-sm corporate-icon-success mr-2">
                        ✓
                      </div>
                      Analysis Complete
                    </div>
                  )}
                </div>
                <div className="corporate-map-container">
                  <div id="map" className="w-full h-96"></div>
                </div>
                <div className="mt-4 flex items-center justify-center space-x-8 text-sm text-gray-600">
                  <div className="flex items-center">
                    <div className="w-4 h-4 bg-blue-600 rounded-full mr-2 border-2 border-white shadow-md"></div>
                    <span className="font-medium">Your Location</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-4 h-4 bg-gray-600 rounded-full mr-2 border-2 border-white shadow-md"></div>
                    <span className="font-medium">Competitors</span>
                  </div>
                </div>
              </div>

              {/* Competitors List */}
              {singleAnalysis &&
                singleAnalysis.competitors &&
                singleAnalysis.competitors.length > 0 && (
                  <div className="corporate-card p-6 animate-slide-up">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center">
                        <div className="corporate-icon">🏢</div>
                        <h3 className="corporate-title text-lg">
                          Nearby Competitors
                        </h3>
                      </div>
                      <div className="flex items-center bg-blue-50 px-3 py-1 rounded-full">
                        <span className="text-blue-600 font-semibold text-sm">
                          {singleAnalysis.competitors.length} Found
                        </span>
                      </div>
                    </div>
                    <div className="max-h-64 overflow-y-auto space-y-3">
                      {singleAnalysis.competitors.map((competitor, index) => (
                        <div key={index} className="competitor-card">
                          <div className="flex items-start space-x-3">
                            <div className="competitor-badge">{index + 1}</div>
                            <div className="flex-1 min-w-0">
                              <h4 className="corporate-title text-base truncate">
                                {competitor.name}
                              </h4>
                              <p className="text-sm text-gray-600 mt-1 flex items-center">
                                <span className="mr-1">📍</span>
                                {competitor.address}
                              </p>
                              <div className="flex items-center mt-3 space-x-4">
                                {competitor.rating && (
                                  <div className="flex items-center bg-yellow-50 px-2 py-1 rounded-md">
                                    <span className="text-yellow-600 mr-1">
                                      ⭐
                                    </span>
                                    <span className="text-sm font-medium text-yellow-700">
                                      {competitor.rating}
                                    </span>
                                  </div>
                                )}
                                {competitor.price_level && (
                                  <div className="flex items-center bg-green-50 px-2 py-1 rounded-md">
                                    <span className="text-green-600 text-sm font-medium">
                                      {"$".repeat(competitor.price_level)}
                                    </span>
                                  </div>
                                )}
                                {competitor.user_ratings_total && (
                                  <div className="text-xs text-gray-500 flex items-center">
                                    <span className="mr-1">👥</span>
                                    {competitor.user_ratings_total} reviews
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          </div>

          {/* Right Sidebar - Analytics */}
          <div className="xl:col-span-1">
            {singleAnalysis && (
              <div className="space-y-4 sticky top-8 animate-slide-up">
                {/* Competition Analysis */}
                <div className="corporate-sidebar-card p-4">
                  <div className="flex items-center mb-3">
                    <div className="corporate-icon-sm mr-2">🎯</div>
                    <h3 className="corporate-title text-base">Competition</h3>
                  </div>
                  <div className="space-y-3">
                    <div className="metric-card">
                      <div className="metric-value text-blue-600">
                        {singleAnalysis.competitor_count}
                      </div>
                      <div className="metric-label">Total Competitors</div>
                    </div>
                    <div className="metric-card">
                      <div
                        className={`metric-value ${getSaturationColor(singleAnalysis.saturation_score)}`}
                      >
                        {getSaturationLabel(singleAnalysis.saturation_score)}
                      </div>
                      <div className="metric-label">Market Saturation</div>
                    </div>
                  </div>
                </div>

                {/* Key Demographics */}
                <div className="corporate-sidebar-card p-4">
                  <div className="flex items-center mb-3">
                    <div className="corporate-icon-sm mr-2">👥</div>
                    <h3 className="corporate-title text-base">Demographics</h3>
                  </div>
                  <div className="space-y-3">
                    <div className="data-row">
                      <span className="data-label flex items-center">
                        <span className="mr-1">🏘️</span>Population:
                      </span>
                      <span className="data-value">
                        {singleAnalysis.demographics?.estimated_population?.toLocaleString() ||
                          "N/A"}
                      </span>
                    </div>
                    {singleAnalysis.demographics?.median_household_income && (
                      <div className="data-row">
                        <span className="data-label flex items-center">
                          <span className="mr-1">💰</span>Med. Income:
                        </span>
                        <span className="data-value text-green-600">
                          {formatCurrency(
                            singleAnalysis.demographics.median_household_income,
                          )}
                        </span>
                      </div>
                    )}
                    {singleAnalysis.demographics?.median_age && (
                      <div className="data-row">
                        <span className="data-label flex items-center">
                          <span className="mr-1">📊</span>Med. Age:
                        </span>
                        <span className="data-value">
                          {Number(
                            singleAnalysis.demographics.median_age,
                          ).toFixed(1)}{" "}
                          yrs
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Financial Projections */}
                <div className="corporate-sidebar-card p-4">
                  <div className="flex items-center mb-3">
                    <div className="corporate-icon-sm mr-2">📈</div>
                    <h3 className="corporate-title text-base">Financials</h3>
                  </div>
                  <div className="space-y-3">
                    <div className="data-row">
                      <span className="data-label flex items-center">
                        <span className="mr-1">📊</span>Revenue:
                      </span>
                      <span className="data-value text-green-600">
                        {formatCurrency(
                          singleAnalysis.break_even_analysis
                            .estimated_monthly_revenue,
                        )}
                      </span>
                    </div>
                    <div className="data-row">
                      <span className="data-label flex items-center">
                        <span className="mr-1">💸</span>Costs:
                      </span>
                      <span className="data-value text-red-600">
                        {formatCurrency(
                          singleAnalysis.break_even_analysis.monthly_costs,
                        )}
                      </span>
                    </div>
                    <div className="data-row">
                      <span className="data-label flex items-center">
                        <span className="mr-1">⏱️</span>Break-even:
                      </span>
                      <span className="data-value">
                        {singleAnalysis.break_even_analysis.break_even_months
                          ? `${singleAnalysis.break_even_analysis.break_even_months} mo`
                          : "N/A"}
                      </span>
                    </div>
                    <div className="data-row">
                      <span className="data-label flex items-center">
                        <span className="mr-1">🎯</span>ROI:
                      </span>
                      <span
                        className={`data-value ${
                          (singleAnalysis.break_even_analysis.roi_percentage ||
                            0) > 20
                            ? "text-green-600"
                            : "text-yellow-600"
                        }`}
                      >
                        {singleAnalysis.break_even_analysis.roi_percentage || 0}
                        %
                      </span>
                    </div>
                  </div>
                </div>

                {/* Air Quality */}
                {singleAnalysis.demographics?.air_quality_index && (
                  <div className="corporate-sidebar-card p-4">
                    <div className="flex items-center mb-3">
                      <div className="corporate-icon-sm mr-2">🌤️</div>
                      <h3 className="corporate-title text-base">Air Quality</h3>
                    </div>
                    <div className="metric-card">
                      <div
                        className={`metric-value ${getAQIColor(singleAnalysis.demographics.air_quality_index)}`}
                      >
                        {singleAnalysis.demographics.air_quality_index}
                      </div>
                      <div
                        className={`text-xs font-medium ${getAQIColor(singleAnalysis.demographics.air_quality_index)}`}
                      >
                        {singleAnalysis.demographics.air_quality_level}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Detailed Analytics Section */}
        {singleAnalysis && (
          <div className="mt-8 animate-slide-up">
            <div className="corporate-card p-6 mb-6">
              <div className="flex items-center mb-6">
                <div className="corporate-icon">📊</div>
                <h2 className="corporate-title text-2xl">
                  Comprehensive Business Intelligence
                </h2>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {/* Detailed Demographics */}
                <div className="corporate-sidebar-card p-6">
                  <div className="flex items-center mb-4">
                    <div className="corporate-icon-sm mr-3">🏘️</div>
                    <h3 className="corporate-title text-lg">
                      Detailed Demographics
                    </h3>
                  </div>
                  {singleAnalysis.demographics?.zip_code && (
                    <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                      <div className="flex items-center">
                        <div className="corporate-icon-sm mr-2">📍</div>
                        <h4 className="font-semibold text-blue-900">
                          ZIP Code: {singleAnalysis.demographics.zip_code}
                        </h4>
                      </div>
                    </div>
                  )}
                  <div className="space-y-3">
                    <div className="data-row">
                      <span className="data-label">Population Density:</span>
                      <span className="data-value">
                        {singleAnalysis.demographics?.population_density ||
                          "N/A"}{" "}
                        /km²
                      </span>
                    </div>
                    {singleAnalysis.demographics?.per_capita_income && (
                      <div className="data-row">
                        <span className="data-label">Per Capita Income:</span>
                        <span className="data-value">
                          {formatCurrency(
                            singleAnalysis.demographics.per_capita_income,
                          )}
                        </span>
                      </div>
                    )}
                    {singleAnalysis.demographics?.education_bachelor_plus && (
                      <div className="data-row">
                        <span className="data-label">College Educated:</span>
                        <span className="data-value">
                          {Number(
                            singleAnalysis.demographics.education_bachelor_plus,
                          ).toFixed(1)}
                          %
                        </span>
                      </div>
                    )}
                    {singleAnalysis.demographics?.unemployment_rate !==
                      undefined &&
                      singleAnalysis.demographics.unemployment_rate !==
                        null && (
                        <div className="data-row">
                          <span className="data-label">Unemployment:</span>
                          <span
                            className={`data-value ${Number(singleAnalysis.demographics.unemployment_rate) < 5 ? "text-green-600" : "text-red-600"}`}
                          >
                            {Number(
                              singleAnalysis.demographics.unemployment_rate,
                            ).toFixed(1)}
                            %
                          </span>
                        </div>
                      )}
                    {singleAnalysis.demographics?.poverty_rate !== undefined &&
                      singleAnalysis.demographics.poverty_rate !== null && (
                        <div className="data-row">
                          <span className="data-label">Poverty Rate:</span>
                          <span
                            className={`data-value ${Number(singleAnalysis.demographics.poverty_rate) < 15 ? "text-green-600" : "text-yellow-600"}`}
                          >
                            {Number(
                              singleAnalysis.demographics.poverty_rate,
                            ).toFixed(1)}
                            %
                          </span>
                        </div>
                      )}
                    <div className="data-row">
                      <span className="data-label">Foot Traffic:</span>
                      <span className="data-value">
                        {singleAnalysis.foot_traffic_score || "N/A"}/100
                      </span>
                    </div>
                  </div>
                </div>

                {/* Consumer Spending Analysis */}
                {(singleAnalysis.demographics?.average_spending_retail ||
                  singleAnalysis.demographics?.consumer_spending_index ||
                  singleAnalysis.demographics?.spending_categories) && (
                  <div className="corporate-sidebar-card p-6">
                    <div className="flex items-center mb-4">
                      <div className="corporate-icon-sm mr-3">💳</div>
                      <h3 className="corporate-title text-lg">
                        Consumer Spending
                      </h3>
                    </div>
                    <div className="space-y-3">
                      {singleAnalysis.demographics?.average_spending_retail && (
                        <div className="data-row">
                          <span className="data-label">Monthly Retail:</span>
                          <span className="data-value text-green-600">
                            {formatCurrency(
                              singleAnalysis.demographics
                                .average_spending_retail,
                            )}
                          </span>
                        </div>
                      )}
                      {singleAnalysis.demographics?.consumer_spending_index && (
                        <div className="data-row">
                          <span className="data-label">Spending Index:</span>
                          <span
                            className={`data-value ${
                              Number(
                                singleAnalysis.demographics
                                  .consumer_spending_index,
                              ) > 100
                                ? "text-green-600"
                                : Number(
                                      singleAnalysis.demographics
                                        .consumer_spending_index,
                                    ) > 80
                                  ? "text-yellow-600"
                                  : "text-red-600"
                            }`}
                          >
                            {Number(
                              singleAnalysis.demographics
                                .consumer_spending_index,
                            ).toFixed(0)}
                          </span>
                        </div>
                      )}
                      {singleAnalysis.demographics?.foot_traffic_multiplier && (
                        <div className="data-row">
                          <span className="data-label">
                            Traffic Multiplier:
                          </span>
                          <span className="data-value text-blue-600">
                            {Number(
                              singleAnalysis.demographics
                                .foot_traffic_multiplier,
                            ).toFixed(2)}
                            x
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Spending Categories */}
                    {singleAnalysis.demographics?.spending_categories &&
                      typeof singleAnalysis.demographics.spending_categories ===
                        "object" && (
                        <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
                          <h4 className="font-semibold text-gray-800 mb-3 text-sm flex items-center">
                            <span className="mr-2">🛍️</span>Top Spending
                            Categories
                          </h4>
                          <div className="space-y-2">
                            {Object.entries(
                              singleAnalysis.demographics.spending_categories,
                            )
                              .slice(0, 4)
                              .map(([category, amount]) => (
                                <div
                                  key={category}
                                  className="flex justify-between text-sm"
                                >
                                  <span className="text-gray-600 capitalize">
                                    {category.replace("_", " ")}:
                                  </span>
                                  <span className="font-semibold">
                                    {formatCurrency(Number(amount) || 0)}
                                  </span>
                                </div>
                              ))}
                          </div>
                        </div>
                      )}
                  </div>
                )}

                {/* Housing & Economic */}
                {(singleAnalysis.demographics?.average_home_value ||
                  singleAnalysis.demographics?.rent_burden_percentage ||
                  singleAnalysis.demographics?.commute_time_minutes) && (
                  <div className="corporate-sidebar-card p-6">
                    <div className="flex items-center mb-4">
                      <div className="corporate-icon-sm mr-3">🏠</div>
                      <h3 className="corporate-title text-lg">
                        Housing & Economy
                      </h3>
                    </div>
                    <div className="space-y-3">
                      {singleAnalysis.demographics?.average_home_value && (
                        <div className="data-row">
                          <span className="data-label">Med. Home Value:</span>
                          <span className="data-value text-blue-600">
                            {formatCurrency(
                              singleAnalysis.demographics.average_home_value,
                            )}
                          </span>
                        </div>
                      )}
                      {singleAnalysis.demographics?.rent_burden_percentage && (
                        <div className="data-row">
                          <span className="data-label">Rent Burden:</span>
                          <span
                            className={`data-value ${
                              Number(
                                singleAnalysis.demographics
                                  .rent_burden_percentage,
                              ) > 30
                                ? "text-red-600"
                                : "text-green-600"
                            }`}
                          >
                            {Number(
                              singleAnalysis.demographics
                                .rent_burden_percentage,
                            ).toFixed(1)}
                            %
                          </span>
                        </div>
                      )}
                      {singleAnalysis.demographics?.commute_time_minutes && (
                        <div className="data-row">
                          <span className="data-label">Avg Commute:</span>
                          <span className="data-value">
                            {Number(
                              singleAnalysis.demographics.commute_time_minutes,
                            ).toFixed(0)}{" "}
                            min
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Income Distribution */}
              {singleAnalysis.demographics?.household_income_distribution &&
                typeof singleAnalysis.demographics
                  .household_income_distribution === "object" && (
                  <div className="mt-8 corporate-sidebar-card p-6">
                    <div className="flex items-center mb-6">
                      <div className="corporate-icon-sm mr-3">📊</div>
                      <h3 className="corporate-title text-lg">
                        Household Income Distribution
                      </h3>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {Object.entries(
                        singleAnalysis.demographics
                          .household_income_distribution,
                      )
                        .slice(0, 8)
                        .map(([bracket, data]) => (
                          <div
                            key={bracket}
                            className="text-center p-3 bg-gray-50 rounded-lg border"
                          >
                            <div className="text-xs text-gray-600 mb-2 font-medium capitalize">
                              {bracket.replace("_", " ").replace("k", "K")}
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                              <div
                                className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full transition-all duration-500"
                                style={{
                                  width: `${Math.min((data?.percentage || 0) * 3, 100)}%`,
                                }}
                              ></div>
                            </div>
                            <div className="font-bold text-sm text-blue-600">
                              {(data?.percentage || 0).toFixed(1)}%
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
