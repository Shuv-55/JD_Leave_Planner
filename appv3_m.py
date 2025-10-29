import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
import calendar
import base64
from pathlib import Path

# =============================================================================
# CONFIGURATION SECTION
# =============================================================================
st.set_page_config(
    page_title="JD-LMS", 
    page_icon="🏢", 
    layout="centered",  # Changed from "wide" to "centered" for better mobile view
    initial_sidebar_state="collapsed"
)

# For Streamlit Cloud - use secrets
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
SPREADSHEET_NAME = "Leave_Planner"
USERS_SHEET_NAME = "user_info"
LEAVES_SHEET_NAME = "leave_Data"
DEFAULT_PASSWORD = "SN123"
ADMIN_USERS = ["10110052", "10059480"]

# Image paths - relative paths for Streamlit Cloud
BACKGROUND_IMAGE_PATH = "template/abstract-background-3840x2160-10850.png"
LOGO_IMAGE_PATH = "template/jd.png"
LOGIN_BUTTON_IMAGE_PATH = "template/login.png"
LMS_LOGO_PATH = "template/LMS.png"

# Mandatory Holidays
MANDATORY_HOLIDAYS = {
    (1, 26): "Republic Day",
    (5, 1): "Labor Day",
    (8, 15): "Independence Day",
    (10, 2): "Gandhi Jayanti"
}

# =============================================================================
# GOOGLE SHEETS CONNECTION SECTION
# =============================================================================
@st.cache_resource
def get_gspread_client():
    """Initialize Google Sheets client using Streamlit secrets"""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=scope)
    return gspread.authorize(creds)

def open_worksheet(client, sheet_name):
    """Open specific worksheet"""
    spreadsheet = client.open(SPREADSHEET_NAME)
    return spreadsheet.worksheet(sheet_name)

@st.cache_data(ttl=60)
def load_user_info(_client):
    """Load user information from Google Sheets"""
    ws = open_worksheet(_client, USERS_SHEET_NAME)
    df = pd.DataFrame(ws.get_all_records())
    return df

@st.cache_data(ttl=60)
def load_leave_data(_client):
    """Load leave data from Google Sheets"""
    ws = open_worksheet(_client, LEAVES_SHEET_NAME)
    df = pd.DataFrame(ws.get_all_records())
    return df

# =============================================================================
# UTILITY FUNCTIONS SECTION
# =============================================================================
def get_base64_image(image_path):
    """Convert image to base64 for HTML embedding"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

def date_to_custom_format(date_obj):
    """Convert date to 25-Oct-2025 format"""
    return date_obj.strftime("%d-%b-%Y")

def parse_custom_date(date_str):
    """Parse date from 25-Oct-2025 format"""
    try:
        return datetime.strptime(date_str, "%d-%b-%Y").date()
    except:
        return None

def refresh_all_data():
    """Clear all cached data"""
    load_user_info.clear()
    load_leave_data.clear()

def get_short_name(full_name):
    """Convert 'Shuvam Sourav Nanda' to 'Shuvam S'"""
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1][0]}"
    return parts[0] if parts else full_name

def is_weekend(date_obj):
    """Check if date is Saturday or Sunday"""
    return date_obj.weekday() in [5, 6]

def is_mandatory_holiday(date_obj):
    """Check if date is a mandatory holiday"""
    return (date_obj.month, date_obj.day) in MANDATORY_HOLIDAYS

def get_holiday_reason(date_obj):
    """Get holiday reason with wasted indicator"""
    reason = MANDATORY_HOLIDAYS.get((date_obj.month, date_obj.day), "")
    if reason and is_weekend(date_obj):
        reason += " !!Wasted!!"
    return reason

# =============================================================================
# LOGIN PAGE SECTION
# =============================================================================
def render_login_page(user_df):
    """Render login page with glass morphism effect"""
    
    bg_image = get_base64_image(BACKGROUND_IMAGE_PATH)
    logo_image = get_base64_image(LOGO_IMAGE_PATH)
    
    login_css = f"""
    <style>
        .stApp {{
            background-image: linear-gradient(rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.3)), 
                              url("data:image/png;base64,{bg_image}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        
        .login-container {{
            background: rgba(0, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 2px solid rgba(0, 255, 255, 0.3);
            padding: 30px;
            box-shadow: 0 8px 32px 0 rgba(0, 255, 255, 0.37);
            margin: 50px auto;
            max-width: 400px;
        }}
        
        .login-logo {{
            text-align: center;
            margin-bottom: 20px;
        }}
        
        .login-logo img {{
            max-width: 100px;
            height: auto;
        }}
        
        .login-title {{
            text-align: center;
            color: #00FFFF;
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 25px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }}
    </style>
    """
    
    st.markdown(login_css, unsafe_allow_html=True)
    
    if logo_image:
        st.markdown(f'<div class="login-logo"><img src="data:image/png;base64,{logo_image}"></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="login-title">JD Leave Management System</div>', unsafe_allow_html=True)
    
    username = st.text_input("Employee Code", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    
    if st.button("Login", use_container_width=True, key="login_btn"):
        match = user_df[(user_df['Employee Code'].astype(str).str.lower() == username.lower()) & 
                       (user_df['Password'].astype(str) == password)]
        if not match.empty:
            st.session_state['user'] = match.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

# =============================================================================
# USER PROFILE MENU SECTION - MOBILE OPTIMIZED
# =============================================================================
def render_user_profile_menu(client, user_df):
    """Render user profile section - mobile responsive"""
    
    user = st.session_state.get('user')
    if not user:
        return
    
    # Use native Streamlit container instead of fixed positioning
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            short_name = get_short_name(user['Employee Name'])
            st.markdown(f"**Welcome {short_name}**")
        
        with col2:
            menu_option = st.selectbox(
                "Menu",
                ["Select", "Change Password", "Refresh", "Logout"],
                key="user_menu",
                label_visibility="collapsed"
            )
            
            if menu_option == "Logout":
                st.session_state.clear()
                st.rerun()
            
            elif menu_option == "Refresh":
                refresh_all_data()
                st.success("✅ Data refreshed!")
                st.rerun()
            
            elif menu_option == "Change Password":
                render_change_password_modal(client, user_df)
    
    st.divider()

def render_change_password_modal(client, user_df):
    """Render change password form"""
    
    st.subheader("🔒 Change Password")
    
    current_password = st.text_input("Current Password", type="password", key="current_pwd")
    new_password = st.text_input("New Password", type="password", key="new_pwd")
    confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_pwd")
    
    if st.button("Update Password", use_container_width=True):
        user = st.session_state.get('user')
        
        if current_password != user['Password']:
            st.error("❌ Current password is incorrect")
        elif new_password != confirm_password:
            st.error("❌ New passwords do not match")
        elif len(new_password) < 4:
            st.error("❌ Password must be at least 4 characters")
        else:
            try:
                ws = open_worksheet(client, USERS_SHEET_NAME)
                data = ws.get_all_records()
                df = pd.DataFrame(data)
                
                df.loc[df['Employee Code'].astype(str) == str(user['Employee Code']), 'Password'] = new_password
                
                ws.clear()
                ws.append_row(list(df.columns))
                for _, row in df.iterrows():
                    ws.append_row(list(row))
                
                st.session_state['user']['Password'] = new_password
                refresh_all_data()
                
                st.success("✅ Password updated successfully!")
            except Exception as e:
                st.error(f"❌ Error updating password: {str(e)}")

# =============================================================================
# HOME PAGE SECTION - MOBILE OPTIMIZED
# =============================================================================
def render_home_page(user_df, leave_df, client):
    """Render home page with statistics and calendar"""
    
    st.title("📊 LMS Dashboard")
    
    user = st.session_state.get('user')
    if not user:
        st.warning("⚠️ Please log in first.")
        return
    
    emp_code = str(user['Employee Code'])
    yearly_leaves = user_df[user_df['Employee Code'].astype(str) == emp_code]['yearly_leaves'].values
    monthly_wfh = user_df[user_df['Employee Code'].astype(str) == emp_code]['monthly_wfh'].values
    
    yearly_leaves = int(yearly_leaves[0]) if len(yearly_leaves) > 0 else 24
    monthly_wfh = int(monthly_wfh[0]) if len(monthly_wfh) > 0 else 5
    
    my_leaves = leave_df[leave_df['Employee Code'].astype(str) == emp_code]
    approved_leaves = my_leaves[my_leaves['Status'] == 'Approved']
    
    leaves_used = len(approved_leaves[(approved_leaves['Leave_type'] == 'Leave')])
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    wfh_this_month = 0
    wfh_leaves = approved_leaves[approved_leaves['Leave_type'] == 'WFH']
    for _, row in wfh_leaves.iterrows():
        date_str = str(row['Date'])
        parsed_date = parse_custom_date(date_str.split(' to ')[0])
        if parsed_date and parsed_date.month == current_month and parsed_date.year == current_year:
            wfh_this_month += 1
    
    pending = len(my_leaves[my_leaves['Status'] == 'Pending'])
    approved = len(approved_leaves)
    
    # Mobile-friendly: 2x2 grid instead of 4 columns
    col1, col2 = st.columns(2)
    col1.metric(f"📅 Yearly Leaves", f"{leaves_used}/{yearly_leaves}")
    col2.metric(f"💼 Monthly WFH", f"{wfh_this_month}/{monthly_wfh}")
    
    col3, col4 = st.columns(2)
    col3.metric("⏳ Pending", pending)
    col4.metric("✅ Approved", approved)
    
    st.markdown("---")
    
    render_leave_calendar(leave_df, user_df)

def render_leave_calendar(leave_df, user_df):
    """Render monthly calendar - mobile friendly with tabs"""
    
    st.subheader("📅 Monthly Leave Calendar")
    
    col1, col2 = st.columns(2)
    
    with col1:
        current_date = datetime.now()
        selected_month = st.selectbox(
            "Month",
            range(1, 13),
            index=current_date.month - 1,
            format_func=lambda x: calendar.month_name[x],
            key="cal_month"
        )
    
    with col2:
        selected_year = st.number_input("Year", min_value=2020, max_value=2030, value=current_date.year, key="cal_year")
    
    if 'Date' in leave_df.columns and not leave_df.empty:
        leave_df_copy = leave_df.copy()
        leave_df_copy['parsed_date'] = leave_df_copy['Date'].apply(lambda x: parse_custom_date(str(x).split(' to ')[0]))
        
        month_leaves = leave_df_copy[
            (leave_df_copy['parsed_date'].notna()) &
            (leave_df_copy['parsed_date'].apply(lambda x: x.month == selected_month)) & 
            (leave_df_copy['parsed_date'].apply(lambda x: x.year == selected_year)) &
            (leave_df_copy['Status'].isin(['Pending', 'Approved'])) &
            (~leave_df_copy['Leave_type'].isin(['Holiday']))
        ]
        
        cal = calendar.monthcalendar(selected_year, selected_month)
        
        st.markdown("**Legend:** 🟦 WFH | 🟩 Leave | 🟥 Weekend/Holiday")
        
        # Mobile-friendly: Use tabs for each week
        week_tabs = st.tabs([f"Week {i+1}" for i in range(len(cal))])
        
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        for week_idx, (week, tab) in enumerate(zip(cal, week_tabs)):
            with tab:
                for i, day in enumerate(week):
                    if day == 0:
                        continue
                    
                    day_date = date(selected_year, selected_month, day)
                    day_leaves = month_leaves[month_leaves['parsed_date'] == day_date]
                    
                    is_wknd = is_weekend(day_date)
                    is_mh = is_mandatory_holiday(day_date)
                    
                    # Use expander for each day - very mobile friendly
                    emoji = "🎉" if is_mh else ("🟥" if is_wknd else "")
                    with st.expander(f"{days[i]} - {day} {emoji}", expanded=False):
                        if is_mh:
                            reason = get_holiday_reason(day_date)
                            st.warning(f"🎉 {reason}")
                        elif is_wknd:
                            st.info("Weekend")
                        
                        wfh_count = len(day_leaves[day_leaves['Leave_type'] == 'WFH'])
                        leave_count = len(day_leaves[day_leaves['Leave_type'] == 'Leave'])
                        
                        if wfh_count > 0:
                            st.write(f"🟦 WFH: {wfh_count}")
                        if leave_count > 0:
                            st.write(f"🟩 Leave: {leave_count}")
                        
                        if len(day_leaves) > 0:
                            names = [get_short_name(name) for name in day_leaves['Employee Name'].tolist()]
                            for name in names:
                                st.write(f"• {name}")
                        
                        if wfh_count == 0 and leave_count == 0 and not is_mh and not is_wknd:
                            st.info("No leaves")

# =============================================================================
# APPLY LEAVE PAGE SECTION
# =============================================================================
def render_apply_leave_page(leave_df, client, user_df):
    """Render apply leave page with custom date format"""
    
    st.title("📝 Apply Leave")
    
    user = st.session_state.get('user')
    if not user:
        st.warning("⚠️ Please log in first.")
        return
    
    is_admin = str(user['Employee Code']) in ADMIN_USERS
    
    col1, col2 = st.columns(2)
    
    with col1:
        leave_types = ["Leave", "WFH", "Holiday"] if is_admin else ["Leave", "WFH"]
        leave_type = st.selectbox("Leave Type", leave_types)
        
    with col2:
        mode = st.radio("Select Date Mode", ["Single Date", "Date Range"])
    
    if mode == "Single Date":
        date_input = st.text_input("Date (DD-Mon-YYYY)", placeholder="25-Oct-2025")
        
        if date_input:
            parsed_date = parse_custom_date(date_input)
            if parsed_date:
                if is_weekend(parsed_date) or is_mandatory_holiday(parsed_date):
                    st.error("❌ Bro You Have Selected a Holiday")
                    start_date = end_date = None
                else:
                    start_date = end_date = parsed_date
                    st.success(f"✅ Selected: {date_to_custom_format(start_date)}")
            else:
                st.error("❌ Invalid date format. Use DD-Mon-YYYY (e.g., 25-Oct-2025)")
                start_date = end_date = None
        else:
            start_date = end_date = None
    else:
        col_start, col_end = st.columns(2)
        
        with col_start:
            start_input = st.text_input("Start Date (DD-Mon-YYYY)", placeholder="25-Oct-2025")
            
        with col_end:
            end_input = st.text_input("End Date (DD-Mon-YYYY)", placeholder="31-Oct-2025")
        
        start_date = parse_custom_date(start_input) if start_input else None
        end_date = parse_custom_date(end_input) if end_input else None
        
        if start_date and end_date:
            if start_date <= end_date:
                has_holiday = False
                check_date = start_date
                while check_date <= end_date:
                    if is_weekend(check_date) or is_mandatory_holiday(check_date):
                        has_holiday = True
                        break
                    check_date += timedelta(days=1)
                
                if has_holiday:
                    st.error("❌ Bro You Have Selected a Holiday")
                    start_date = end_date = None
                else:
                    st.success(f"✅ Range: {date_to_custom_format(start_date)} to {date_to_custom_format(end_date)}")
            else:
                st.error("❌ End date must be after start date")
                start_date = end_date = None
    
    reason = st.text_area("Reason", placeholder="Enter reason for leave...")
    
    if st.button("📤 Submit Leave Request", type="primary", use_container_width=True):
        if not start_date or not end_date:
            st.error("❌ Please enter valid dates")
        elif not reason:
            st.error("❌ Please enter a reason")
        else:
            try:
                ws = open_worksheet(client, LEAVES_SHEET_NAME)
                
                if start_date == end_date:
                    date_str = date_to_custom_format(start_date)
                else:
                    date_str = f"{date_to_custom_format(start_date)} to {date_to_custom_format(end_date)}"
                
                status = "Approved" if leave_type == "Holiday" and is_admin else "Pending"
                
                ws.append_row([
                    user['Employee Code'],
                    user['Employee Name'],
                    user['Reporting Manger_empc'],
                    user['Reporting Manger_Name'],
                    date_str,
                    leave_type,
                    reason,
                    status,
                    ""
                ])
                
                refresh_all_data()
                st.success("✅ Leave request submitted successfully!")
                
            except Exception as e:
                st.error(f"❌ Error submitting leave: {str(e)}")

# =============================================================================
# MY LEAVE PAGE SECTION - MOBILE OPTIMIZED
# =============================================================================
def render_my_leave_page(leave_df):
    """Render my leaves page"""
    
    st.title("📋 My Leaves")
    
    user = st.session_state.get('user')
    if not user:
        st.warning("⚠️ Please log in first.")
        return
    
    emp_code = str(user['Employee Code'])
    my_leaves = leave_df[leave_df['Employee Code'].astype(str) == emp_code]
    
    if my_leaves.empty:
        st.info("ℹ️ No leaves applied yet.")
    else:
        # Filters in mobile-friendly layout
        status_filter = st.multiselect(
            "Filter by Status",
            ["Pending", "Approved", "Rejected"],
            default=["Pending", "Approved", "Rejected"],
            key="my_leave_status"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            month_filter = st.selectbox(
                "Month",
                ["All"] + [calendar.month_name[i] for i in range(1, 13)],
                key="my_leave_month"
            )
        
        with col2:
            year_filter = st.selectbox(
                "Year",
                ["All"] + list(range(2020, 2031)),
                key="my_leave_year"
            )
        
        filtered_leaves = my_leaves[my_leaves['Status'].isin(status_filter)]
        
        if month_filter != "All" or year_filter != "All":
            filtered_leaves['parsed_date'] = filtered_leaves['Date'].apply(lambda x: parse_custom_date(str(x).split(' to ')[0]))
            
            if month_filter != "All":
                month_num = list(calendar.month_name).index(month_filter)
                filtered_leaves = filtered_leaves[filtered_leaves['parsed_date'].apply(lambda x: x.month == month_num if x else False)]
            
            if year_filter != "All":
                filtered_leaves = filtered_leaves[filtered_leaves['parsed_date'].apply(lambda x: x.year == year_filter if x else False)]
        
        display_cols = ['Date', 'Leave_type', 'Reason', 'Status']
        if 'M_Comment' in filtered_leaves.columns:
            display_cols.append('M_Comment')
        
        # Mobile-friendly: Fixed height with scroll
        st.dataframe(
            filtered_leaves[display_cols],
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Approved", len(my_leaves[my_leaves['Status'] == 'Approved']))
        col2.metric("⏳ Pending", len(my_leaves[my_leaves['Status'] == 'Pending']))
        col3.metric("❌ Rejected", len(my_leaves[my_leaves['Status'] == 'Rejected']))

# =============================================================================
# MANAGE LEAVE PAGE SECTION - MOBILE OPTIMIZED
# =============================================================================
def render_manage_leave_page(leave_df, client, user_df):
    """Render manage leave page for managers - mobile optimized"""
    
    st.title("🧭 Manage Leaves")
    
    user = st.session_state.get('user')
    if not user:
        st.warning("⚠️ Please log in first.")
        return
    
    mgr_code = str(user['Employee Code'])
    
    team_leaves = leave_df[leave_df['Reporting Manger_empc'].astype(str) == mgr_code]
    
    # Mobile-friendly filters
    col1, col2 = st.columns(2)
    
    with col1:
        current_date = datetime.now()
        selected_month = st.selectbox(
            "Month",
            range(1, 13),
            index=current_date.month - 1,
            format_func=lambda x: calendar.month_name[x],
            key="manage_month"
        )
    
    with col2:
        selected_year = st.number_input("Year", min_value=2020, max_value=2030, value=current_date.year, key="manage_year")
    
    reportees = team_leaves['Employee Name'].unique().tolist()
    selected_reportee = st.selectbox("Filter by Reportee", ["All"] + reportees, key="manage_reportee")
    
    if selected_reportee != "All":
        display_leaves = team_leaves[team_leaves['Employee Name'] == selected_reportee]
    else:
        display_leaves = team_leaves
    
    display_leaves_copy = display_leaves.copy()
    display_leaves_copy['parsed_date'] = display_leaves_copy['Date'].apply(lambda x: parse_custom_date(str(x).split(' to ')[0]))
    
    month_leaves = display_leaves_copy[
        (display_leaves_copy['parsed_date'].notna()) &
        (display_leaves_copy['parsed_date'].apply(lambda x: x.month == selected_month)) & 
        (display_leaves_copy['parsed_date'].apply(lambda x: x.year == selected_year)) &
        (~display_leaves_copy['Leave_type'].isin(['Holiday']))
    ]
    
    # Mobile-friendly: Use tabs instead of showing everything at once
    tab1, tab2 = st.tabs(["📅 Calendar View", "📋 Action Center"])
    
    with tab1:
        render_manager_calendar(month_leaves, selected_month, selected_year)
    
    with tab2:
        st.subheader("Take Action on Pending Leaves")
        
        pending_leaves = month_leaves[month_leaves['Status'] == 'Pending']
        
        if pending_leaves.empty:
            st.info("ℹ️ No pending leaves to review for this month.")
            return
        
        # Mobile-friendly: Show each leave as a card with expander
        for idx, row in pending_leaves.iterrows():
            with st.expander(f"{get_short_name(row['Employee Name'])} - {row['Date']}"):
                st.write(f"**Type:** {row['Leave_type']}")
                st.write(f"**Reason:** {row['Reason']}")
                st.write(f"**Status:** {row['Status']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("✅ Approve", key=f"approve_{idx}", use_container_width=True):
                        update_single_leave_status(client, row, 'Approved')
                        st.success("Approved!")
                        st.rerun()
                
                with col2:
                    if st.button("❌ Reject", key=f"reject_{idx}", use_container_width=True):
                        update_single_leave_status(client, row, 'Rejected')
                        st.error("Rejected!")
                        st.rerun()

def render_manager_calendar(month_leaves, selected_month, selected_year):
    """Render calendar for manager view - mobile friendly"""
    
    st.subheader("📅 Team Calendar")
    
    cal = calendar.monthcalendar(selected_year, selected_month)
    
    st.markdown("**Legend:** 🟦 WFH | 🟩 Leave | 🟥 Weekend/Holiday")
    
    # Mobile-friendly: Use tabs for weeks
    week_tabs = st.tabs([f"Week {i+1}" for i in range(len(cal))])
    
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    for week_idx, (week, tab) in enumerate(zip(cal, week_tabs)):
        with tab:
            for i, day in enumerate(week):
                if day == 0:
                    continue
                
                day_date = date(selected_year, selected_month, day)
                day_leaves = month_leaves[month_leaves['parsed_date'] == day_date]
                
                is_wknd = is_weekend(day_date)
                is_mh = is_mandatory_holiday(day_date)
                
                emoji = "🎉" if is_mh else ("🟥" if is_wknd else "")
                with st.expander(f"{days[i]} - {day} {emoji}", expanded=False):
                    if is_mh:
                        reason = get_holiday_reason(day_date)
                        st.warning(f"🎉 {reason}")
                    elif is_wknd:
                        st.info("Weekend")
                    
                    wfh_count = len(day_leaves[day_leaves['Leave_type'] == 'WFH'])
                    leave_count = len(day_leaves[day_leaves['Leave_type'] == 'Leave'])
                    
                    if wfh_count > 0:
                        st.write(f"🟦 WFH: {wfh_count}")
                    if leave_count > 0:
                        st.write(f"🟩 Leave: {leave_count}")
                    
                    if len(day_leaves) > 0:
                        names = [get_short_name(name) for name in day_leaves['Employee Name'].tolist()]
                        for name in names:
                            st.write(f"• {name}")
                    
                    if wfh_count == 0 and leave_count == 0 and not is_mh and not is_wknd:
                        st.info("No leaves")

def update_single_leave_status(client, row, status):
    """Update single leave status in Google Sheets"""
    try:
        ws = open_worksheet(client, LEAVES_SHEET_NAME)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        mask = (
            (df['Employee Code'].astype(str) == str(row['Employee Code'])) &
            (df['Date'].astype(str) == str(row['Date'])) &
            (df['Leave_type'].astype(str) == str(row['Leave_type'])) &
            (df['Status'].astype(str) == 'Pending')
        )
        
        df.loc[mask, 'Status'] = status
        
        ws.clear()
        ws.append_row(list(df.columns))
        for _, r in df.iterrows():
            ws.append_row(list(r))
        
        refresh_all_data()
        
    except Exception as e:
        st.error(f"Error updating status: {str(e)}")

# =============================================================================
# EDIT USER PAGE SECTION (ADMIN ONLY) - MOBILE OPTIMIZED
# =============================================================================
def render_edit_user_page(user_df, client, leave_df):
    """Render edit user page - only for admins - mobile optimized"""
    
    st.title("👥 Edit Users (Admin Only)")
    
    user = st.session_state.get('user')
    if not user:
        st.warning("⚠️ Please log in first.")
        return
    
    if str(user['Employee Code']) not in ADMIN_USERS:
        st.error("🚫 Access Denied. Only authorized users can access this page.")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 View Users", "➕ Add User", "🗑️ Remove User", "📊 Report"])
    
    with tab1:
        st.subheader("All Users")
        
        if 'show_passwords' not in st.session_state:
            st.session_state.show_passwords = {}
        
        # Mobile-friendly: Show users as cards with expanders
        for idx, row in user_df.iterrows():
            emp_code = str(row['Employee Code'])
            show_pwd = st.session_state.show_passwords.get(emp_code, False)
            
            with st.expander(f"{get_short_name(row['Employee Name'])} ({emp_code})"):
                st.write(f"**Manager Code:** {row['Reporting Manger_empc']}")
                st.write(f"**Manager Name:** {get_short_name(row['Reporting Manger_Name'])}")
                st.write(f"**Yearly Leaves:** {row['yearly_leaves']}")
                st.write(f"**Monthly WFH:** {row['monthly_wfh']}")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if show_pwd:
                        st.write(f"**Password:** {row['Password']}")
                    else:
                        st.write(f"**Password:** {'*' * len(str(row['Password']))}")
                
                with col2:
                    if st.button("👁️", key=f"show_{emp_code}"):
                        st.session_state.show_passwords[emp_code] = not show_pwd
                        st.rerun()
    
    with tab2:
        st.subheader("Add New User")
        
        with st.form("add_user_form"):
            new_emp_code = st.text_input("Employee Code*")
            new_emp_name = st.text_input("Employee Name*")
            new_mgr_code = st.text_input("Reporting Manager Employee Code*")
            new_mgr_name = st.text_input("Reporting Manager Name*")
            
            col1, col2 = st.columns(2)
            with col1:
                new_yearly_leaves = st.number_input("Yearly Leaves*", min_value=0, max_value=50, value=24)
            with col2:
                new_monthly_wfh = st.number_input("Monthly WFH*", min_value=0, max_value=10, value=5)
            
            st.info(f"ℹ️ Default password will be set to: **{DEFAULT_PASSWORD}**")
            
            submitted = st.form_submit_button("➕ Add User", type="primary", use_container_width=True)
            
            if submitted:
                if not all([new_emp_code, new_emp_name, new_mgr_code, new_mgr_name]):
                    st.error("❌ All fields are required")
                elif str(new_emp_code) in user_df['Employee Code'].astype(str).values:
                    st.error("❌ Employee Code already exists")
                else:
                    try:
                        ws = open_worksheet(client, USERS_SHEET_NAME)
                        ws.append_row([
                            new_emp_code,
                            new_emp_name,
                            new_mgr_code,
                            new_mgr_name,
                            DEFAULT_PASSWORD,
                            new_yearly_leaves,
                            new_monthly_wfh
                        ])
                        
                        refresh_all_data()
                        st.success(f"✅ User {new_emp_name} added successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error adding user: {str(e)}")
    
    with tab3:
        st.subheader("Remove User")
        
        st.warning("⚠️ Warning: This action cannot be undone!")
        
        remove_emp_code = st.text_input("Enter Employee Code to Remove")
        
        if remove_emp_code:
            user_to_remove = user_df[user_df['Employee Code'].astype(str) == remove_emp_code]
            
            if not user_to_remove.empty:
                st.write("**User to be removed:**")
                
                # Mobile-friendly: Show as card instead of dataframe
                with st.container():
                    st.write(f"**Employee Code:** {user_to_remove.iloc[0]['Employee Code']}")
                    st.write(f"**Employee Name:** {user_to_remove.iloc[0]['Employee Name']}")
                    st.write(f"**Manager Code:** {user_to_remove.iloc[0]['Reporting Manger_empc']}")
                    st.write(f"**Manager Name:** {user_to_remove.iloc[0]['Reporting Manger_Name']}")
                
                if st.button("🗑️ Confirm Removal", type="secondary", use_container_width=True):
                    try:
                        ws = open_worksheet(client, USERS_SHEET_NAME)
                        data = ws.get_all_records()
                        df = pd.DataFrame(data)
                        
                        df = df[df['Employee Code'].astype(str) != remove_emp_code]
                        
                        ws.clear()
                        ws.append_row(list(df.columns))
                        for _, row in df.iterrows():
                            ws.append_row(list(row))
                        
                        refresh_all_data()
                        st.success(f"✅ User removed successfully!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error removing user: {str(e)}")
            else:
                st.error("❌ Employee Code not found")
    
    with tab4:
        st.subheader("📊 Leave Report")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_month = st.selectbox(
                "Select Month",
                ["Yearly"] + [calendar.month_name[i] for i in range(1, 13)],
                key="report_month"
            )
        
        with col2:
            report_year = st.selectbox(
                "Select Year",
                list(range(2020, 2031)),
                index=list(range(2020, 2031)).index(datetime.now().year),
                key="report_year"
            )
        
        report_leaves = leave_df[
            (leave_df['Status'] == 'Approved') &
            (~leave_df['Leave_type'].isin(['Holiday']))
        ].copy()
        
        report_leaves['parsed_date'] = report_leaves['Date'].apply(lambda x: parse_custom_date(str(x).split(' to ')[0]))
        
        report_leaves = report_leaves[report_leaves['parsed_date'].apply(lambda x: x.year == report_year if x else False)]
        
        if report_month != "Yearly":
            month_num = list(calendar.month_name).index(report_month)
            report_leaves = report_leaves[report_leaves['parsed_date'].apply(lambda x: x.month == month_num if x else False)]
        
        if not report_leaves.empty:
            report_data = []
            
            for emp_name in report_leaves['Employee Name'].unique():
                emp_leaves = report_leaves[report_leaves['Employee Name'] == emp_name]
                
                wfh_count = len(emp_leaves[emp_leaves['Leave_type'] == 'WFH'])
                leave_count = len(emp_leaves[emp_leaves['Leave_type'] == 'Leave'])
                
                report_data.append({
                    'Employee Name': get_short_name(emp_name),
                    'WFH': wfh_count,
                    'Leave': leave_count,
                    'Total': wfh_count + leave_count
                })
            
            report_df = pd.DataFrame(report_data)
            report_df = report_df.sort_values('Total', ascending=False)
            
            # Mobile-friendly: Fixed height with scroll
            st.dataframe(
                report_df, 
                use_container_width=True, 
                hide_index=True,
                height=400
            )
            
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total WFH", report_df['WFH'].sum())
            col2.metric("Total Leaves", report_df['Leave'].sum())
            col3.metric("Total Days", report_df['Total'].sum())
        else:
            st.info("ℹ️ No leave data found for selected period.")

# =============================================================================
# MAIN APPLICATION SECTION
# =============================================================================
def main():
    """Main application entry point"""
    
    try:
        client = get_gspread_client()
        user_df = load_user_info(client)
        leave_df = load_leave_data(client)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {str(e)}")
        st.info("Please check your Google Sheets credentials and make sure the service account has access to the spreadsheet.")
        return
    
    if 'user' not in st.session_state:
        render_login_page(user_df)
        return
    
    render_user_profile_menu(client, user_df)
    
    lms_logo = get_base64_image(LMS_LOGO_PATH)
    
    st.sidebar.markdown("---")
    if lms_logo:
        st.sidebar.markdown(f'<img src="data:image/png;base64,{lms_logo}" style="max-width: 50px; margin-bottom: 10px;">', unsafe_allow_html=True)
    st.sidebar.title("JD-LMS")
    
    pages = {
        "🏠 Home": "home",
        "📝 Apply Leave": "apply",
        "📋 My Leaves": "my_leaves",
        "🧭 Manage Leaves": "manage",
        "👥 Edit Users": "edit_users"
    }
    
    selected_page = st.sidebar.radio("Navigation", list(pages.keys()))
    page = pages[selected_page]
    
    if page == "home":
        render_home_page(user_df, leave_df, client)
    elif page == "apply":
        render_apply_leave_page(leave_df, client, user_df)
    elif page == "my_leaves":
        render_my_leave_page(leave_df)
    elif page == "manage":
        render_manage_leave_page(leave_df, client, user_df)
    elif page == "edit_users":
        render_edit_user_page(user_df, client, leave_df)

if __name__ == '__main__':
    main()