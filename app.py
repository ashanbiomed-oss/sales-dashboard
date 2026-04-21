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
st.set_page_config(page_title="Procurement & Sales Suite", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv('quotation_data_extracted.csv')
    df['Quotation Expecting Day'] = pd.to_datetime(df['Quotation Expecting Day'], errors='coerce')
    
    # PROCUREMENT LOGIC: Order date = Required date - 2 months
    df['Order_Placement_Date'] = df['Quotation Expecting Day'] - pd.DateOffset(months=2)
    
    # Original Customer Requirement Dates
    df['Year'] = df['Quotation Expecting Day'].dt.year
    df['Month_Name'] = df['Quotation Expecting Day'].dt.strftime('%B')
    
    # Procurement/Order Placement Dates
    df['Order_Year'] = df['Order_Placement_Date'].dt.year
    df['Order_Month'] = df['Order_Placement_Date'].dt.strftime('%B')
    df['Order_Month_Num'] = df['Order_Placement_Date'].dt.month
    
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
if 'mode' not in st.session_state: st.session_state.mode = 'Procurement Planner'
if 'view' not in st.session_state: st.session_state.view = 'main'

for key in ['sel_cust', 'sel_order_month', 'sel_cat']:
    if key not in st.session_state: st.session_state[key] = None

# --- 4. EXCEL EXPORT FUNCTION ---
def to_excel(dataframe):
    output = io.BytesIO()
    # Uses openpyxl (Ensure this is in requirements.txt!)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Procurement_Plan')
    return output.getvalue()

# --- 5. SIDEBAR ---
st.sidebar.header("Control Panel")
st.session_state.mode = st.sidebar.radio("Switch View:", ["Procurement Planner", "Sales View"])

st.sidebar.divider()
st.sidebar.subheader("Excel Export")

if st.sidebar.button("📊 Generate Detailed Excel Report"):
    report_df = df[[
        'Customer Name', 
        'Order_Month', 
        'Order_Year', 
        'Month_Name', 
        'Year', 
        'Product Category', 
        'Product Name', 
        'Part Number', 
        'Quantity'
    ]].copy()
    
    report_df.columns = [
        'Customer', 
        'Order Placement Month', 
        'Order Placement Year', 
        'Customer Required Month', 
        'Customer Required Year',
        'Category', 
        'Item Name', 
        'Part Number', 
        'Quantity'
    ]
    
    report_df = report_df.sort_values(['Order Placement Year', 'Order Placement Month'])
    
    excel_data = to_excel(report_df)
    st.sidebar.download_button(
        label="📥 Download Detailed Excel",
        data=excel_data,
        file_name="Detailed_Procurement_Plan.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if st.sidebar.button("🏠 Reset Dashboard Home"):
    st.session_state.view = 'main'
    st.rerun()

# --- 6. MAIN UI ---
st.title(f"{st.session_state.mode}")

if st.session_state.mode == "Procurement Planner":
    st.info("💡 **Goal:** Plan orders 2 months before customer requirement.")
    
    # BACK BUTTON
    if st.session_state.view != 'main':
        if st.button("⬅ Back"):
            if st.session_state.view == 'items': st.session_state.view = 'categories'
            elif st.session_state.view == 'categories': st.session_state.view = 'months'
            elif st.session_state.view == 'months': st.session_state.view = 'main'
            st.rerun()

    # LAYER 1: CUSTOMERS
    if st.session_state.view == 'main':
        st.subheader("1. Select Customer")
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
        st.subheader(f"2. Ordering Schedule for: {cust}")
        cust_df = df[df['Customer Name'] == cust]
        months = cust_df.groupby(['Order_Month_Num', 'Order_Month'])['Quantity'].sum().reset_index().sort_values('Order_Month_Num')
        
        cols = st.columns(4)
        for i, row in enumerate(months.itertuples()):
            with cols[i % 4]:
                st.metric(f"Order in {row.Order_Month}", f"{row.Quantity:,.2f}")
                if st.button(f"Open {row.Order_Month}", key=f"p_mo_{i}"):
                    st.session_state.sel_order_month = row.Order_Month
                    st.session_state.view = 'categories'
                    st.rerun()

    # LAYER 3: CATEGORIES
    elif st.session_state.view == 'categories':
        cust, month = st.session_state.sel_cust, st.session_state.sel_order_month
        st.subheader(f"3. Categories for {cust} (Order in {month})")
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
        st.subheader(f"4. Final Order List: {month} — {cat}")
        
        final_df = df[
            (df['Customer Name'] == cust) & 
            (df['Order_Month'] == month) & 
            (df['Product Category'] == cat)
        ]
        
        items = final_df.groupby(['Product Name', 'Part Number', 'Month_Name'])['Quantity'].sum().reset_index()
        
        for _, row in items.iterrows():
            with st.expander(f"{row['Product Name']} [{row['Part Number']}]"):
                st.write(f"**Quantity to Order:** {row['Quantity']:,.2f}")
                st.warning(f"This order is needed for delivery in **{row['Month_Name']}**.")

else:
    st.info("Sales View active. Switching modes in the sidebar resets the drill-down.")
    st.bar_chart(df.groupby('Product Category')['Quantity'].sum())
