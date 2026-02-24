# Code Refactoring & Modularization Plan

The goal is to refactor `src/App.vue` into a clean, modular architecture using Vue 3 Composition API best practices (Composables + Components) without losing any functionality.

## 1. Directory Structure
We will create a `composables` directory for logic reuse and split `App.vue` into functional components.

```
src/
├── components/
│   ├── TheHeader.vue          # Top navigation bar (Weather, Time, Title)
│   ├── LeftSidebar.vue        # Stats cards, Filters, Ranking list
│   ├── RightSidebar.vue       # Analysis charts (Pie, Bar, Land Type)
│   ├── MapContainer.vue       # Leaflet map, Layer control, Legend
│   └── MineDetailModal.vue    # Popup with details and trend charts
├── composables/
│   ├── useMineData.js         # Data fetching (Mines, Stats, Indices) & Filtering logic
│   ├── useWeather.js          # Weather & AQI fetching
│   └── useChart.js            # ECharts initialization helper (optional, or keep in components)
└── App.vue                    # Main layout orchestrator
```

## 2. Refactoring Steps

### Phase 1: Logic Extraction (Composables)
*   **`useWeather.js`**: Extract `temperature`, `weatherIcon`, `airQuality`, `currentDate`, `currentTime` and related fetch/update logic.
*   **`useMineData.js`**: Extract:
    *   State: `allMinesData`, `filteredMinesData`, `mineTotal`, `overviewArea`, `treatedCount`, `untreatedCount`, `stats` lists.
    *   Actions: `loadData`, `applyFilters`, `resetFilters`, `searchMineById`, `fetchIndices`.
    *   Computed: `cityOptions`, `miningMethodOptions`.

### Phase 2: Component Extraction
*   **`TheHeader.vue`**: Move HTML/CSS for the header. Accepts weather/time props or uses `useWeather`.
*   **`LeftSidebar.vue`**: Move "Data Overview", "Filters", and "Ranking". Accepts stats and filter models as props/v-models.
*   **`RightSidebar.vue`**: Move "Analysis Statistics" (Pie/Bar charts).
*   **`MapContainer.vue`**: Encapsulate Leaflet logic.
    *   Props: `filteredMinesData` (to render markers).
    *   Events: `select-mine` (when a marker is clicked).
    *   Exposes: `flyToMine` (for search functionality).
*   **`MineDetailModal.vue`**: Move the popup logic.
    *   Props: `visible`, `mineData`, `indicesData`.
    *   Events: `close`, `tab-change`.

### Phase 3: Integration in `App.vue`
*   Reassemble the application using the new components.
*   Ensure state flows correctly between `useMineData` -> `App.vue` -> Components.

## 3. Verification
*   Check if map renders and markers appear.
*   Check if filters update the map.
*   Check if clicking a marker opens the modal with correct charts.
*   Check if weather and time update.

This approach ensures the code is maintainable, readable, and scalable.
