import streamlit as st
import pandas as pd

# --- 1. PASSWORD PROTECTION ---
def check_password():
    def password_entered():
        if st.session_state["password_input"] == "JVc32VEDsJhnnhrE":
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password_input")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password_input")
        st.error("Incorrect password. Please try again.")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. CONFIGURATION & STYLING ---
st.set_page_config(page_title="Sales Dashboard", layout="wide")

CAT_COLORS = {
    'BIOCHEMISTRY': '#185FA5', 'BLOODGAS & ELECTROLYTE': '#1D9E75',
    'COAGULATION': '#D85A30', 'FLOWCYTOMETRY': '#7F77DD',
    'IMMUNOLOGY': '#D4537E', 'LOCAL-PURCHASE': '#6B6B6B',
    'IL SPARES': '#BA7517', 'HAEMATOLOGY': '#639922',
    'MAIN UNITS': '#993556', 'PARTICLE': '#3C3489',
    'PARTICLE SPARES': '#0F6E56', 'IL-COAGULATION-REAGENT-CSD': '#A32D2D',
}

# --- 3. DATA LOADING ---
@st.cache_data
def load_data():
    # Load and clean dates
    df = pd.read_csv('quotation_data_extracted.csv')
    df['Quotation Expecting Day'] = pd.to_datetime(df['Quotation Expecting Day'], errors='coerce')
    df['Year'] = df['Quotation Expecting Day'].dt.year
    df['Month_Name'] = df['Quotation Expecting Day'].dt.strftime('%B')
    df['Month_Num'] = df['Quotation Expecting Day'].dt.month
    
    # Fill NA values to ensure search and grouping don't crash
    df = df.fillna({
        'Part Number': 'N/A', 
        'Product Name': 'Unknown Item', 
        'Customer Name': 'Unknown Customer',
        'Quantity': 0
    })
    
    # Pre-calculate search options
    customers = df['Customer Name'].unique().tolist()
    parts = df['Part Number'].unique().tolist()
    products = df['Product Name'].unique().tolist()
    search_options = sorted(list(set(customers + parts + products)))
    
    return df, search_options

df, search_options = load_data()

# --- 4. SESSION STATE INITIALIZATION ---
if 'view' not in st.session_state:
    st.session_state.view = 'categories'
    st.session_state.sel_cat = None
    st.session_state.sel_year = None
    st.session_state.sel_month = None

# --- 5. HEADER & TOP METRICS ---
st.title("Sales Quotation Requests Dashboard")
st.caption("Version 1.4 — Integrated Smart Search & Drill-Down")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Line Items", f"{len(df):,}")
m2.metric("Total Customers", df['Customer Name'].nunique())
m3.metric("Unique Products", df['Part Number'].nunique())
m4.metric("Categories", df['Product Category'].nunique())
st.divider()

# --- 6. SMART SEARCH (MIDDLE AREA) ---
st.write("### 🔍 Quick Search")
selected_search = st.selectbox(
    "Search for a Customer, Part Number, or Product Name:",
    options=[None] + search_options,
    index=0,
    placeholder="Type here to search...",
)

# Sidebar Reset Button
if st.sidebar.button("🏠 Reset to Dashboard Home"):
    st.session_state.view = 'categories'
    st.rerun()

# --- 7. MAIN DISPLAY LOGIC ---

# CASE A: SEARCH RESULTS
if selected_search:
    st.write("---")
    if st.button("⬅ Clear Search & Return to Layers"):
        st.rerun()

    st.subheader(f"Results for: '{selected_search}'")
    
    mask = (
        (df['Customer Name'] == selected_search) |
        (df['Part Number'] == selected_search) |
        (df['Product Name'] == selected_search)
    )
    search_df = df[mask]
    
    # Group by Part Number so we don't show the same item multiple times
    results = search_df.groupby(['Part Number', 'Product Name']).agg({'Quantity': 'sum'}).reset_index()
    results = results.sort_values('Quantity', ascending=False)
    
    for _, row in results.iterrows():
        with st.expander(f"{row['Product Name']} [{row['Part Number']}] — Total Qty: {row['Quantity']:,.2f}"):
            st.write("**Customer & Date Breakdown:**")
            breakdown = search_df[search_df['Part Number'] == row['Part Number']]
            breakdown_table = breakdown.groupby(['Customer Name', 'Year', 'Month_Name'])['Quantity'].sum().reset_index()
            breakdown_table = breakdown_table.sort_values('Quantity', ascending=False)
            
            st.table(breakdown_table.set_index('Customer Name').style.format({"Quantity": "{:.2f}"}))

# CASE B: LAYERED NAVIGATION
else:
    # Navigation Back Button
    if st.session_state.view != 'categories':
        if st.button("⬅ Back to Previous Level"):
            if st.session_state.view == 'items': st.session_state.view = 'months'
            elif st.session_state.view == 'months': st.session_state.view = 'years'
            else: st.session_state.view = 'categories'
            st.rerun()

    # --- LAYER 1: CATEGORIES ---
    if st.session_state.view == 'categories':
        st.subheader("1. Select a Product Category")
        cats = df.groupby('Product Category')['Quantity'].sum().sort_index()
        grid = st.columns(4)
        for i, (cat, total) in enumerate(cats.items()):
            color = CAT_COLORS.get(cat, '#555')
            with grid[i % 4]:
                st.markdown(f"""<div style="border-left: 5px solid {color}; padding-left:10px; margin-bottom:10px;">
                    <p style="margin:0; font-size:12px; color:#666;">{cat}</p>
                    <h3 style="margin:0; color:{color};">{int(total):,}</h3></div>""", unsafe_allow_html=True)
                if st.button(f"Open {cat}", key=cat):
                    st.session_state.sel_cat = cat
                    st.session_state.view = 'years'
                    st.rerun()

    # --- LAYER 2: YEARS ---
    elif st.session_state.view == 'years':
        cat = st.session_state.sel_cat
        st.subheader(f"2. Select Year for {cat}")
        cat_df = df[df['Product Category'] == cat]
        years = cat_df.groupby('Year')['Quantity'].sum().reset_index().sort_values('Year')
        grid = st.columns(4)
        for i, row in enumerate(years.itertuples()):
            with grid[i % 4]:
                st.metric(f"Year {int(row.Year)}", f"{int(row.Quantity):,}")
                if st.button(f"View {int(row.Year)}", key=f"yr_{row.Year}"):
                    st.session_state.sel_year = row.Year
                    st.session_state.view = 'months'
                    st.rerun()

    # --- LAYER 3: MONTHS ---
    elif st.session_state.view == 'months':
        cat, year = st.session_state.sel_cat, st.session_state.sel_year
        st.subheader(f"3. Select Month ({int(year)} — {cat})")
        yr_df = df[(df['Product Category'] == cat) & (df['Year'] == year)]
        months = yr_df.groupby(['Month_Num', 'Month_Name'])['Quantity'].sum().reset_index().sort_values('Month_Num')
        grid = st.columns(5)
        for i, row in enumerate(months.itertuples()):
            with grid[i % 5]:
                st.metric(row.Month_Name, f"{int(row.Quantity):,}")
                if st.button("View Items", key=f"m_{row.Month_Num}"):
                    st.session_state.sel_month = row.Month_Name
                    st.session_state.view = 'items'
                    st.rerun()

    # --- LAYER 4: ITEMS & CUSTOMERS ---
    elif st.session_state.view == 'items':
        cat, year, month = st.session_state.sel_cat, st.session_state.sel_year, st.session_state.sel_month
        st.subheader(f"4. Product Detail ({month} {int(year)} — {cat})")
        
        item_df = df[(df['Product Category'] == cat) & (df['Year'] == year) & (df['Month_Name'] == month)]
        items = item_df.groupby(['Part Number', 'Product Name'])['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False)
        
        for _, row in items.iterrows():
            # Item Header with Part Number
            with st.expander(f"{row['Product Name']} [{row['Part Number']}] ({row['Quantity']:,.2f} units)"):
                st.write("**Customer Breakdown:**")
                cust_breakdown = item_df[item_df['Part Number'] == row['Part Number']].groupby('Customer Name')['Quantity'].sum().reset_index()
                cust_breakdown = cust_breakdown.sort_values(by='Quantity', ascending=False)
                # Display table with 2 decimal points and sorted by volume
                st.table(cust_breakdown.set_index('Customer Name').style.format("{:.2f}"))
