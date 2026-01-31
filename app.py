"""
HDL Workshop Capacity Board
===========================
A production-ready Streamlit dashboard for visualizing Cin7 Omni Sales Orders
as workshop jobs with capacity tracking and visual status indicators.

Author: HDL Engineering
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import time
import pytz

# Hardware Direct Theme
from hd_theme import apply_hd_theme, add_logo, metric_card, badge

# =============================================================================
# CONFIGURATION
# =============================================================================

# Hardware Direct Theme Colors
HDL_THEME = {
    "primary": "#2B2B2B",      # Dark gray (Hardware Direct)
    "accent": "#F47920",       # Hardware Direct orange
    "background": "#F5F7FA",   # Light gray background
    "card": "#FFFFFF",         # White cards
    "overdue": "#DC3545",      # Red for overdue
    "dueSoon": "#FFC107",      # Amber for due soon
    "ok": "#28A745",           # Green for on track
    "noDate": "#6C757D",       # Gray for no date
    "text": "#212529",         # Dark text
    "textLight": "#6C757D",    # Light text
}

# Stages we WANT to see (jobs in progress)
# Once "Fully Dispatched" - job is complete and removed from board
ACTIVE_STAGES = ['New', 'Processing', 'Job Complete']

# Stages to exclude (completed/cancelled work)
ACTIVE_EXCLUDED_STAGES = [
    'Fully Dispatched', 'Dispatched', 'Cancelled', 'Declined',
    'To Call', 'To Collect', 'Awaiting PO', 'Awaiting Payment',
    'Release To Pick', 'Partially Picked', 'Fully Picked',
    'Fully Picked - Hold', 'On Hold', 'Ready to Invoice',
    'Release To Pick - WMS', 'Ready To Pack - WMS'
]

# Due soon threshold (days)
DUE_SOON_DAYS = 7

# Upcoming days for optional filter
UPCOMING_DAYS = 30

# Timezone for display
TIMEZONE_DISPLAY = 'Pacific/Auckland'

# Distribution Branch filter - only show orders for this distribution branch
# Using ID is more reliable than name matching
DISTRIBUTION_BRANCH_ID = 6877  # Locksmiths
DISTRIBUTION_BRANCH_NAME = "Locksmiths"  # For display only

# API Configuration
API_TIMEOUT = 30
API_MAX_RETRIES = 3
API_RETRY_DELAY = 1.0
DEBUG_MODE = False  # Set to True to show API debug info in sidebar

# Fields to request from Sales Orders
SALES_ORDER_FIELDS = [
    "Id", "Reference", "ProjectName", "Company",
    "CreatedDate", "ModifiedDate",
    "Stage", "Status", "BranchId",
    "EstimatedDeliveryDate", "DispatchedDate",
    "IsVoid", "LineItems",
    "DistributionBranchId", "DistributionBranch"
]

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Workshop Capacity Board | Hardware Direct",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply Hardware Direct theme
apply_hd_theme()

# Add logo to sidebar
try:
    add_logo(logo_path="Logos-01.jpg", text="Hardware Direct", subtitle="Workshop Capacity Board")
except:
    add_logo(text="Hardware Direct", subtitle="Workshop Capacity Board")

# =============================================================================
# CUSTOM CSS
# =============================================================================

def inject_custom_css():
    """Inject custom CSS for the dashboard styling."""
    st.markdown(f"""
    <style>
        /* Main app styling */
        .stApp {{
            background-color: {HDL_THEME['background']};
        }}

        /* Header bar */
        .header-bar {{
            background: linear-gradient(135deg, {HDL_THEME['primary']} 0%, #2C4F7C 100%);
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        }}

        .header-title {{
            color: white;
            font-size: 2rem;
            font-weight: 700;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .header-subtitle {{
            color: rgba(255,255,255,0.8);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }}

        /* KPI Cards */
        .kpi-container {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }}

        .kpi-card {{
            background: {HDL_THEME['card']};
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            flex: 1;
            min-width: 150px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid {HDL_THEME['accent']};
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .kpi-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }}

        .kpi-value {{
            font-size: 2rem;
            font-weight: 700;
            color: {HDL_THEME['primary']};
            line-height: 1;
        }}

        .kpi-label {{
            font-size: 0.85rem;
            color: {HDL_THEME['textLight']};
            margin-top: 0.25rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .kpi-card.overdue {{
            border-left-color: {HDL_THEME['overdue']};
        }}
        .kpi-card.overdue .kpi-value {{
            color: {HDL_THEME['overdue']};
        }}

        .kpi-card.due-soon {{
            border-left-color: {HDL_THEME['dueSoon']};
        }}
        .kpi-card.due-soon .kpi-value {{
            color: {HDL_THEME['dueSoon']};
        }}

        /* Board columns */
        .board-column {{
            background: {HDL_THEME['card']};
            border-radius: 12px;
            padding: 1rem;
            height: 100%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}

        .column-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 0.75rem;
            margin-bottom: 0.75rem;
            border-bottom: 2px solid {HDL_THEME['background']};
        }}

        .column-title {{
            font-weight: 600;
            font-size: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .column-count {{
            background: {HDL_THEME['background']};
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .column-overdue .column-title {{
            color: {HDL_THEME['overdue']};
        }}
        .column-overdue .column-count {{
            background: {HDL_THEME['overdue']};
            color: white;
        }}

        .column-due-soon .column-title {{
            color: {HDL_THEME['dueSoon']};
        }}
        .column-due-soon .column-count {{
            background: {HDL_THEME['dueSoon']};
            color: {HDL_THEME['text']};
        }}

        .column-on-track .column-title {{
            color: {HDL_THEME['ok']};
        }}
        .column-on-track .column-count {{
            background: {HDL_THEME['ok']};
            color: white;
        }}

        .column-no-date .column-title {{
            color: {HDL_THEME['noDate']};
        }}
        .column-no-date .column-count {{
            background: {HDL_THEME['noDate']};
            color: white;
        }}

        /* Currently Working On section */
        .working-on-section {{
            background: linear-gradient(135deg, {HDL_THEME['primary']} 0%, #2C4F7C 100%);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
        }}

        .working-on-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }}

        .working-on-title {{
            color: white;
            font-weight: 600;
            font-size: 1.1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .working-on-count {{
            background: {HDL_THEME['accent']};
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .working-on-cards {{
            display: flex;
            gap: 1rem;
            overflow-x: auto;
            padding-bottom: 0.5rem;
        }}

        .working-on-cards::-webkit-scrollbar {{
            height: 6px;
        }}

        .working-on-cards::-webkit-scrollbar-track {{
            background: rgba(255,255,255,0.2);
            border-radius: 3px;
        }}

        .working-on-cards::-webkit-scrollbar-thumb {{
            background: rgba(255,255,255,0.5);
            border-radius: 3px;
        }}

        .working-on-cards .job-card {{
            flex: 0 0 280px;
            margin-bottom: 0;
        }}

        /* Job cards */
        .job-card {{
            background: {HDL_THEME['card']};
            border: 1px solid #E9ECEF;
            border-radius: 8px;
            padding: 0.875rem;
            margin-bottom: 0.75rem;
            transition: transform 0.15s, box-shadow 0.15s;
            cursor: pointer;
        }}

        .job-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}

        .job-card.overdue {{
            border-left: 4px solid {HDL_THEME['overdue']};
        }}

        .job-card.due-soon {{
            border-left: 4px solid {HDL_THEME['dueSoon']};
        }}

        .job-card.on-track {{
            border-left: 4px solid {HDL_THEME['ok']};
        }}

        .job-card.no-date {{
            border-left: 4px solid {HDL_THEME['noDate']};
        }}

        .job-reference {{
            font-weight: 600;
            color: {HDL_THEME['primary']};
            font-size: 0.95rem;
            margin-bottom: 0.25rem;
        }}

        .job-project {{
            color: {HDL_THEME['text']};
            font-size: 0.85rem;
            margin-bottom: 0.25rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .job-company {{
            color: {HDL_THEME['textLight']};
            font-size: 0.8rem;
            margin-bottom: 0.5rem;
        }}

        .job-meta {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-bottom: 0.5rem;
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}

        .badge-overdue {{
            background: {HDL_THEME['overdue']};
            color: white;
        }}

        .badge-due-soon {{
            background: {HDL_THEME['dueSoon']};
            color: {HDL_THEME['text']};
        }}

        .badge-on-track {{
            background: {HDL_THEME['ok']};
            color: white;
        }}

        .badge-no-date {{
            background: {HDL_THEME['noDate']};
            color: white;
        }}

        .badge-size {{
            background: {HDL_THEME['primary']};
            color: white;
        }}

        .badge-stage {{
            background: #E9ECEF;
            color: {HDL_THEME['text']};
        }}

        .job-date {{
            font-size: 0.75rem;
            color: {HDL_THEME['textLight']};
            margin-top: 0.25rem;
        }}

        /* Workload bar */
        .workload-bar {{
            height: 4px;
            background: #E9ECEF;
            border-radius: 2px;
            margin-top: 0.5rem;
            overflow: hidden;
        }}

        .workload-fill {{
            height: 100%;
            background: linear-gradient(90deg, {HDL_THEME['accent']} 0%, {HDL_THEME['primary']} 100%);
            border-radius: 2px;
            transition: width 0.3s ease;
        }}

        /* Search and controls */
        .controls-row {{
            background: {HDL_THEME['card']};
            padding: 1rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}

        /* Scrollable card container */
        .cards-container {{
            max-height: 600px;
            overflow-y: auto;
            padding-right: 0.5rem;
        }}

        .cards-container::-webkit-scrollbar {{
            width: 6px;
        }}

        .cards-container::-webkit-scrollbar-track {{
            background: {HDL_THEME['background']};
            border-radius: 3px;
        }}

        .cards-container::-webkit-scrollbar-thumb {{
            background: #CED4DA;
            border-radius: 3px;
        }}

        .cards-container::-webkit-scrollbar-thumb:hover {{
            background: #ADB5BD;
        }}

        /* Warning/Info boxes */
        .info-box {{
            background: #E7F3FF;
            border: 1px solid #B8DAFF;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin-bottom: 1rem;
            font-size: 0.85rem;
            color: #004085;
        }}

        .warning-box {{
            background: #FFF3CD;
            border: 1px solid #FFEEBA;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin-bottom: 1rem;
            font-size: 0.85rem;
            color: #856404;
        }}

        /* Hide Streamlit branding */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}

        /* Adjust column gaps */
        .stColumns > div {{
            padding: 0 0.5rem;
        }}

        /* Button styling */
        .stButton > button {{
            background: {HDL_THEME['primary']};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            transition: background 0.2s;
        }}

        .stButton > button:hover {{
            background: #2C4F7C;
            color: white;
        }}
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# API FUNCTIONS
# =============================================================================

def get_api_credentials() -> tuple[str, str, str]:
    """Get API credentials from Streamlit secrets."""
    try:
        # Default to Cin7 Omni API base URL
        # Common options:
        #   Cin7 Omni: https://api.cin7.com/api/v1
        #   Cin7 Core (DEAR): https://inventory.dearsystems.com/ExternalApi/v2
        base_url = st.secrets.get("CIN7_API_BASE", "https://api.cin7.com/api/v1")
        username = st.secrets["CIN7_USERNAME"]
        api_key = st.secrets["CIN7_KEY"]
        return base_url, username, api_key
    except KeyError as e:
        st.error(f"""
        **API Credentials Missing**

        Please configure your Streamlit secrets with the following keys:
        - `CIN7_USERNAME`: Your Cin7 API username (Account ID for Cin7 Core)
        - `CIN7_KEY`: Your Cin7 API key (Application Key for Cin7 Core)
        - `CIN7_API_BASE` (optional): API base URL

        **Common base URLs:**
        - Cin7 Omni: `https://api.cin7.com/api/v1`
        - Cin7 Core (DEAR): `https://inventory.dearsystems.com/ExternalApi/v2`

        Missing key: {e}
        """)
        st.stop()


def request_json(path: str, params: Optional[Dict] = None, suppress_error: bool = False) -> Any:
    """
    Make an authenticated request to the Cin7 API with retry logic.

    Args:
        path: API endpoint path (e.g., "/SalesOrders")
        params: Query parameters
        suppress_error: If True, don't show error in UI (for fallback attempts)

    Returns:
        Parsed JSON response
    """
    base_url, username, api_key = get_api_credentials()

    # Normalize URL: remove trailing slash from base, ensure path starts with /
    base_url = base_url.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path

    url = f"{base_url}{path}"
    auth = HTTPBasicAuth(username, api_key)

    if DEBUG_MODE:
        st.sidebar.markdown("### 🔧 API Debug")
        st.sidebar.code(f"URL: {url}\nParams: {params}", language="text")

    last_error = None
    for attempt in range(API_MAX_RETRIES):
        try:
            response = requests.get(
                url,
                params=params,
                auth=auth,
                timeout=API_TIMEOUT,
                headers={"Accept": "application/json"}
            )

            if DEBUG_MODE:
                st.sidebar.text(f"Status: {response.status_code}")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                st.error("**Authentication Failed**: Invalid API credentials. Please check your CIN7_USERNAME and CIN7_KEY.")
                st.stop()
            elif response.status_code == 403:
                st.error("**Access Denied**: Your API credentials don't have permission to access this resource.")
                st.stop()
            elif response.status_code == 429:
                # Rate limited - wait and retry
                wait_time = API_RETRY_DELAY * (attempt + 1) * 2
                time.sleep(wait_time)
                continue
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:500]}"
                if DEBUG_MODE:
                    st.sidebar.error(f"Response: {response.text[:500]}")

        except requests.exceptions.Timeout:
            last_error = "Request timed out. The API may be slow or unavailable."
        except requests.exceptions.ConnectionError:
            last_error = "Could not connect to the Cin7 API. Please check your network connection."
        except requests.exceptions.RequestException as e:
            last_error = f"Request failed: {str(e)}"

        # Wait before retry
        if attempt < API_MAX_RETRIES - 1:
            time.sleep(API_RETRY_DELAY * (attempt + 1))

    if not suppress_error:
        st.error(f"**API Error** after {API_MAX_RETRIES} attempts: {last_error}")
    return None


def build_where_clause(excluded_stages: List[str]) -> str:
    """
    Build the where clause for the Cin7 API query.

    Note: IsVoid is NOT a valid filter field in Cin7 Omni API.
    We filter void orders and Distribution Branch in Python after fetching.

    Args:
        excluded_stages: List of stages to exclude

    Returns:
        Where clause string
    """
    conditions = []

    # Add stage exclusions
    for stage in excluded_stages:
        conditions.append(f"Stage<>'{stage}'")

    return " AND ".join(conditions) if conditions else ""


@st.cache_data(ttl=300, show_spinner=False)
def fetch_sales_orders(excluded_stages: tuple) -> pd.DataFrame:
    """
    Fetch all active sales orders filtered by Distribution Branch.

    Args:
        excluded_stages: Tuple of stages to exclude (tuple for caching)

    Returns:
        DataFrame with sales order data
    """
    fields = ",".join(SALES_ORDER_FIELDS)
    where = build_where_clause(list(excluded_stages))
    order = "EstimatedDeliveryDate ASC, CreatedDate ASC"

    all_orders = []
    page = 1
    rows_per_page = 250

    while True:
        params = {
            "fields": fields,
            "order": order,
            "page": page,
            "rows": rows_per_page
        }

        # Only add where clause if not empty
        if where:
            params["where"] = where

        response = request_json("/SalesOrders", params)

        if response is None:
            break

        # Handle different response formats
        if isinstance(response, list):
            orders = response
        elif isinstance(response, dict):
            orders = response.get("data", response.get("Data", []))
            if not isinstance(orders, list):
                orders = [response] if response.get("Id") else []
        else:
            break

        if not orders:
            break

        all_orders.extend(orders)

        # Check if we got fewer than requested (last page)
        if len(orders) < rows_per_page:
            break

        page += 1

        # Safety limit
        if page > 100:
            st.warning("Reached maximum page limit (100). Some orders may not be shown.")
            break

    if DEBUG_MODE:
        st.sidebar.markdown(f"### 📊 API Results")
        st.sidebar.text(f"Total orders fetched: {len(all_orders)}")
        if all_orders:
            # Show sample of distribution branches found
            dist_branches = set()
            stages_found = set()
            for o in all_orders[:100]:  # Sample first 100
                db = o.get("DistributionBranch") or o.get("distributionBranch") or "None"
                dist_branches.add(db)
                stages_found.add(o.get("Stage", "Unknown"))
            st.sidebar.text(f"Dist Branches: {dist_branches}")
            st.sidebar.text(f"Stages: {stages_found}")

    if not all_orders:
        return pd.DataFrame()

    return process_orders_dataframe(all_orders)


def process_orders_dataframe(orders: List[Dict]) -> pd.DataFrame:
    """
    Process raw order data into a structured DataFrame.

    Args:
        orders: List of order dictionaries from API

    Returns:
        Processed DataFrame
    """
    tz = pytz.timezone(TIMEZONE_DISPLAY)
    today = datetime.now(tz).date()

    processed = []
    line_items_available = False

    for order in orders:
        # Skip void orders (filtered in Python since IsVoid isn't queryable in API)
        is_void = order.get("IsVoid") or order.get("isVoid") or False
        if is_void:
            continue

        # Filter by Distribution Branch ID (more reliable than name)
        dist_branch_id = order.get("DistributionBranchId") or order.get("distributionBranchId")
        if DISTRIBUTION_BRANCH_ID:
            if dist_branch_id != DISTRIBUTION_BRANCH_ID:
                continue

        # Debug: Show first matching order's raw data (all keys)
        if DEBUG_MODE and len(processed) == 0:
            st.sidebar.markdown("### 🔍 First Matching Order (Raw)")
            st.sidebar.json(order)

        # Helper to get field value (handles both camelCase and PascalCase)
        def get_field(field_name):
            # Try PascalCase first, then camelCase
            return order.get(field_name) or order.get(field_name[0].lower() + field_name[1:])

        # Parse dates
        created_date = parse_date(get_field("CreatedDate"))
        modified_date = parse_date(get_field("ModifiedDate"))
        estimated_delivery = parse_date(get_field("EstimatedDeliveryDate"))
        dispatched_date = parse_date(get_field("DispatchedDate"))

        # Calculate line items metrics
        line_items = get_field("LineItems") or []
        if line_items is None:
            line_items = []

        if line_items:
            line_items_available = True

        line_count = len(line_items) if line_items else 0
        qty_total = 0

        for item in (line_items or []):
            qty = item.get("Qty") or item.get("qty") or item.get("UomQtyOrdered") or item.get("uomQtyOrdered") or 0
            try:
                qty_total += float(qty)
            except (TypeError, ValueError):
                pass

        # Determine size bucket
        if line_count < 10:
            size_bucket = "S"
        elif line_count < 30:
            size_bucket = "M"
        else:
            size_bucket = "L"

        # Calculate workload score
        workload_score = line_count + (qty_total / 10.0)

        # Determine status flags
        is_overdue = False
        is_due_soon = False
        is_on_track = False
        days_overdue = None

        stage = get_field("Stage") or ""
        is_dispatched = stage == "Dispatched" or dispatched_date is not None

        if estimated_delivery and not is_dispatched:
            est_date = estimated_delivery.date() if hasattr(estimated_delivery, 'date') else estimated_delivery
            days_until_due = (est_date - today).days

            if days_until_due < 0:
                is_overdue = True
                days_overdue = abs(days_until_due)
            elif days_until_due <= DUE_SOON_DAYS:
                is_due_soon = True
            else:
                is_on_track = True

        processed.append({
            "Id": get_field("Id"),
            "Reference": get_field("Reference") or "",
            "ProjectName": get_field("ProjectName") or "",
            "Company": get_field("Company") or "",
            "CreatedDate": created_date,
            "ModifiedDate": modified_date,
            "Stage": stage,
            "Status": get_field("Status") or "",
            "BranchId": get_field("BranchId"),
            "EstimatedDeliveryDate": estimated_delivery,
            "DispatchedDate": dispatched_date,
            "LineCount": line_count,
            "QtyTotal": qty_total,
            "SizeBucket": size_bucket,
            "WorkloadScore": workload_score,
            "IsOverdue": is_overdue,
            "IsDueSoon": is_due_soon,
            "IsOnTrack": is_on_track,
            "DaysOverdue": days_overdue,
            "HasLineItems": bool(line_items)
        })

    df = pd.DataFrame(processed)

    # Store metadata for later use
    if not df.empty:
        df.attrs["line_items_available"] = line_items_available

    return df


def parse_date(date_value: Any) -> Optional[datetime]:
    """
    Parse various date formats into datetime.

    Args:
        date_value: Date string or value from API

    Returns:
        Parsed datetime or None
    """
    if date_value is None:
        return None

    if isinstance(date_value, datetime):
        return date_value

    if not isinstance(date_value, str):
        return None

    date_formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_value.replace("+00:00", "").replace("Z", ""), fmt.replace("Z", ""))
        except ValueError:
            continue

    return None


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_header():
    """Render the main header bar."""
    tz = pytz.timezone(TIMEZONE_DISPLAY)
    now = datetime.now(tz)

    st.markdown(f"""
    <div class="header-bar">
        <h1 class="header-title">
            🔧 HDL {DISTRIBUTION_BRANCH_NAME} Workshop Board
        </h1>
        <div class="header-subtitle">
            Last updated: {now.strftime('%d %b %Y %H:%M %Z')}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_cards(df: pd.DataFrame):
    """Render the KPI metric cards."""
    if df.empty:
        total_jobs = 0
        overdue_count = 0
        due_soon_count = 0
        on_track_count = 0
    else:
        total_jobs = len(df)
        overdue_count = df["IsOverdue"].sum()
        due_soon_count = df["IsDueSoon"].sum()
        on_track_count = df["IsOnTrack"].sum()

    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-value">{total_jobs}</div>
            <div class="kpi-label">Active Jobs</div>
        </div>
        <div class="kpi-card overdue">
            <div class="kpi-value">{int(overdue_count)}</div>
            <div class="kpi-label">Overdue</div>
        </div>
        <div class="kpi-card due-soon">
            <div class="kpi-value">{int(due_soon_count)}</div>
            <div class="kpi-label">Due in {DUE_SOON_DAYS} Days</div>
        </div>
        <div class="kpi-card" style="border-left-color: {HDL_THEME['ok']};">
            <div class="kpi-value" style="color: {HDL_THEME['ok']};">{int(on_track_count)}</div>
            <div class="kpi-label">On Track</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_job_card(job: pd.Series) -> str:
    """
    Render a single job card as HTML.

    Args:
        job: Series containing job data

    Returns:
        HTML string for the card
    """
    # Determine card class and status badge
    if job["IsOverdue"]:
        card_class = "overdue"
        status_badge = f'<span class="badge badge-overdue">{job["DaysOverdue"]}d OVERDUE</span>'
    elif job["IsDueSoon"]:
        card_class = "due-soon"
        status_badge = '<span class="badge badge-due-soon">DUE SOON</span>'
    elif job["IsOnTrack"]:
        card_class = "on-track"
        status_badge = '<span class="badge badge-on-track">ON TRACK</span>'
    else:
        card_class = "no-date"
        status_badge = '<span class="badge badge-no-date">NO ETD</span>'

    # Stage badge
    stage = job["Stage"] or "Unknown"
    stage_badge = f'<span class="badge badge-stage">{stage}</span>'

    # Format dates
    due_date_str = ""
    if job["EstimatedDeliveryDate"]:
        due_dt = job["EstimatedDeliveryDate"]
        if hasattr(due_dt, 'strftime'):
            due_date_str = f'ETD: {due_dt.strftime("%d %b %Y")}'

    created_str = ""
    if job["CreatedDate"]:
        created_dt = job["CreatedDate"]
        if hasattr(created_dt, 'strftime'):
            created_str = f'Created: {created_dt.strftime("%d %b %Y")}'

    # Escape text content
    reference = str(job["Reference"] or "No Ref").replace("<", "&lt;").replace(">", "&gt;")
    project = str(job["ProjectName"] or "").replace("<", "&lt;").replace(">", "&gt;")
    company = str(job["Company"] or "").replace("<", "&lt;").replace(">", "&gt;")

    return f"""
    <div class="job-card {card_class}">
        <div class="job-reference">{reference}</div>
        <div class="job-project" title="{project}">{project if project else '—'}</div>
        <div class="job-company">{company if company else '—'}</div>
        <div class="job-meta">
            {status_badge}
            {stage_badge}
        </div>
        <div class="job-date">
            {due_date_str}
        </div>
        <div class="job-date">
            {created_str}
        </div>
    </div>
    """


def render_board_column(title: str, emoji: str, jobs_df: pd.DataFrame, column_class: str):
    """
    Render a single board column with job cards.

    Args:
        title: Column title
        emoji: Emoji icon for the column
        jobs_df: DataFrame of jobs for this column
        column_class: CSS class for styling
    """
    count = len(jobs_df)

    cards_html = ""
    for _, job in jobs_df.iterrows():
        cards_html += render_job_card(job)

    if not cards_html:
        cards_html = '<div style="color: #6C757D; text-align: center; padding: 2rem; font-size: 0.9rem;">No jobs</div>'

    st.markdown(f"""
    <div class="board-column">
        <div class="column-header {column_class}">
            <span class="column-title">{emoji} {title}</span>
            <span class="column-count">{count}</span>
        </div>
        <div class="cards-container">
            {cards_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_currently_working_on(df: pd.DataFrame):
    """Render the 'Currently Working On' section for Processing stage jobs."""
    processing_df = df[df["Stage"] == "Processing"]

    if processing_df.empty:
        return

    # Sort by ETD (overdue first, then due soon, then by date)
    processing_df = processing_df.sort_values(
        by=["IsOverdue", "IsDueSoon", "EstimatedDeliveryDate"],
        ascending=[False, False, True]
    )

    count = len(processing_df)

    # Build cards HTML
    cards_html = ""
    for _, job in processing_df.iterrows():
        cards_html += render_job_card(job)

    st.markdown(f"""
    <div class="working-on-section">
        <div class="working-on-header">
            <span class="working-on-title">
                🔨 Currently Working On
            </span>
            <span class="working-on-count">
                {count}
            </span>
        </div>
        <div class="working-on-cards">
            {cards_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_board(df: pd.DataFrame):
    """Render the main board with Currently Working On section and four columns."""
    if df.empty:
        st.info("No active jobs found for Locksmiths workshop.")
        return

    # Render "Currently Working On" section first (Processing stage jobs)
    render_currently_working_on(df)

    # For the main columns, exclude Processing jobs (they're shown above)
    non_processing_df = df[df["Stage"] != "Processing"]

    # Split data into categories
    overdue_df = non_processing_df[non_processing_df["IsOverdue"]].sort_values("DaysOverdue", ascending=False)
    due_soon_df = non_processing_df[non_processing_df["IsDueSoon"]].sort_values("EstimatedDeliveryDate")
    on_track_df = non_processing_df[non_processing_df["IsOnTrack"]].sort_values("EstimatedDeliveryDate")
    no_date_df = non_processing_df[~non_processing_df["IsOverdue"] & ~non_processing_df["IsDueSoon"] & ~non_processing_df["IsOnTrack"]].sort_values("CreatedDate", ascending=False)

    # Render columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_board_column("Overdue", "🔴", overdue_df, "column-overdue")

    with col2:
        render_board_column(f"Due Soon ({DUE_SOON_DAYS}d)", "🟡", due_soon_df, "column-due-soon")

    with col3:
        render_board_column("On Track", "🟢", on_track_df, "column-on-track")

    with col4:
        render_board_column("No ETD", "⚪", no_date_df, "column-no-date")


def render_data_table(df: pd.DataFrame):
    """Render the data table with export functionality."""
    if df.empty:
        return

    st.markdown("### 📋 Detailed View")

    # Prepare display columns
    display_df = df[[
        "Reference", "ProjectName", "Company", "Stage",
        "CreatedDate", "EstimatedDeliveryDate", "DaysOverdue",
        "LineCount", "QtyTotal", "WorkloadScore", "SizeBucket"
    ]].copy()

    # Format dates for display
    for col in ["CreatedDate", "EstimatedDeliveryDate"]:
        display_df[col] = display_df[col].apply(
            lambda x: x.strftime("%d %b %Y") if pd.notna(x) and hasattr(x, 'strftime') else ""
        )

    # Rename columns for display
    display_df.columns = [
        "Reference", "Project", "Company", "Stage",
        "Created", "Due Date", "Days Overdue",
        "Lines", "Qty", "Workload", "Size"
    ]

    # Show dataframe
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # CSV download
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"workshop_jobs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def test_api_connection() -> bool:
    """Test API connection and show diagnostic info."""
    base_url, username, _ = get_api_credentials()

    st.sidebar.markdown("### 🔌 API Connection")
    st.sidebar.text(f"Base URL: {base_url}")
    st.sidebar.text(f"Username: {username[:4]}***")

    # Test with a simple request (try to get just 1 sales order)
    test_result = request_json("/SalesOrders", {"rows": 1}, suppress_error=True)

    if test_result is not None:
        st.sidebar.success("✅ API Connected")
        return True
    else:
        st.sidebar.error("❌ API Connection Failed")
        st.sidebar.markdown("""
        **Troubleshooting:**
        1. Check your `CIN7_API_BASE` URL
        2. Verify credentials in secrets.toml
        3. Common base URLs:
           - Omni: `https://api.cin7.com/api/v1`
           - Core: `https://inventory.dearsystems.com/ExternalApi/v2`
        """)
        return False


def main():
    """Main application entry point."""
    inject_custom_css()
    render_header()

    # Test API connection first (in debug mode)
    if DEBUG_MODE:
        if not test_api_connection():
            st.error("""
            **Cannot connect to Cin7 API**

            Please check:
            1. Your `CIN7_API_BASE` URL in `.streamlit/secrets.toml`
            2. Your `CIN7_USERNAME` and `CIN7_KEY` credentials

            See the sidebar for debug information.
            """)
            st.stop()

    # Show current filter info
    st.markdown(f"""
    <div class="info-box">
        📍 <strong>Distribution Branch:</strong> {DISTRIBUTION_BRANCH_NAME} &nbsp;|&nbsp;
        🕐 <strong>Timezone:</strong> {TIMEZONE_DISPLAY}
    </div>
    """, unsafe_allow_html=True)

    # Controls row
    st.markdown('<div class="controls-row">', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([3, 2, 3, 1])

    with col1:
        # Stages from Cin7 - only show workshop-relevant ones by default
        all_stages = [
            "New", "Processing", "Job Complete",  # Active workshop stages
            "To Call", "To Collect", "Awaiting PO", "Awaiting Payment",
            "Release To Pick", "Partially Picked", "Fully Picked",
            "Fully Picked - Hold", "On Hold", "Ready to Invoice",
            "Fully Dispatched", "Dispatched", "Cancelled"
        ]
        # Default to only active workshop stages
        default_stages = ACTIVE_STAGES.copy()

        selected_stages = st.multiselect(
            "📊 Stages",
            options=all_stages,
            default=default_stages
        )

    with col2:
        show_upcoming_only = st.toggle(
            f"Show only next {UPCOMING_DAYS} days",
            value=False
        )

    with col3:
        search_term = st.text_input(
            "🔍 Search",
            placeholder="Reference, Project, Company..."
        )

    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Determine excluded stages based on selection
    excluded_stages = [s for s in all_stages if s not in selected_stages]

    # Fetch data
    with st.spinner(f"Loading {DISTRIBUTION_BRANCH_NAME} workshop data..."):
        df = fetch_sales_orders(tuple(excluded_stages))

    # Apply search filter
    if search_term and not df.empty:
        search_lower = search_term.lower()
        mask = (
            df["Reference"].str.lower().str.contains(search_lower, na=False) |
            df["ProjectName"].str.lower().str.contains(search_lower, na=False) |
            df["Company"].str.lower().str.contains(search_lower, na=False)
        )
        df = df[mask]

    # Apply upcoming filter
    if show_upcoming_only and not df.empty:
        tz = pytz.timezone(TIMEZONE_DISPLAY)
        today = datetime.now(tz).date()
        cutoff = today + timedelta(days=UPCOMING_DAYS)

        mask = df["EstimatedDeliveryDate"].apply(
            lambda x: x is not None and hasattr(x, 'date') and x.date() <= cutoff
        ) | df["EstimatedDeliveryDate"].isna()
        df = df[mask]

    # Render KPIs
    render_kpi_cards(df)

    # Render board
    render_board(df)

    # Spacer
    st.markdown("<br>", unsafe_allow_html=True)

    # Render data table
    render_data_table(df)

    # Footer info
    st.markdown(f"""
    <div style="text-align: center; color: #6C757D; font-size: 0.8rem; margin-top: 2rem; padding: 1rem;">
        HDL Workshop Capacity Board v1.0 | Timezone: {TIMEZONE_DISPLAY} |
        Data cached for 5 minutes
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
