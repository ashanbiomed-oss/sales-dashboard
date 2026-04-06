import streamlit as st

def check_password():
    if "password_correct" not in st.session_state:
        st.text_input("Enter Password", type="password", on_change=lambda: st.session_state.update({"password_correct": st.session_state.password == "YourCompanyPassword2024"}), key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop()  # Stop the app here if password is wrong

# ... (Rest of your dashboard code goes here)
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

# 2. SESSION STATE (To track which "Layer" we are on)
if 'view' not in st.session_state:
    st.session_state.view = 'categories'
    st.session_state.sel_cat = None
    st.session_state.sel_month = None

# 3. DATA LOADING
@st.cache_data
def load_data():
    df = pd.read_csv('quotation_data_extracted.csv')
    df['Quotation Expecting Day'] = pd.to_datetime(df['Quotation Expecting Day'], errors='coerce')
    df['Month_Name'] = df['Quotation Expecting Day'].dt.strftime('%B')
    df['Month_Num'] = df['Quotation Expecting Day'].dt.month
    return df

df = load_data()

# 4. CUSTOM CSS (To match the Colab look)
st.markdown("""
<style>
    .card {
        border-radius: 10px; padding: 15px; background: white;
        border: 1px solid #e6e9ef; transition: 0.3s;
    }
    .card:hover { border-color: #185FA5; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .stat-val { font-size: 24px; font-weight: bold; color: #185FA5; }
    .stat-lbl { font-size: 12px; color: #666; }
</style>
""", unsafe_allow_html=True)

# 5. HEADER
st.title("📊 Sales Quotation Dashboard")
st.caption("Biomed Scientific (Pvt) Ltd")

# Summary Bar
c1, c2, c3, c4 = st.columns(4)
c1.metric("Line Items", f"{len(df):,}")
c2.metric("Customers", df['Customer Name'].nunique())
c3.metric("Unique Items", df['Part Number'].nunique())
c4.metric("Categories", df['Product Category'].nunique())
st.divider()

# 6. LAYER NAVIGATION (The Drill-Down Logic)

# --- BREADCRUMBS ---
cols = st.columns([1, 10])
if st.session_state.view != 'categories':
    if cols[0].button("⬅ Back"):
        if st.session_state.view == 'items': st.session_state.view = 'months'
        else: st.session_state.view = 'categories'
        st.rerun()

# --- LAYER 1: CATEGORIES ---
if st.session_state.view == 'categories':
    st.subheader("Select a Category")
    cats = df.groupby('Product Category')['Quantity'].sum().sort_index()
    
    # Create a grid
    grid = st.columns(4)
    for i, (cat, total) in enumerate(cats.items()):
        color = CAT_COLORS.get(cat, '#555')
        with grid[i % 4]:
            st.markdown(f"""<div style="border-left: 5px solid {color}; padding-left:10px;">
                <p style="margin:0; font-size:12px; color:#666;">{cat}</p>
                <h3 style="margin:0; color:{color};">{int(total):,}</h3>
                </div>""", unsafe_allow_html=True)
            if st.button(f"Open {cat}", key=cat):
                st.session_state.sel_cat = cat
                st.session_state.view = 'months'
                st.rerun()

# --- LAYER 2: MONTHS ---
elif st.session_state.view == 'months':
    cat = st.session_state.sel_cat
    st.subheader(f"Months for {cat}")
    cat_df = df[df['Product Category'] == cat]
    months = cat_df.groupby(['Month_Num', 'Month_Name'])['Quantity'].sum().reset_index().sort_values('Month_Num')
    
    grid = st.columns(5)
    for i, row in enumerate(months.itertuples()):
        with grid[i % 5]:
            st.markdown(f"**{row.Month_Name}**")
            st.metric("Qty", f"{int(row.Quantity):,}")
            if st.button("View Items", key=f"m_{row.Month_Num}"):
                st.session_state.sel_month = row.Month_Name
                st.session_state.view = 'items'
                st.rerun()

# --- LAYER 3: ITEMS & CUSTOMERS ---
elif st.session_state.view == 'items':
    cat = st.session_state.sel_cat
    month = st.session_state.sel_month
    st.subheader(f"Items in {cat} ({month})")
    
    item_df = df[(df['Product Category'] == cat) & (df['Month_Name'] == month)]
    items = item_df.groupby(['Part Number', 'Product Name'])['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False)
    
    for _, row in items.iterrows():
        with st.expander(f"{row['Product Name']} ({int(row['Quantity'])} units)"):
            st.write("**Customer Breakdown:**")
            cust_breakdown = item_df[item_df['Part Number'] == row['Part Number']].groupby('Customer Name')['Quantity'].sum().reset_index()
            st.table(cust_breakdown)
