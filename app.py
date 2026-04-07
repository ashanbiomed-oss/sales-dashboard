import streamlit as st

def check_password():
    """Returns True if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password_input"] == "JVc32VEDsJhnnhrE":
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]  # Clean up the password from state
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run: show the input box
        st.text_input(
            "Enter Password", 
            type="password", 
            on_change=password_entered, 
            key="password_input"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Wrong password: show input box again + error message
        st.text_input(
            "Enter Password", 
            type="password", 
            on_change=password_entered, 
            key="password_input"
        )
        st.error("Incorrect password. Please try again.")
        return False
    else:
        # Password was correct
        return True

if not check_password():
    st.stop()  # Halt the app until password is correct
    import streamlit as st
import pandas as pd

# 1. SETUP & THEME
st.set_page_config(page_title="Sales Dashboard", layout="wide")

CAT_COLORS = {
    'BIOCHEMISTRY': '#185FA5', 'BLOODGAS & ELECTROLYTE': '#1D9E75',
    'COAGULATION': '#D85A30', 'FLOWCYTOMETRY': '#7F77DD',
    'IMMUNOLOGY': '#D4537E', 'LOCAL-PURCHASE': '#6B6B6B',
    'IL SPARES': '#BA7517', 'HAEMATOLOGY': '#639922',
    'MAIN UNITS': '#993556', 'PARTICLE': '#3C3489',
    'PARTICLE SPARES': '#0F6E56', 'IL-COAGULATION-REAGENT-CSD': '#A32D2D',
}

# 2. SESSION STATE
if 'view' not in st.session_state:
    st.session_state.view = 'categories'
    st.session_state.sel_cat = None
    st.session_state.sel_year = None # Added Year state
    st.session_state.sel_month = None

# 3. DATA LOADING
@st.cache_data
def load_data():
    df = pd.read_csv('quotation_data_extracted.csv')
    df['Quotation Expecting Day'] = pd.to_datetime(df['Quotation Expecting Day'], errors='coerce')
    df['Year'] = df['Quotation Expecting Day'].dt.year # Extract Year
    df['Month_Name'] = df['Quotation Expecting Day'].dt.strftime('%B')
    df['Month_Num'] = df['Quotation Expecting Day'].dt.month
    return df

df = load_data()

# 4. CUSTOM CSS
st.markdown("""
<style>
    .card { border-radius: 10px; padding: 15px; background: white; border: 1px solid #e6e9ef; }
    .stat-val { font-size: 24px; font-weight: bold; color: #185FA5; }
</style>
""", unsafe_allow_html=True)

# 5. HEADER
st.title("Sales Quotation Dashboard")
st.caption("Vesrion 1.1")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Line Items", f"{len(df):,}")
c2.metric("Customers", df['Customer Name'].nunique())
c3.metric("Unique Items", df['Part Number'].nunique())
c4.metric("Categories", df['Product Category'].nunique())
st.divider()

# 6. LAYER NAVIGATION (Updated for Year layer)

# --- BREADCRUMBS / BACK BUTTON ---
if st.session_state.view != 'categories':
    if st.button("⬅ Back"):
        if st.session_state.view == 'items': 
            st.session_state.view = 'months'
        elif st.session_state.view == 'months': 
            st.session_state.view = 'years'
        else: 
            st.session_state.view = 'categories'
        st.rerun()

# --- LAYER 1: CATEGORIES ---
if st.session_state.view == 'categories':
    st.subheader("Select a Category")
    cats = df.groupby('Product Category')['Quantity'].sum().sort_index()
    grid = st.columns(4)
    for i, (cat, total) in enumerate(cats.items()):
        color = CAT_COLORS.get(cat, '#555')
        with grid[i % 4]:
            st.markdown(f"""<div style="border-left: 5px solid {color}; padding-left:10px;">
                <p style="margin:0; font-size:12px; color:#666;">{cat}</p>
                <h3 style="margin:0; color:{color};">{int(total):,}</h3></div>""", unsafe_allow_html=True)
            if st.button(f"Open {cat}", key=cat):
                st.session_state.sel_cat = cat
                st.session_state.view = 'years' # Move to Years next
                st.rerun()

# --- LAYER 2: YEARS (New Layer) ---
elif st.session_state.view == 'years':
    cat = st.session_state.sel_cat
    st.subheader(f"Select Year for {cat}")
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
    cat = st.session_state.sel_cat
    year = st.session_state.sel_year
    st.subheader(f"Months in {int(year)} — {cat}")
    
    # Filter by Cat AND Year
    yr_df = df[(df['Product Category'] == cat) & (df['Year'] == year)]
    months = yr_df.groupby(['Month_Num', 'Month_Name'])['Quantity'].sum().reset_index().sort_values('Month_Num')
    
    grid = st.columns(5)
    for i, row in enumerate(months.itertuples()):
        with grid[i % 5]:
            st.markdown(f"**{row.Month_Name}**")
            st.metric("Qty", f"{int(row.Quantity):,}")
            if st.button("View Items", key=f"m_{row.Month_Num}"):
                st.session_state.sel_month = row.Month_Name
                st.session_state.view = 'items'
                st.rerun()

# --- LAYER 4: ITEMS & CUSTOMERS ---
elif st.session_state.view == 'items':
    cat = st.session_state.sel_cat
    year = st.session_state.sel_year
    month = st.session_state.sel_month
    st.subheader(f"Items in {month} {int(year)} — {cat}")
    
    item_df = df[(df['Product Category'] == cat) & 
                 (df['Year'] == year) & 
                 (df['Month_Name'] == month)]
    
    # We round the main items list to 2 decimals as well
    items = item_df.groupby(['Part Number', 'Product Name'])['Quantity'].sum().reset_index()
    items = items.sort_values('Quantity', ascending=False)

    for _, row in items.iterrows():
        # Display the item quantity with 2 decimal points in the expander title
        with st.expander(f"{row['Product Name']} ({row['Quantity']:,.2f} units)"):
            st.write("**Customer Breakdown:**")
            
            # 1. Group and Sum
            cust_breakdown = item_df[item_df['Part Number'] == row['Part Number']].groupby('Customer Name')['Quantity'].sum().reset_index()
            
            # 2. Sort from Highest to Lowest
            cust_breakdown = cust_breakdown.sort_values(by='Quantity', ascending=False)
            
            # 3. Round to 2 decimal places
            cust_breakdown['Quantity'] = cust_breakdown['Quantity'].round(2)
            
            # Reset index to hide the row numbers for a cleaner look
            st.table(cust_breakdown.set_index('Customer Name'))
