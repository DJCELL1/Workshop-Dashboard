"""
HDL Workshop Capacity Board - TEST VERSION
============================================
Testing: Stage-based filtering using "Workshop -" prefixed stages
instead of Distribution Branch filtering to avoid stock issues.

Changes from app.py:
1. ACTIVE_STAGES now uses 'Workshop - New', 'Workshop - Processing', etc.
2. Removed Distribution Branch ID filtering (DISTRIBUTION_BRANCH_ID = None)
3. Filter now uses stage name prefix "Workshop -" instead of DistributionBranchId
4. All stage comparisons updated to use new Workshop stage names
5. all_stages list updated to include new Workshop stages
6. UI text updated to reflect stage-based filtering

Author: HDL Engineering
Version: 2.0.0-test
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
    "primary": "#11222c",      # Dark navy
    "secondary": "#1c5858",    # Dark teal
    "accent": "#f69000",       # HDL Orange
    "background": "#F5F7FA",   # Light gray background
    "card": "#FFFFFF",         # White cards
    "overdue": "#DC3545",      # Red for overdue
    "dueSoon": "#f6c624",      # Yellow/gold for due soon
    "ok": "#53b1b1",           # Teal for on track/positive
    "noDate": "#1c5858",       # Dark teal for no date
    "text": "#11222c",         # Dark navy text
    "textLight": "#1c5858",    # Teal light text
}

# Stages we WANT to see (workshop jobs in progress)
# Now using "Workshop -" prefixed stages to identify workshop orders
# This replaces Distribution Branch filtering and avoids stock issues
ACTIVE_STAGES = ['Workshop - New', 'Workshop - Processing', 'Workshop - Job Complete', 'Workshop - To Collect']

# Workshop stage prefix - used to identify workshop orders by stage name
WORKSHOP_STAGE_PREFIX = "Workshop - "

# Stages to exclude (completed/cancelled work)
ACTIVE_EXCLUDED_STAGES = [
    'Fully Dispatched', 'Dispatched', 'Cancelled', 'Declined',
    'To Call', 'Awaiting PO', 'Awaiting Payment',
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

# Auto-refresh settings
# The page will automatically refresh every X hours
AUTO_REFRESH_HOURS = 12  # Refresh every 12 hours

# Distribution Branch filter - DISABLED
# No longer filtering by Distribution Branch to avoid stock allocation issues
# Orders are now identified as workshop jobs by their "Workshop -" prefixed stage
DISTRIBUTION_BRANCH_ID = None  # Disabled - using stage-based filtering instead
DISTRIBUTION_BRANCH_NAME = "Workshop"  # For display only

# API Configuration
API_TIMEOUT = 30
API_MAX_RETRIES = 3
API_RETRY_DELAY = 1.0
DEBUG_MODE = False  # Set to True to show API debug info in sidebar

# Cin7 Web App URL for linking to Sales Orders
# Format: https://go.cin7.com/Cloud/TransactionEntry/TransactionEntry.aspx?idCustomerAppsLink={}&OrderId={ID}
CIN7_WEB_URL_BASE = "https://go.cin7.com/Cloud/TransactionEntry/TransactionEntry.aspx"
CIN7_CUSTOMER_APPS_LINK = "767392"  # Your Cin7 customer apps link ID

# Fields to request from Sales Orders
# Note: DistributionBranchId/DistributionBranch kept for reference but no longer used for filtering
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

# Hide sidebar completely
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
    [data-testid="stSidebarCollapsedControl"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

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
            background: linear-gradient(135deg, {HDL_THEME['accent']} 0%, {HDL_THEME['dueSoon']} 100%);
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(244, 121, 32, 0.3);
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }}

        .header-logo {{
            height: 60px;
            width: auto;
            border-radius: 8px;
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
            color: {HDL_THEME['accent']};
        }}
        .column-due-soon .column-count {{
            background: {HDL_THEME['accent']};
            color: white;
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

        /* Currently Working On section - Green */
        .working-on-section {{
            background: linear-gradient(135deg, {HDL_THEME['ok']} 0%, #3d8a8a 100%);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
        }}

        /* Overdue section - Red */
        .overdue-section {{
            background: linear-gradient(135deg, {HDL_THEME['overdue']} 0%, #C82333 100%);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
        }}

        .overdue-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }}

        .overdue-title {{
            color: white;
            font-weight: 600;
            font-size: 1.1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .overdue-count {{
            background: white;
            color: {HDL_THEME['overdue']};
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .overdue-cards {{
            display: flex;
            gap: 1rem;
            overflow-x: auto;
            padding-bottom: 0.5rem;
        }}

        .overdue-cards::-webkit-scrollbar {{
            height: 6px;
        }}

        .overdue-cards::-webkit-scrollbar-track {{
            background: rgba(255,255,255,0.2);
            border-radius: 3px;
        }}

        .overdue-cards::-webkit-scrollbar-thumb {{
            background: rgba(255,255,255,0.5);
            border-radius: 3px;
        }}

        .overdue-cards .job-card {{
            flex: 0 0 260px;
            margin-bottom: 0;
        }}

        /* Needs ETD section */
        .needs-etd-section {{
            background: linear-gradient(135deg, {HDL_THEME['noDate']} 0%, {HDL_THEME['primary']} 100%);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
        }}

        .needs-etd-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }}

        .needs-etd-title {{
            color: white;
            font-weight: 600;
            font-size: 1.1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .needs-etd-count {{
            background: {HDL_THEME['accent']};
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .needs-etd-cards {{
            display: flex;
            gap: 1rem;
            overflow-x: auto;
            padding-bottom: 0.5rem;
        }}

        .needs-etd-cards::-webkit-scrollbar {{
            height: 6px;
        }}

        .needs-etd-cards::-webkit-scrollbar-track {{
            background: rgba(255,255,255,0.2);
            border-radius: 3px;
        }}

        .needs-etd-cards::-webkit-scrollbar-thumb {{
            background: rgba(255,255,255,0.5);
            border-radius: 3px;
        }}

        .needs-etd-cards .job-card {{
            flex: 0 0 260px;
            margin-bottom: 0;
        }}

        /* To Collect section - Purple */
        .to-collect-section {{
            background: linear-gradient(135deg, #6f42c1 0%, #5a32a3 100%);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
        }}

        .to-collect-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }}

        .to-collect-title {{
            color: white;
            font-weight: 600;
            font-size: 1.1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .to-collect-count {{
            background: white;
            color: #6f42c1;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .to-collect-cards {{
            display: flex;
            gap: 1rem;
            overflow-x: auto;
            padding-bottom: 0.5rem;
        }}

        .to-collect-cards::-webkit-scrollbar {{
            height: 6px;
        }}

        .to-collect-cards::-webkit-scrollbar-track {{
            background: rgba(255,255,255,0.2);
            border-radius: 3px;
        }}

        .to-collect-cards::-webkit-scrollbar-thumb {{
            background: rgba(255,255,255,0.5);
            border-radius: 3px;
        }}

        .to-collect-cards .job-card {{
            flex: 0 0 260px;
            margin-bottom: 0;
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
            flex: 0 0 260px;
            margin-bottom: 0;
        }}

        /* Job card links */
        .job-card-link {{
            text-decoration: none;
            color: inherit;
            display: block;
        }}

        .job-card-link:hover {{
            text-decoration: none;
        }}

        /* Job cards - Fixed size for consistency */
        .job-card {{
            background: {HDL_THEME['card']};
            border: 1px solid #E9ECEF;
            border-radius: 8px;
            padding: 0.875rem;
            margin-bottom: 0.75rem;
            transition: transform 0.15s, box-shadow 0.15s;
            cursor: pointer;
            height: 160px;
            width: 260px;
            min-width: 260px;
            max-width: 260px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        .job-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-color: {HDL_THEME['accent']};
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
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex-shrink: 0;
        }}

        .job-project {{
            color: {HDL_THEME['text']};
            font-size: 0.85rem;
            margin-bottom: 0.25rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex-shrink: 0;
        }}

        .job-company {{
            color: {HDL_THEME['textLight']};
            font-size: 0.8rem;
            margin-bottom: 0.5rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex-shrink: 0;
        }}

        .job-meta {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: nowrap;
            margin-bottom: 0.5rem;
            flex-shrink: 0;
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

        .job-dates {{
            margin-top: auto;
            flex-shrink: 0;
        }}

        .job-date {{
            font-size: 0.75rem;
            color: {HDL_THEME['textLight']};
            margin-top: 0.15rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
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

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background: {HDL_THEME['card']};
            padding: 0.5rem;
            border-radius: 12px;
            margin-bottom: 1rem;
        }}

        .stTabs [data-baseweb="tab"] {{
            height: 50px;
            padding: 0 24px;
            background: transparent;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1rem;
            color: {HDL_THEME['textLight']};
        }}

        .stTabs [data-baseweb="tab"]:hover {{
            background: {HDL_THEME['background']};
            color: {HDL_THEME['primary']};
        }}

        .stTabs [aria-selected="true"] {{
            background: {HDL_THEME['accent']} !important;
            color: white !important;
        }}

        .stTabs [data-baseweb="tab-highlight"] {{
            display: none;
        }}

        .stTabs [data-baseweb="tab-border"] {{
            display: none;
        }}

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

        /* =====================================================
           TV VIEW STYLES - Optimized for 50" TV display
           Single screen, no scrolling, large readable text
           ===================================================== */

        /* TV Container - uses viewport height */
        .tv-container {{
            min-height: 85vh;
            display: flex;
            flex-direction: column;
            padding: 0.5rem;
        }}

        /* TV Header - compact */
        .tv-header {{
            background: linear-gradient(135deg, {HDL_THEME['primary']} 0%, {HDL_THEME['secondary']} 100%);
            padding: 0.75rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .tv-header-left {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .tv-logo {{
            height: 60px;
            width: auto;
            border-radius: 6px;
        }}

        .tv-title {{
            color: white;
            font-size: 2rem;
            font-weight: 700;
            margin: 0;
        }}

        .tv-time {{
            color: white;
            font-size: 2.5rem;
            font-weight: 700;
            text-align: right;
        }}

        .tv-date {{
            color: rgba(255,255,255,0.8);
            font-size: 1rem;
            text-align: right;
        }}

        /* TV KPI Cards - Row at top */
        .tv-kpi-container {{
            display: flex;
            gap: 1rem;
            margin-bottom: 0.75rem;
        }}

        .tv-kpi-card {{
            flex: 1;
            background: {HDL_THEME['card']};
            border-radius: 16px;
            padding: 1rem 1.5rem;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-bottom: 6px solid {HDL_THEME['accent']};
        }}

        .tv-kpi-card.overdue {{
            border-bottom-color: {HDL_THEME['overdue']};
        }}

        .tv-kpi-card.queue {{
            border-bottom-color: {HDL_THEME['accent']};
        }}

        .tv-kpi-card.workshop {{
            border-bottom-color: {HDL_THEME['ok']};
        }}

        .tv-kpi-card.to-collect {{
            border-bottom-color: #6f42c1;
        }}

        .tv-kpi-value {{
            font-size: 4rem;
            font-weight: 800;
            line-height: 1;
        }}

        .tv-kpi-card.overdue .tv-kpi-value {{
            color: {HDL_THEME['overdue']};
        }}

        .tv-kpi-card.queue .tv-kpi-value {{
            color: {HDL_THEME['accent']};
        }}

        .tv-kpi-card.workshop .tv-kpi-value {{
            color: {HDL_THEME['ok']};
        }}

        .tv-kpi-card.to-collect .tv-kpi-value {{
            color: #6f42c1;
        }}

        .tv-kpi-label {{
            font-size: 1.2rem;
            font-weight: 600;
            color: {HDL_THEME['primary']};
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 0.25rem;
        }}

        /* TV Board - 4 column grid layout */
        .tv-board {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.75rem;
            flex: 1;
            width: 100%;
            overflow: hidden;
        }}

        /* TV Section/Column */
        .tv-section {{
            border-radius: 16px;
            padding: 0.75rem;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            min-width: 0;
        }}

        .tv-section.overdue {{
            background: linear-gradient(135deg, {HDL_THEME['overdue']} 0%, #C82333 100%);
        }}

        .tv-section.workshop {{
            background: linear-gradient(135deg, {HDL_THEME['ok']} 0%, #3d8a8a 100%);
        }}

        .tv-section.to-collect {{
            background: linear-gradient(135deg, #6f42c1 0%, #5a32a3 100%);
        }}

        .tv-section.queue {{
            background: {HDL_THEME['accent']};
        }}

        .tv-section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            flex-shrink: 0;
        }}

        .tv-section-title {{
            color: white;
            font-size: 1.2rem;
            font-weight: 700;
            white-space: nowrap;
        }}

        .tv-section-count {{
            background: white;
            color: {HDL_THEME['primary']};
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 1.1rem;
            font-weight: 700;
        }}

        .tv-section.overdue .tv-section-count {{
            color: {HDL_THEME['overdue']};
        }}

        .tv-section.workshop .tv-section-count {{
            color: {HDL_THEME['ok']};
        }}

        .tv-section.queue .tv-section-count {{
            color: {HDL_THEME['accent']};
        }}

        .tv-section.to-collect .tv-section-count {{
            color: #6f42c1;
        }}

        /* TV Cards container - vertical stack */
        .tv-cards-column {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            overflow: hidden;
            flex: 1;
        }}

        /* TV Job Cards - Fill width, fixed height */
        .tv-job-card {{
            background: white;
            border-radius: 10px;
            padding: 0.6rem 0.75rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            height: 100px;
            min-height: 100px;
            max-height: 100px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            width: 100%;
            box-sizing: border-box;
        }}

        .tv-job-card.overdue {{
            border-left: 5px solid {HDL_THEME['overdue']};
        }}

        .tv-job-card.due-soon {{
            border-left: 5px solid {HDL_THEME['accent']};
        }}

        .tv-job-card.on-track {{
            border-left: 5px solid {HDL_THEME['ok']};
        }}

        .tv-job-reference {{
            font-size: 1.1rem;
            font-weight: 700;
            color: {HDL_THEME['primary']};
            margin-bottom: 0.15rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex-shrink: 0;
        }}

        .tv-job-project {{
            font-size: 0.95rem;
            font-weight: 600;
            color: {HDL_THEME['text']};
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex-shrink: 0;
        }}

        .tv-job-company {{
            font-size: 0.85rem;
            color: {HDL_THEME['textLight']};
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex-shrink: 0;
        }}

        .tv-job-date {{
            font-size: 0.8rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            display: inline-block;
            margin-top: auto;
            align-self: flex-start;
        }}

        .tv-job-date.overdue {{
            background: {HDL_THEME['overdue']};
            color: white;
        }}

        .tv-job-date.due-soon {{
            background: {HDL_THEME['dueSoon']};
            color: {HDL_THEME['primary']};
        }}

        .tv-job-date.on-track {{
            background: {HDL_THEME['ok']};
            color: white;
        }}

        /* TV Empty state */
        .tv-empty {{
            text-align: center;
            padding: 2rem;
            color: rgba(255,255,255,0.8);
            font-size: 1.3rem;
        }}

        /* More jobs indicator */
        .tv-more-jobs {{
            text-align: center;
            color: rgba(255,255,255,0.9);
            font-size: 1.1rem;
            font-weight: 600;
            padding: 0.5rem;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin-top: 0.5rem;
        }}

        /* Legacy horizontal scroll row - kept for compatibility */
        .tv-cards-row {{
            display: flex;
            gap: 1rem;
            overflow-x: auto;
            padding-bottom: 0.5rem;
        }}

        /* TV Empty state - legacy */
        .tv-empty-legacy {{
            text-align: center;
            padding: 2rem;
            color: rgba(255,255,255,0.8);
            font-size: 1.5rem;
        }}

        /* Auto-refresh indicator */
        .tv-refresh-indicator {{
            position: fixed;
            bottom: 1rem;
            right: 1rem;
            background: {HDL_THEME['primary']};
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 30px;
            font-size: 1rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}

    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# AUTO-REFRESH FUNCTIONS
# =============================================================================

def setup_auto_refresh():
    """
    Set up a meta refresh tag to reload the page after the configured interval.
    This is a simple browser-based refresh - no intermediate API calls.
    """
    # Convert hours to seconds for the meta refresh
    refresh_seconds = AUTO_REFRESH_HOURS * 60 * 60  # 12 hours = 43200 seconds
    st.markdown(
        f'<meta http-equiv="refresh" content="{refresh_seconds}">',
        unsafe_allow_html=True
    )


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
        st.sidebar.markdown("### API Debug")
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
    We filter void orders in Python after fetching.
    Workshop orders are now identified by their "Workshop -" prefixed stage names.

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
    Fetch all active sales orders filtered by Workshop stages.

    Orders are identified as workshop jobs by their "Workshop -" prefixed stage names,
    instead of by Distribution Branch. This avoids stock allocation issues.

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
        st.sidebar.markdown(f"### API Results")
        st.sidebar.text(f"Total orders fetched: {len(all_orders)}")
        if all_orders:
            # Show sample of stages found
            stages_found = set()
            for o in all_orders[:100]:  # Sample first 100
                stages_found.add(o.get("Stage", "Unknown"))
            st.sidebar.text(f"Stages: {stages_found}")

    if not all_orders:
        return pd.DataFrame()

    return process_orders_dataframe(all_orders)


def process_orders_dataframe(orders: List[Dict]) -> pd.DataFrame:
    """
    Process raw order data into a structured DataFrame.

    Filters orders by "Workshop -" prefixed stage names instead of Distribution Branch.

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

        # Filter by Workshop stage prefix instead of Distribution Branch
        # Only include orders whose stage starts with "Workshop - "
        stage = order.get("Stage") or order.get("stage") or ""
        if not stage.startswith(WORKSHOP_STAGE_PREFIX):
            continue

        # Debug: Show first matching order's raw data (all keys)
        if DEBUG_MODE and len(processed) == 0:
            st.sidebar.markdown("### First Matching Order (Raw)")
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
    """Render the main header bar with logo."""
    tz = pytz.timezone(TIMEZONE_DISPLAY)
    now = datetime.now(tz)

    # Try to load the logo, use a placeholder if not found
    import base64
    import os

    logo_html = ""
    logo_path = "Logos-01.jpg"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_data = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/jpeg;base64,{logo_data}" class="header-logo" alt="Hardware Direct">'

    st.markdown(f"""
    <div class="header-bar">
        {logo_html}
        <div>
            <h1 class="header-title">
                HDL Workshop Board
            </h1>
            <div class="header-subtitle">
                Last updated: {now.strftime('%d %b %Y %H:%M %Z')}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_cards(df: pd.DataFrame):
    """Render the KPI metric cards."""
    if df.empty:
        total_jobs = 0
        overdue_count = 0
        due_soon_count = 0
    else:
        total_jobs = len(df)
        overdue_count = df["IsOverdue"].sum()
        due_soon_count = df["IsDueSoon"].sum()

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

    # Stage badge - show shortened stage name (strip "Workshop - " prefix for cleaner display)
    stage = job["Stage"] or "Unknown"
    display_stage = stage.replace(WORKSHOP_STAGE_PREFIX, "") if stage.startswith(WORKSHOP_STAGE_PREFIX) else stage
    stage_badge = f'<span class="badge badge-stage">{display_stage}</span>'

    # Format dates (check for NaT values)
    due_date_str = ""
    due_dt = job["EstimatedDeliveryDate"]
    if pd.notna(due_dt) and hasattr(due_dt, 'strftime'):
        due_date_str = f'ETD: {due_dt.strftime("%d %b %Y")}'

    created_str = ""
    created_dt = job["CreatedDate"]
    if pd.notna(created_dt) and hasattr(created_dt, 'strftime'):
        created_str = f'Created: {created_dt.strftime("%d %b %Y")}'

    # Escape text content for HTML
    reference = str(job["Reference"] or "No Ref").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    project = str(job["ProjectName"] or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    company = str(job["Company"] or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    # Get the Sales Order ID for the link
    order_id = job["Id"]
    cin7_url = f"{CIN7_WEB_URL_BASE}?idCustomerAppsLink={CIN7_CUSTOMER_APPS_LINK}&OrderId={order_id}" if order_id else "#"

    # Build the card HTML as a clickable link
    card_html = f'<a href="{cin7_url}" target="_blank" class="job-card-link">'
    card_html += f'<div class="job-card {card_class}">'
    card_html += f'<div class="job-reference" title="{reference}">{reference}</div>'
    card_html += f'<div class="job-project" title="{project}">{project if project else "—"}</div>'
    card_html += f'<div class="job-company" title="{company}">{company if company else "—"}</div>'
    card_html += f'<div class="job-meta">{status_badge}{stage_badge}</div>'
    card_html += '<div class="job-dates">'
    if due_date_str:
        card_html += f'<div class="job-date">{due_date_str}</div>'
    if created_str:
        card_html += f'<div class="job-date">{created_str}</div>'
    card_html += '</div>'
    card_html += '</div>'
    card_html += '</a>'

    return card_html


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
    """Render the 'Currently Working On' section for Workshop - Processing stage jobs."""
    processing_df = df[df["Stage"] == "Workshop - Processing"]

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
                Currently in Workshop
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


def render_overdue(df: pd.DataFrame):
    """Render the 'Overdue' section for jobs past their ETD."""
    overdue_df = df[df["IsOverdue"]]

    if overdue_df.empty:
        return

    # Sort by days overdue (most overdue first)
    overdue_df = overdue_df.sort_values(by=["DaysOverdue"], ascending=False)

    count = len(overdue_df)

    # Build cards HTML
    cards_html = ""
    for _, job in overdue_df.iterrows():
        cards_html += render_job_card(job)

    st.markdown(f"""
    <div class="overdue-section">
        <div class="overdue-header">
            <span class="overdue-title">
                Overdue
            </span>
            <span class="overdue-count">
                {count}
            </span>
        </div>
        <div class="overdue-cards">
            {cards_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_needs_etd(df: pd.DataFrame):
    """Render the 'Needs ETD' section for jobs without an estimated delivery date."""
    # Jobs with no ETD are those that are not overdue, not due soon, and not on track
    no_etd_df = df[~df["IsOverdue"] & ~df["IsDueSoon"] & ~df["IsOnTrack"]]

    if no_etd_df.empty:
        return

    # Sort by created date (oldest first - they need attention)
    no_etd_df = no_etd_df.sort_values(by=["CreatedDate"], ascending=True)

    count = len(no_etd_df)

    # Build cards HTML
    cards_html = ""
    for _, job in no_etd_df.iterrows():
        cards_html += render_job_card(job)

    st.markdown(f"""
    <div class="needs-etd-section">
        <div class="needs-etd-header">
            <span class="needs-etd-title">
                Needs ETD
            </span>
            <span class="needs-etd-count">
                {count}
            </span>
        </div>
        <div class="needs-etd-cards">
            {cards_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_to_collect(df: pd.DataFrame):
    """Render the 'To Collect' section for jobs ready for customer pickup."""
    to_collect_df = df[df["Stage"] == "Workshop - To Collect"]

    if to_collect_df.empty:
        return

    # Sort by ETD (earliest first), then by created date
    to_collect_df = to_collect_df.sort_values(
        by=["EstimatedDeliveryDate", "CreatedDate"],
        ascending=[True, True]
    )

    count = len(to_collect_df)

    # Build cards HTML
    cards_html = ""
    for _, job in to_collect_df.iterrows():
        cards_html += render_job_card(job)

    st.markdown(f"""
    <div class="to-collect-section">
        <div class="to-collect-header">
            <span class="to-collect-title">
                To Collect
            </span>
            <span class="to-collect-count">
                {count}
            </span>
        </div>
        <div class="to-collect-cards">
            {cards_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_board(df: pd.DataFrame):
    """Render the main board with highlighted sections and two columns."""
    if df.empty:
        st.info("No active workshop jobs found. Orders need a 'Workshop -' prefixed stage to appear here.")
        return

    # Render "Currently in Workshop" section first - GREEN (Workshop - Processing stage jobs)
    render_currently_working_on(df)

    # Render "To Collect" section - PURPLE (jobs ready for customer pickup)
    render_to_collect(df)

    # Render "Overdue" section - RED (most urgent)
    render_overdue(df)

    # Render "Needs ETD" section - GRAY (jobs without estimated delivery dates)
    render_needs_etd(df)

    # For the main column, exclude Processing jobs, To Collect jobs, and Overdue jobs (shown in dedicated sections above)
    non_processing_df = df[(df["Stage"] != "Workshop - Processing") & (df["Stage"] != "Workshop - To Collect")]
    # Also exclude overdue (shown in red section above)
    non_processing_df = non_processing_df[~non_processing_df["IsOverdue"]]

    # Get due soon jobs
    due_soon_df = non_processing_df[non_processing_df["IsDueSoon"]].sort_values("EstimatedDeliveryDate")

    # Render single column for Jobs in Queue (due within 7 days)
    render_board_column("Jobs in Queue", "", due_soon_df, "column-due-soon")


# =============================================================================
# TV VIEW COMPONENTS
# =============================================================================

def render_tv_header():
    """Render the TV view header with logo, title and time - compact for TV."""
    tz = pytz.timezone(TIMEZONE_DISPLAY)
    now = datetime.now(tz)

    # Try to load the logo
    import base64
    import os

    logo_html = ""
    logo_path = "Logos-01.jpg"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_data = base64.b64encode(f.read()).decode()
        logo_html = '<img src="data:image/jpeg;base64,' + logo_data + '" class="tv-logo" alt="HDL">'

    time_str = now.strftime('%H:%M')
    date_str = now.strftime('%A, %d %b')

    header_html = '<div class="tv-header">'
    header_html += '<div class="tv-header-left">'
    header_html += logo_html
    header_html += '<h1 class="tv-title">Workshop Board</h1>'
    header_html += '</div>'
    header_html += '<div>'
    header_html += '<div class="tv-time">' + time_str + '</div>'
    header_html += '<div class="tv-date">' + date_str + '</div>'
    header_html += '</div>'
    header_html += '</div>'

    st.markdown(header_html, unsafe_allow_html=True)


def render_tv_kpi_cards(df: pd.DataFrame):
    """Render compact horizontal KPI cards for TV display."""
    if df.empty:
        overdue_count = 0
        queue_count = 0
        workshop_count = 0
        to_collect_count = 0
    else:
        overdue_count = int(df["IsOverdue"].sum())
        queue_count = int(df["IsDueSoon"].sum())
        workshop_count = int((df["Stage"] == "Workshop - Processing").sum())
        to_collect_count = int((df["Stage"] == "Workshop - To Collect").sum())

    st.markdown(f"""
    <div class="tv-kpi-container">
        <div class="tv-kpi-card overdue">
            <div class="tv-kpi-value">{overdue_count}</div>
            <div class="tv-kpi-label">OVERDUE</div>
        </div>
        <div class="tv-kpi-card workshop">
            <div class="tv-kpi-value">{workshop_count}</div>
            <div class="tv-kpi-label">IN WORKSHOP</div>
        </div>
        <div class="tv-kpi-card to-collect">
            <div class="tv-kpi-value">{to_collect_count}</div>
            <div class="tv-kpi-label">TO COLLECT</div>
        </div>
        <div class="tv-kpi-card queue">
            <div class="tv-kpi-value">{queue_count}</div>
            <div class="tv-kpi-label">IN QUEUE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_tv_job_card(job: pd.Series) -> str:
    """Render a single job card for TV display (larger text, no hover effects)."""
    import html

    # Determine card class and date styling
    if job["IsOverdue"]:
        card_class = "overdue"
        date_class = "overdue"
    elif job["IsDueSoon"]:
        card_class = "due-soon"
        date_class = "due-soon"
    else:
        card_class = "on-track"
        date_class = "on-track"

    # Format due date
    due_date_str = ""
    due_dt = job["EstimatedDeliveryDate"]
    if pd.notna(due_dt) and hasattr(due_dt, 'strftime'):
        due_date_str = due_dt.strftime("%d %b")
        if job["IsOverdue"]:
            days = int(job["DaysOverdue"])
            due_date_str = str(days) + "d OVERDUE"
        elif job["IsDueSoon"]:
            # Calculate days until due
            tz = pytz.timezone(TIMEZONE_DISPLAY)
            today = datetime.now(tz).date()
            if hasattr(due_dt, 'date'):
                days_until = (due_dt.date() - today).days
                due_date_str = "Due in " + str(days_until) + "d"

    # Escape ALL text content properly using html.escape
    reference = html.escape(str(job["Reference"] or "No Ref"))
    project = html.escape(str(job["ProjectName"] or ""))
    company = html.escape(str(job["Company"] or ""))

    # Build HTML using concatenation to avoid f-string issues
    card_html = '<div class="tv-job-card ' + card_class + '">'
    card_html += '<div class="tv-job-reference">' + reference + '</div>'
    card_html += '<div class="tv-job-project">' + (project if project else "—") + '</div>'
    card_html += '<div class="tv-job-company">' + (company if company else "—") + '</div>'
    card_html += '<div class="tv-job-date ' + date_class + '">' + due_date_str + '</div>'
    card_html += '</div>'

    return card_html


def render_tv_column_cards(jobs_df: pd.DataFrame, max_cards: int = 6) -> str:
    """Render job cards for a TV column, limiting to max_cards to fit screen."""
    if jobs_df.empty:
        return '<div class="tv-empty">No jobs</div>'

    cards_html = ""
    total_jobs = len(jobs_df)
    display_jobs = jobs_df.head(max_cards)

    for _, job in display_jobs.iterrows():
        cards_html += render_tv_job_card(job)

    # Show indicator if there are more jobs
    if total_jobs > max_cards:
        remaining = total_jobs - max_cards
        cards_html += '<div class="tv-more-jobs">+ ' + str(remaining) + ' more</div>'

    return cards_html


def render_tv_board(df: pd.DataFrame):
    """Render the full TV board as a 4-column grid layout for 50" TV."""
    # Get overdue jobs (most urgent)
    overdue_df = df[df["IsOverdue"]].sort_values("DaysOverdue", ascending=False) if not df.empty else pd.DataFrame()

    # Get jobs currently being worked on (Workshop - Processing stage)
    processing_df = df[df["Stage"] == "Workshop - Processing"].sort_values("EstimatedDeliveryDate") if not df.empty else pd.DataFrame()

    # Get jobs ready for customer pickup (Workshop - To Collect stage)
    to_collect_df = df[df["Stage"] == "Workshop - To Collect"].sort_values("EstimatedDeliveryDate") if not df.empty else pd.DataFrame()

    # Get jobs in queue (due soon, not overdue, not processing, not to collect)
    if not df.empty:
        non_special = df[(df["Stage"] != "Workshop - Processing") & (df["Stage"] != "Workshop - To Collect")]
        non_overdue = non_special[~non_special["IsOverdue"]]
        queue_df = non_overdue[non_overdue["IsDueSoon"]].sort_values("EstimatedDeliveryDate")
    else:
        queue_df = pd.DataFrame()

    # Build the 4-column grid
    # Show up to 6 cards per column - optimized for 50" TV with 4 columns
    overdue_cards = render_tv_column_cards(overdue_df, max_cards=6)
    workshop_cards = render_tv_column_cards(processing_df, max_cards=6)
    to_collect_cards = render_tv_column_cards(to_collect_df, max_cards=6)
    queue_cards = render_tv_column_cards(queue_df, max_cards=6)

    overdue_count = len(overdue_df)
    workshop_count = len(processing_df)
    to_collect_count = len(to_collect_df)
    queue_count = len(queue_df)

    st.markdown(f'''
    <div class="tv-board">
        <div class="tv-section overdue">
            <div class="tv-section-header">
                <span class="tv-section-title">OVERDUE</span>
                <span class="tv-section-count">{overdue_count}</span>
            </div>
            <div class="tv-cards-column">
                {overdue_cards}
            </div>
        </div>
        <div class="tv-section workshop">
            <div class="tv-section-header">
                <span class="tv-section-title">IN WORKSHOP</span>
                <span class="tv-section-count">{workshop_count}</span>
            </div>
            <div class="tv-cards-column">
                {workshop_cards}
            </div>
        </div>
        <div class="tv-section to-collect">
            <div class="tv-section-header">
                <span class="tv-section-title">TO COLLECT</span>
                <span class="tv-section-count">{to_collect_count}</span>
            </div>
            <div class="tv-cards-column">
                {to_collect_cards}
            </div>
        </div>
        <div class="tv-section queue">
            <div class="tv-section-header">
                <span class="tv-section-title">COMING UP</span>
                <span class="tv-section-count">{queue_count}</span>
            </div>
            <div class="tv-cards-column">
                {queue_cards}
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)


def render_tv_view(df: pd.DataFrame):
    """Main TV view render function optimized for 50" TV display.

    Designed for wall-mounted TV displays in the workshop.
    Uses large fonts and high contrast for readability from a distance.
    """

    # Render TV components directly (container styling applied via CSS)
    render_tv_header()
    render_tv_kpi_cards(df)
    render_tv_board(df)


def render_data_table(df: pd.DataFrame):
    """Render the data table with export functionality."""
    if df.empty:
        return

    st.markdown("### Detailed View")

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
        label="Download CSV",
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

    st.sidebar.markdown("### API Connection")
    st.sidebar.text(f"Base URL: {base_url}")
    st.sidebar.text(f"Username: {username[:4]}***")

    # Test with a simple request (try to get just 1 sales order)
    test_result = request_json("/SalesOrders", {"rows": 1}, suppress_error=True)

    if test_result is not None:
        st.sidebar.success("API Connected")
        return True
    else:
        st.sidebar.error("API Connection Failed")
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

    # Set up auto-refresh (page will refresh once every 12 hours)
    setup_auto_refresh()

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

    # Create tabs for Desktop and TV views
    tab_desktop, tab_tv = st.tabs(["Desktop View", "TV View"])

    # All known stages including the new Workshop-prefixed ones
    all_stages = [
        "Workshop - New", "Workshop - Processing", "Workshop - Job Complete", "Workshop - To Collect",  # Workshop stages
        "New", "Processing", "Job Complete",  # Regular stages (non-workshop)
        "To Call", "To Collect", "Awaiting PO", "Awaiting Payment",
        "Release To Pick", "Partially Picked", "Fully Picked",
        "Fully Picked - Hold", "On Hold", "Ready to Invoice",
        "Fully Dispatched", "Dispatched", "Cancelled"
    ]

    # =========================================================================
    # DESKTOP VIEW TAB
    # =========================================================================
    with tab_desktop:
        render_header()

        # Show current filter info - updated to reflect stage-based filtering
        st.markdown(f"""
        <div class="info-box">
            <strong>Filter:</strong> Workshop stages (Workshop - New, Processing, Job Complete, To Collect) &nbsp;|&nbsp;
            <strong>Timezone:</strong> {TIMEZONE_DISPLAY}
        </div>
        """, unsafe_allow_html=True)

        # Controls row
        st.markdown('<div class="controls-row">', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns([3, 2, 3, 1])

        with col1:
            # Default to only active workshop stages
            default_stages = ACTIVE_STAGES.copy()

            selected_stages = st.multiselect(
                "Stages",
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
                "Search",
                placeholder="Reference, Project, Company..."
            )

        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # Determine excluded stages based on selection
        excluded_stages = [s for s in all_stages if s not in selected_stages]

        # Fetch data for desktop view
        with st.spinner("Loading workshop data..."):
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
            HDL Workshop Capacity Board v2.0-test | Timezone: {TIMEZONE_DISPLAY} |
            Data cached for 5 minutes | Filtering by Workshop stages (no Distribution Branch)
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # TV VIEW TAB
    # =========================================================================
    with tab_tv:
        # TV view uses default active stages only, no filters
        excluded_stages_tv = [s for s in all_stages if s not in ACTIVE_STAGES]

        # Fetch data for TV view
        with st.spinner("Loading workshop data..."):
            df_tv = fetch_sales_orders(tuple(excluded_stages_tv))

        # Render the TV view
        render_tv_view(df_tv)


if __name__ == "__main__":
    main()
