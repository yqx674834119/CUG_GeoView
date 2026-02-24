# UI/UX Enhancement & Functional Upgrade Plan

This plan aims to modernize the interface and integrate the `yunnan.kml` data source while preserving existing functionality.

## 1. Backend Data Integration (Node.js)
**Goal**: Switch data source from `dali.geojson` to `yunnan.kml` as requested.
*   **Dependencies**: Add `@mapbox/togeojson` and `@xmldom/xmldom` for KML parsing.
*   **Logic Update (`server.js`)**:
    *   Implement a KML-to-GeoJSON converter.
    *   Load `yunnan.kml` on startup.
    *   Map KML attributes (e.g., `FID_1`, `HFZLQK`, `KCFS`) to the standardized GeoJSON properties used by the frontend.
    *   Ensure compatibility with existing Excel data (NDVI/NDBI/NDWI) matching by `FID`.

## 2. Frontend UI/UX Overhaul (Vue.js)
**Goal**: Create a professional "Smart Ecological Monitoring Dashboard" style.

### A. Layout Restructuring
*   **Container**: Switch to a full-screen layout with semi-transparent floating sidebars.
*   **Left Panel (Control & Summary)**:
    *   Project Title & Live Weather (refined styling).
    *   **New**: Interactive Filters (City/County, Restoration Status, Mining Method).
    *   Key Metrics Cards (Total Area, Treated vs. Untreated).
*   **Right Panel (Analytics)**:
    *   **New**: Pie Chart for "Restoration Status Distribution" (Treated vs. Untreated vs. In Progress).
    *   Bar Chart for "Top Mining Methods" or "Land Types".
    *   "Top Restoration Projects" Ranking List.
*   **Center (Map)**:
    *   Maximize map area.
    *   Update Map Style (use a dark-themed base map or high-contrast satellite view).

### B. Visual Polish
*   **Theme**: "Dark Science/Tech" (Deep Blue `#0a1929` background, Cyan `#4ecdc4` accents, Glassmorphism effects).
*   **Typography**: Clean sans-serif fonts, better hierarchy, and readable data labels.
*   **Animations**: Smooth transitions for numbers and panel entry.

### C. Map Interactions
*   **Smart Markers**: Color-code map polygons/markers based on status (e.g., Green = Treated, Red = Untreated).
*   **Enhanced Popup**:
    *   A clean, tabbed modal for mine details.
    *   Integrate the Trend Charts (NDVI) directly into the detail view with better styling.
*   **Tooltips**: Hover effects showing Mine Name/ID.

## 3. Functionality Enhancements
*   **Filtering System**: Allow users to filter the map display by:
    *   **Region**: Filter by `SHI` (City) or `XIAN` (County).
    *   **Status**: Show only "Untreated" or "Treated" mines.
*   **Search**: Enhance search to query KML attributes (Mine Name, ID).

## 4. Execution Steps
1.  **Install Dependencies**: `@mapbox/togeojson`, `@xmldom/xmldom` (Backend).
2.  **Update Backend**: Modify `server.js` to parse KML and serve unified GeoJSON.
3.  **Refactor App.vue**:
    *   Update CSS for the new dark theme.
    *   Implement the Sidebar layout.
    *   Add Filter logic (computed properties).
    *   Update Chart components.
4.  **Verify**: Ensure data accuracy (matches KML) and UI responsiveness.
