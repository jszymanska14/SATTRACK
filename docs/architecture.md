%% ─────────────────────────────────────────────────────────────────
%% PASTE INTO mermaid.live  —  only the diagram code, nothing else
%% ─────────────────────────────────────────────────────────────────

%% == DIAGRAM 1: Sequence diagram (Figure 2.9) ==========================

sequenceDiagram
    actor User
    participant Browser
    participant Django as Django Server
    participant Skyfield as Skyfield SGP4
    participant Shapely as Shapely / PyProj
    participant N2YO as N2YO API
    participant Spectator as Spectator.earth API
    participant WeatherAPI as WeatherAPI.com
    participant DB as PostgreSQL

    User->>Browser: (1) Draw area on map,<br/>select date & time (UTC)
    Browser->>Django: (2) POST /event/<br/>{ area_geojson, date, time }
    Django->>DB: Save Event record

    loop For each optical satellite<br/>(Sentinel-2A/B, Landsat 8/9)
        Django->>N2YO: (3) GET /tle/{norad_id}
        N2YO-->>Django: TLE line1 + line2
        Django->>Skyfield: (4) Propagate trajectory<br/>+/- 3 days, 5-min steps
        Skyfield-->>Django: List of positions<br/>{ lat, lon, alt, timestamp }
        Django->>Shapely: (5) Filter positions within<br/>sensor footprint of area
        Shapely-->>Django: Filtered overpass positions
    end

    Django->>Spectator: (6) GET /overpass/<br/>{ bbox, satellites, days }
    Spectator-->>Django: Overpasses with<br/>acquisition status<br/>(imaging / no_image / unknown)

    Django->>WeatherAPI: (7) GET /forecast.json<br/>?q={centroid_lat},{centroid_lon}
    WeatherAPI-->>Django: Forecast data<br/>{ visibility, rain_chance, wind_kph }

    Note over Django: (8) Compute weather score (0-100)<br/>per overpass, sort by proximity<br/>to user-selected date

    Django->>Browser: (9) Render HTML response<br/>{ map markers, Spectator table,<br/>pass analysis, recommendations }
    Browser->>User: (10) Display interactive results page<br/>with Leaflet map and data tables


%% == DIAGRAM 2: Architecture flowchart (Figure 2.8) ===================

flowchart TB
    classDef client   fill:#1e3a5f,stroke:#00d4ff,color:#e0f4ff
    classDef app      fill:#1a2e1a,stroke:#4ade80,color:#dcfce7
    classDef data     fill:#3b1f1f,stroke:#f87171,color:#fee2e2
    classDef external fill:#2d2540,stroke:#a78bfa,color:#ede9fe

    subgraph CLIENT["CLIENT TIER — Web Browser"]
        direction LR
        L["Leaflet.js\nInteractive Map"]:::client
        LD["Leaflet.Draw\nArea Drawing Tool"]:::client
        FC["FullCalendar.js\nObservation Calendar"]:::client
        BS["Bootstrap + CSS3\nResponsive UI"]:::client
    end

    subgraph APP["APPLICATION TIER — Django Server (Python 3.10)"]
        direction TB

        subgraph VIEWS["Views & URL Router"]
            V1["home /\nArea selection form"]:::app
            V2["event/id/\nSatellite analysis"]:::app
            V3["weather/\nWeather panel"]:::app
            V4["profile/ | calendar/\nUser panel & calendar"]:::app
        end

        subgraph ENGINE["Core Engine"]
            SKY["Skyfield\nSGP4/SDP4 Propagator\n+/- 3-day trajectory"]:::app
            CALC["SatelliteTrajectoryCalculator\nFilter by footprint"]:::app
            WX["Weather Analysis\nFunctions — Score 0-100"]:::app
        end

        subgraph CLIENTS["External API Clients"]
            N2YO_C["N2YOClient\nTLE fetch"]:::app
            SPEC_C["SpectatorClient\nOverpasses + acquisition"]:::app
            WX_C["WeatherAPI Client\nForecast fetch"]:::app
        end

        subgraph MODELS["Django ORM Models"]
            M1["UserAccountModel\nemail / username / password"]:::app
            M2["Event\ntimestamp / area_geojson / satellite_key"]:::app
            M3["Observation\nlat / lon / date / time / satellite_name"]:::app
        end
    end

    subgraph DATA["DATA TIER — PostgreSQL Database"]
        direction LR
        DB1[("sat_track_useraccountmodel")]:::data
        DB2[("sat_track_event")]:::data
        DB3[("sat_track_observation")]:::data
    end

    subgraph EXT["External Services"]
        direction LR
        CT["CelesTrak\nTLE Repository"]:::external
        N2YO_S["N2YO\nREST API v1"]:::external
        SPEC_S["Spectator.earth\nOverpass API"]:::external
        WX_S["WeatherAPI.com\nForecast API"]:::external
    end

    L -->|"GeoJSON POST /event/"| V2
    LD -->|"GeoJSON POST /event/"| V2
    FC -->|"GET /api/calendar-events/"| V4
    BS --- V1
    BS --- V3
    BS --- V4

    V2 --> CALC
    CALC --> SKY
    CALC --> WX
    V3 --> WX_C

    SKY --> N2YO_C
    V2 --> SPEC_C
    WX --> WX_C

    N2YO_C -->|"GET /tle/id"| N2YO_S
    N2YO_S -.->|"TLE source"| CT
    SPEC_C -->|"GET /overpass/"| SPEC_S
    WX_C -->|"GET /forecast.json"| WX_S

    V1 -->|"save Event"| M2
    V4 -->|"CRUD Observation"| M3
    V4 -->|"read User"| M1

    M1 --- DB1
    M2 --- DB2
    M3 --- DB3
