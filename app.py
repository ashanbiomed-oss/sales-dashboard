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

# --- 2. SETUP & DATA LOADING ---
st.set_page_config(page_title="Sales Dashboard", layout="wide")

CAT_COLORS = {
    'BIOCHEMISTRY': '#185FA5', 'BLOODGAS & ELECTROLYTE': '#1D9E75',
    'COAGULATION': '#D85A30', 'FLOWCYTOMETRY': '#7F77DD',
    'IMMUNOLOGY': '#D4537E', 'LOCAL-PURCHASE': '#6B6B6B',
    'IL SPARES': '#BA7517', 'HAEMATOLOGY': '#639922',
    'MAIN UNITS': '#993556', 'PARTICLE': '#3C3489',
    'PARTICLE SPARES': '#0F6E56', 'IL-COAGULATION-REAGENT-CSD': '#A32D2D',
}

@st.cache_data
def load_data():
    df = pd.read_csv('quotation_data_extracted.csv')
    df['Quotation Expecting Day'] = pd.to_datetime(df['Quotation Expecting Day'], errors='coerce')
    df['Year'] = df['Quotation Expecting Day'].dt.year
    df['Month_Name'] = df['Quotation Expecting Day'].dt.strftime('%B')
    df['Month_Num'] = df['Quotation Expecting Day'].dt.month
    # Fill NA values to prevent search errors
    df = df.fillna({'Part Number': 'N/A', 'Product Name': 'Unknown', 'Customer Name': 'Unknown'})
    return df

df = load_data()

# --- 3. SEARCH LOGIC (Sidebar) ---
st.sidebar.header("Navigation & Search")

# We use session_state to control the text in the search box
if "search_text" not in st.session_state:
    st.session_state.search_text = ""

def clear_search():
    st.session_state.search_text = ""

# The text input now uses the session_state value
search_query = st.sidebar.text_input(
    "🔍 Search", 
    value=st.session_state.search_text,
    key="search_input_box",
    placeholder="Customer, Part #, or Product...",
    on_change=lambda: st.session_state.update({"search_text": st.session_state.search_input_box})
)

# Show a 'Clear' button in sidebar if something is searched
if search_query:
    st.sidebar.button("❌ Clear Search", on_click=clear_search)

# --- 5. DISPLAY LOGIC ---
# --- 3. DATA LOADING (Updated to prepare search list) ---
@st.cache_data
def load_data():
    df = pd.read_csv('quotation_data_extracted.csv')
    df['Quotation Expecting Day'] = pd.to_datetime(df['Quotation Expecting Day'], errors='coerce')
    df['Year'] = df['Quotation Expecting Day'].dt.year
    df['Month_Name'] = df['Quotation Expecting Day'].dt.strftime('%B')
    df['Month_Num'] = df['Quotation Expecting Day'].dt.month
    df = df.fillna({'Part Number': 'N/A', 'Product Name': 'Unknown', 'Customer Name': 'Unknown'})
    
    # Pre-calculate a list of all searchable terms for the dropdown
    customers = df['Customer Name'].unique().tolist()
    parts = df['Part Number'].unique().tolist()
    products = df['Product Name'].unique().tolist()
    
    # Combine and sort for the dropdown list
    search_options = sorted(list(set(customers + parts + products)))
    return df, search_options

df, search_options = load_data()

# --- 4. NAVIGATION & SEARCH (Main Area) ---
st.title("Sales Quotation Requests Dashboard")
st.caption("Version 1.3 — Smart Search & Dropdown")

# Stats Bar (Top)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Line Items", f"{len(df):,}")
c2.metric("Customers", df['Customer Name'].nunique())
c3.metric("Unique Items", df['Part Number'].nunique())
c4.metric("Categories", df['Product Category'].nunique())
st.divider()

# --- THE "MIDDLE" SEARCH DROPDOWN ---
st.write("### 🔍 Quick Search")
selected_search = st.selectbox(
    "Type to search for a Customer, Part Number, or Product Name:",
    options=[None] + search_options, 
    index=0,
    placeholder="Start typing...",
    help="Selecting an item here will override the manual filters below."
)

if st.sidebar.button("🏠 Home"):
    st.session_state.view = 'categories'
    st.rerun()

# --- 5. DISPLAY LOGIC ---

# IF USER SELECTED SOMETHING FROM DROPDOWN
if selected_search:
    if st.button("⬅ Clear Search & Return to Layers"):
        st.rerun()

    st.subheader(f"Results for: '{selected_search}'")
    
    # Filter for exact match from the dropdown selection
    mask = (
        (df['Customer Name'] == selected_search) |
        (df['Part Number'] == selected_search) |
        (df['Product Name'] == selected_search)
    )
    search_df = df[mask]
    
    # Show results grouped by item
    results = search_df.groupby(['Part Number', 'Product Name']).agg({'Quantity': 'sum'}).reset_index()
    results = results.sort_values('Quantity', ascending=False)
    
    for _, row in results.iterrows():
        # Title now includes Part Number in brackets
        with st.expander(f"{row['Product Name']} [{row['Part Number']}] — {row['Quantity']:,.2f} total"):
            st.write("**Transaction Details:**")
            breakdown = search_df[search_df['Part Number'] == row['Part Number']]
            # Added Year and Month to the breakdown table for clarity
            breakdown_table = breakdown.groupby(['Customer Name', 'Year', 'Month_Name'])['Quantity'].sum().reset_index()
            breakdown_table = breakdown_table.sort_values('Quantity', ascending=False)
            
            # Formatting the table for 2 decimals and no index
            st.table(breakdown_table.set_index('Customer Name').style.format({"Quantity": "{:.2f}"}))

# IF NO SEARCH SELECTED, SHOW THE LAYERS AS USUAL
else:
    # --- BREADCRUMBS / BACK BUTTON ---
    if st.session_state.view != 'categories':
        if st.button("⬅ Back to Previous Layer"):
            if st.session_state.view == 'items': st.session_state.view = 'months'
            elif st.session_state.view == 'months': st.session_state.view = 'years'
            else: st.session_state.view = 'categories'
            st.rerun()

    # (Insert your Category / Year / Month / Item layer code here...)

            
    # ... (Rest of your Category/Year/Month/Item layers code goes here)
    # LAYER 1: CATEGORIES
    if st.session_state.view == 'categories':
        st.subheader("Select a Category")
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

    # LAYER 2: YEARS
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

    # LAYER 3: MONTHS
    elif st.session_state.view == 'months':
        cat, year = st.session_state.sel_cat, st.session_state.sel_year
        st.subheader(f"Months in {int(year)} — {cat}")
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

    # LAYER 4: ITEMS & CUSTOMERS
    elif st.session_state.view == 'items':
        cat, year, month = st.session_state.sel_cat, st.session_state.sel_year, st.session_state.sel_month
        st.subheader(f"Items in {month} {int(year)} — {cat}")
        
        item_df = df[(df['Product Category'] == cat) & (df['Year'] == year) & (df['Month_Name'] == month)]
        items = item_df.groupby(['Part Number', 'Product Name'])['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False)
        
        for _, row in items.iterrows():
            # PART NUMBER ADDED TO TITLE HERE
            with st.expander(f"{row['Product Name']} [{row['Part Number']}] ({row['Quantity']:,.2f} units)"):
                st.write("**Customer Breakdown:**")
                cust_breakdown = item_df[item_df['Part Number'] == row['Part Number']].groupby('Customer Name')['Quantity'].sum().reset_index()
                cust_breakdown = cust_breakdown.sort_values(by='Quantity', ascending=False)
                st.table(cust_breakdown.set_index('Customer Name').style.format("{:.2f}"))
