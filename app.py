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
    df = pd.read_csv('quotation_data_extracted.csv')
    df['Quotation Expecting Day'] = pd.to_datetime(df['Quotation Expecting Day'], errors='coerce')
    
    # --- PROCUREMENT LOGIC (2 Months Lead Time) ---
    df['Order_Placement_Date'] = df['Quotation_Expecting_Day'] - pd.DateOffset(months=2)
    
    # Extract Original Dates
    df['Year'] = df['Quotation_Expecting_Day'].dt.year
    df['Month_Name'] = df['Quotation_Expecting_Day'].dt.strftime('%B')
    
    # Extract Order Placement Dates
    df['Order_Year'] = df['Order_Placement_Date'].dt.year
    df['Order_Month'] = df['Order_Placement_Date'].dt.strftime('%B')
    df['Order_Month_Num'] = df['Order_Placement_Date'].dt.month
    
    df = df.fillna({'Part Number': 'N/A', 'Product Name': 'Unknown', 'Customer Name': 'Unknown', 'Quantity': 0})
    return df

df = load_data()

# --- 3. SESSION STATE ---
if 'mode' not in st.session_state: st.session_state.mode = 'Sales'
if 'view' not in st.session_state: st.session_state.view = 'main'
# Drill-down states
states = ['sel_cust', 'sel_order_month', 'sel_cat', 'sel_year']
for s in states:
    if s not in st.session_state: st.session_state[s] = None

# --- 4. SIDEBAR & EXCEL EXPORT ---
st.sidebar.header("Control Panel")
st.session_state.mode = st.sidebar.radio("Switch View:", ["Sales View", "Procurement Planner"])

# Excel Export Function
def to_excel(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Procurement_Plan')
    return output.getvalue()

st.sidebar.divider()
if st.sidebar.button("📊 Export Full Procurement Plan"):
    proc_df = df[['Customer Name', 'Order_Month', 'Order_Year', 'Product Category', 'Product Name', 'Part Number', 'Quantity', 'Month_Name']]
    proc_df.columns = ['Customer', 'Order Placement Month', 'Order Year', 'Category', 'Item', 'Part#', 'Qty', 'Required For Month']
    excel_data = to_excel(proc_df)
    st.sidebar.download_button("📥 Download Excel", data=excel_data, file_name="Procurement_Schedule.xlsx")

if st.sidebar.button("🏠 Reset Home"):
    st.session_state.view = 'main'
    st.rerun()

# --- 5. MAIN UI ---
st.title(f"{st.session_state.mode}")
st.caption(f"Lead time logic: Order date = Required date - 2 months")

# --- PROCUREMENET PLANNER LOGIC ---
if st.session_state.mode == "Procurement Planner":
    
    # BACK BUTTON
    if st.session_state.view != 'main':
        if st.button("⬅ Back"):
            if st.session_state.view == 'items': st.session_state.view = 'categories'
            elif st.session_state.view == 'categories': st.session_state.view = 'months'
            elif st.session_state.view == 'months': st.session_state.view = 'main'
            st.rerun()

    # LAYER 1: CUSTOMERS
    if st.session_state.view == 'main':
        st.subheader("Select Customer to view Order Schedule")
        cust_list = sorted(df['Customer Name'].unique())
        cols = st.columns(3)
        for i, cust in enumerate(cust_list):
            with cols[i % 3]:
                if st.button(cust, key=f"cust_{i}", use_container_width=True):
                    st.session_state.sel_cust = cust
                    st.session_state.view = 'months'
                    st.rerun()

    # LAYER 2: MONTHS (Order Placement Month)
    elif st.session_state.view == 'months':
        cust = st.session_state.sel_cust
        st.subheader(f"Ordering Schedule for {cust}")
        cust_df = df[df['Customer Name'] == cust]
        months = cust_df.groupby(['Order_Month_Num', 'Order_Month'])['Quantity'].sum().reset_index().sort_values('Order_Month_Num')
        
        cols = st.columns(4)
        for i, row in enumerate(months.itertuples()):
            with cols[i % 4]:
                st.metric(f"Order in {row.Order_Month}", f"{int(row.Quantity):,}")
                if st.button(f"View {row.Order_Month} Orders", key=f"m_{i}"):
                    st.session_state.sel_order_month = row.Order_Month
                    st.session_state.view = 'categories'
                    st.rerun()

    # LAYER 3: CATEGORIES
    elif st.session_state.view == 'categories':
        cust, month = st.session_state.sel_cust, st.session_state.sel_order_month
        st.subheader(f"Categories to order in {month} for {cust}")
        cat_df = df[(df['Customer Name'] == cust) & (df['Order_Month'] == month)]
        cats = cat_df.groupby('Product Category')['Quantity'].sum().reset_index()
        
        cols = st.columns(3)
        for i, row in enumerate(cats.itertuples()):
            with cols[i % 3]:
                st.markdown(f"**{row[1]}**")
                if st.button(f"See Items ({int(row.Quantity)})", key=f"cat_{i}"):
                    st.session_state.sel_cat = row[1]
                    st.session_state.view = 'items'
                    st.rerun()

    # LAYER 4: PRODUCTS
    elif st.session_state.view == 'items':
        cust, month, cat = st.session_state.sel_cust, st.session_state.sel_order_month, st.session_state.sel_cat
        st.subheader(f"Place these orders in {month} ({cat})")
        
        final_df = df[(df['Customer Name'] == cust) & (df['Order_Month'] == month) & (df['Product Category'] == cat)]
        
        items = final_df.groupby(['Product Name', 'Part Number', 'Month_Name'])['Quantity'].sum().reset_index()
        
        for _, row in items.iterrows():
            with st.expander(f"{row['Product Name']} [{row['Part Number']}]"):
                st.write(f"**Quantity to Order:** {row['Quantity']:.2f}")
                st.info(f"Target Delivery: Required by the customer in **{row['Month_Name']}**")

# --- RETAIN OLD SALES VIEW LOGIC ---
else:
    st.info("You are in Sales View. Switch to Procurement Planner in the sidebar to see the ordering schedule.")
    # (The code for your previous Sales Dashboard layers would go here)
