import streamlit as st
import pandas as pd
import io

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
        st.error("Incorrect password.")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. CONFIG & DATA LOADING ---
st.set_page_config(page_title="Inventory & Sales Suite", layout="wide")

@st.cache_data
def load_data():
    # Use the exact column name from your CSV (with spaces)
    df = pd.read_csv('quotation_data_extracted.csv')
    df['Quotation Expecting Day'] = pd.to_datetime(df['Quotation Expecting Day'], errors='coerce')
    
    # --- PROCUREMENT LOGIC (2 Months Lead Time) ---
    # We use 'Quotation Expecting Day' (the column name you provided earlier)
    df['Order_Placement_Date'] = df['Quotation Expecting Day'] - pd.DateOffset(months=2)
    
    # Extract Original Date Info (Required by Customer)
    df['Year'] = df['Quotation Expecting Day'].dt.year
    df['Month_Name'] = df['Quotation Expecting Day'].dt.strftime('%B')
    
    # Extract Order Placement Date Info (When we should order)
    df['Order_Year'] = df['Order_Placement_Date'].dt.year
    df['Order_Month'] = df['Order_Placement_Date'].dt.strftime('%B')
    df['Order_Month_Num'] = df['Order_Placement_Date'].dt.month
    
    # Handle empty values to prevent crashes
    df = df.fillna({
        'Part Number': 'N/A', 
        'Product Name': 'Unknown', 
        'Customer Name': 'Unknown', 
        'Quantity': 0,
        'Product Category': 'Uncategorized'
    })
    return df

df = load_data()

# --- 3. SESSION STATE ---
if 'mode' not in st.session_state: st.session_state.mode = 'Sales View'
if 'view' not in st.session_state: st.session_state.view = 'main'

# Navigation keys for drill-down
for key in ['sel_cust', 'sel_order_month', 'sel_cat']:
    if key not in st.session_state: st.session_state[key] = None

# --- 4. SIDEBAR & EXCEL EXPORT ---
st.sidebar.header("Control Panel")
st.session_state.mode = st.sidebar.radio("Switch View:", ["Sales View", "Procurement Planner"])

def to_excel(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Procurement_Plan')
    return output.getvalue()

st.sidebar.divider()
if st.sidebar.button("📊 Export Full Procurement Plan"):
    # Selecting relevant columns for the export
    proc_df = df[[
        'Customer Name', 'Order_Month', 'Order_Year', 
        'Product Category', 'Product Name', 'Part Number', 
        'Quantity', 'Month_Name'
    ]].copy()
    
    proc_df.columns = [
        'Customer', 'Order Placement Month', 'Order Year', 
        'Category', 'Item Description', 'Part Number', 
        'Quantity', 'Customer Required Month'
    ]
    
    excel_data = to_excel(proc_df)
    st.sidebar.download_button(
        label="📥 Download Excel",
        data=excel_data,
        file_name="Procurement_Schedule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if st.sidebar.button("🏠 Reset Dashboard Home"):
    st.session_state.view = 'main'
    st.rerun()

# --- 5. MAIN UI ---
st.title(f"{st.session_state.mode}")

# PROCUREMENT PLANNER LOGIC
if st.session_state.mode == "Procurement Planner":
    st.caption("Ordering Schedule: Current logic subtracts 2 months from the customer's required date.")
    
    # BACK BUTTON
    if st.session_state.view != 'main':
        if st.button("⬅ Back"):
            if st.session_state.view == 'items': st.session_state.view = 'categories'
            elif st.session_state.view == 'categories': st.session_state.view = 'months'
            elif st.session_state.view == 'months': st.session_state.view = 'main'
            st.rerun()

    # LAYER 1: CUSTOMERS
    if st.session_state.view == 'main':
        st.subheader("Select Customer")
        cust_list = sorted(df['Customer Name'].unique())
        cols = st.columns(3)
        for i, cust in enumerate(cust_list):
            with cols[i % 3]:
                if st.button(cust, key=f"p_cust_{i}", use_container_width=True):
                    st.session_state.sel_cust = cust
                    st.session_state.view = 'months'
                    st.rerun()

    # LAYER 2: ORDERING MONTHS
    elif st.session_state.view == 'months':
        cust = st.session_state.sel_cust
        st.subheader(f"Ordering Months for {cust}")
        cust_df = df[df['Customer Name'] == cust]
        
        # Group by the Order Placement month
        months = cust_df.groupby(['Order_Month_Num', 'Order_Month'])['Quantity'].sum().reset_index().sort_values('Order_Month_Num')
        
        cols = st.columns(4)
        for i, row in enumerate(months.itertuples()):
            with cols[i % 4]:
                st.metric(f"To order in {row.Order_Month}", f"{row.Quantity:,.2f}")
                if st.button(f"Open {row.Order_Month}", key=f"p_mo_{i}"):
                    st.session_state.sel_order_month = row.Order_Month
                    st.session_state.view = 'categories'
                    st.rerun()

    # LAYER 3: CATEGORIES
    elif st.session_state.view == 'categories':
        cust, month = st.session_state.sel_cust, st.session_state.sel_order_month
        st.subheader(f"Categories for {cust} (Order in {month})")
        cat_df = df[(df['Customer Name'] == cust) & (df['Order_Month'] == month)]
        cats = cat_df.groupby('Product Category')['Quantity'].sum().reset_index()
        
        cols = st.columns(3)
        for i, row in enumerate(cats.itertuples()):
            with cols[i % 3]:
                st.markdown(f"**{row[1]}**")
                if st.button(f"View Items ({row.Quantity:,.0f})", key=f"p_cat_{i}"):
                    st.session_state.sel_cat = row[1]
                    st.session_state.view = 'items'
                    st.rerun()

    # LAYER 4: PRODUCTS
    elif st.session_state.view == 'items':
        cust, month, cat = st.session_state.sel_cust, st.session_state.sel_order_month, st.session_state.sel_cat
        st.subheader(f"Final Order List: {month} — {cat}")
        
        final_df = df[
            (df['Customer Name'] == cust) & 
            (df['Order_Month'] == month) & 
            (df['Product Category'] == cat)
        ]
        
        # We group by Part Number and include the target delivery month
        items = final_df.groupby(['Product Name', 'Part Number', 'Month_Name'])['Quantity'].sum().reset_index()
        
        for _, row in items.iterrows():
            with st.expander(f"{row['Product Name']} [{row['Part Number']}]"):
                st.write(f"**Required Quantity:** {row['Quantity']:,.2f}")
                st.info(f"Target Delivery: Needs to reach the customer by **{row['Month_Name']}**")

# SALES VIEW (Your original logic)
else:
    st.info("You are in Sales View. Use the sidebar to switch to the Procurement Planner.")
    st.write("---")
    # This just shows the top level categories for now
    st.subheader("General Category Overview")
    cats = df.groupby('Product Category')['Quantity'].sum().sort_index()
    grid = st.columns(4)
    for i, (cat, total) in enumerate(cats.items()):
        with grid[i % 4]:
            st.metric(cat, f"{total:,.0f}")
