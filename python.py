# python.py

import streamlit as st
import pandas as pd
from google import genai
from google.genai.errors import APIError

# ==============================
# ⚙️ Cấu hình giao diện chính
# ==============================
st.set_page_config(
    page_title="📊 Phân Tích Báo Cáo Tài Chính",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# 🎨 Giao diện tiêu đề
# ==============================
st.markdown("""
<h1 style='text-align:center; color:#AE1C3F;'>📊 ỨNG DỤNG PHÂN TÍCH BÁO CÁO TÀI CHÍNH</h1>
<p style='text-align:center; color:gray;'>Phân tích tự động tốc độ tăng trưởng, tỷ trọng tài sản và đánh giá AI</p>
<hr style='border:1px solid #AE1C3F'>
""", unsafe_allow_html=True)

# ==============================
# 🔑 Nhập API Key trực tiếp
# ==============================
with st.expander("🔑 Cấu hình API Key Gemini (bắt buộc để phân tích AI)"):
    api_key = st.text_input("Nhập API Key của bạn tại đây:", type="password", placeholder="Ví dụ: AIzaSyA...")
    st.caption("👉 API Key chỉ được sử dụng cục bộ và không lưu lại trên máy chủ Streamlit Cloud.")

# ==============================
# 📤 Upload file Excel
# ==============================
uploaded_file = st.file_uploader(
    "1️⃣  Tải file Excel Báo cáo Tài chính (các cột: Chỉ tiêu | Năm trước | Năm sau)",
    type=["xlsx", "xls"]
)

# ==============================
# 🧮 Hàm xử lý dữ liệu
# ==============================
@st.cache_data
def process_financial_data(df):
    numeric_cols = ['Năm trước', 'Năm sau']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 1. Tốc độ tăng trưởng
    df['Tốc độ tăng trưởng (%)'] = (
        (df['Năm sau'] - df['Năm trước']) / df['Năm trước'].replace(0, 1e-9)
    ) * 100

    # 2. Tỷ trọng theo Tổng tài sản
    tong_tai_san = df[df['Chỉ tiêu'].str.contains('TỔNG CỘNG TÀI SẢN', case=False, na=False)]
    if tong_tai_san.empty:
        raise ValueError("Không tìm thấy chỉ tiêu 'TỔNG CỘNG TÀI SẢN'.")

    divisor_N_1 = tong_tai_san['Năm trước'].iloc[0] if tong_tai_san['Năm trước'].iloc[0] != 0 else 1e-9
    divisor_N = tong_tai_san['Năm sau'].iloc[0] if tong_tai_san['Năm sau'].iloc[0] != 0 else 1e-9

    df['Tỷ trọng Năm trước (%)'] = (df['Năm trước'] / divisor_N_1) * 100
    df['Tỷ trọng Năm sau (%)'] = (df['Năm sau'] / divisor_N) * 100
    
    return df

# ==============================
# 🤖 Hàm gọi Gemini AI
# ==============================
def get_ai_analysis(data_for_ai, api_key):
    try:
        client = genai.Client(api_key=api_key)
        model = 'gemini-2.5-flash'
        prompt = f"""
        Bạn là một chuyên gia phân tích tài chính. 
        Hãy nhận xét khách quan (3–4 đoạn) dựa trên dữ liệu sau:
        - Tốc độ tăng trưởng
        - Thay đổi cơ cấu tài sản
        - Chỉ số thanh toán hiện hành
        
        Dữ liệu cung cấp:
        {data_for_ai}
        """
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text
    except APIError as e:
        return f"⚠️ Lỗi khi gọi Gemini API: {e}"
    except Exception as e:
        return f"⚠️ Lỗi khác: {e}"

# ==============================
# 📊 Xử lý dữ liệu người dùng tải lên
# ==============================
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = ['Chỉ tiêu', 'Năm trước', 'Năm sau']
        df_result = process_financial_data(df.copy())

        st.subheader("📈 2️⃣ Tốc độ Tăng trưởng & Tỷ trọng Tài sản")
        st.dataframe(
            df_result.style.format({
                'Năm trước': '{:,.0f}',
                'Năm sau': '{:,.0f}',
                'Tốc độ tăng trưởng (%)': '{:.2f}%',
                'Tỷ trọng Năm trước (%)': '{:.2f}%',
                'Tỷ trọng Năm sau (%)': '{:.2f}%'
            }), use_container_width=True
        )

        # Tính chỉ số thanh toán
        st.subheader("💰 3️⃣ Các Chỉ số Tài chính Cơ bản")
        try:
            tsnh_n = df_result[df_result['Chỉ tiêu'].str.contains('TÀI SẢN NGẮN HẠN', case=False)]['Năm sau'].iloc[0]
            tsnh_n_1 = df_result[df_result['Chỉ tiêu'].str.contains('TÀI SẢN NGẮN HẠN', case=False)]['Năm trước'].iloc[0]
            no_ngan_han_N = df_result[df_result['Chỉ tiêu'].str.contains('NỢ NGẮN HẠN', case=False)]['Năm sau'].iloc[0]
            no_ngan_han_N_1 = df_result[df_result['Chỉ tiêu'].str.contains('NỢ NGẮN HẠN', case=False)]['Năm trước'].iloc[0]

            current_ratio_N = tsnh_n / no_ngan_han_N
            current_ratio_N_1 = tsnh_n_1 / no_ngan_han_N_1

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Thanh toán Hiện hành (Năm trước)", f"{current_ratio_N_1:.2f} lần")
            with col2:
                st.metric("Thanh toán Hiện hành (Năm sau)", f"{current_ratio_N:.2f} lần",
                          delta=f"{current_ratio_N - current_ratio_N_1:.2f}")
        except IndexError:
            st.warning("Thiếu chỉ tiêu 'TÀI SẢN NGẮN HẠN' hoặc 'NỢ NGẮN HẠN' trong file Excel.")
            current_ratio_N, current_ratio_N_1 = None, None

        # Phân tích AI
        st.subheader("🧠 4️⃣ Phân tích AI – Nhận xét Tình hình Tài chính")

        data_for_ai = pd.DataFrame({
            'Chỉ tiêu': [
                'Bảng dữ liệu đầy đủ',
                'Tăng trưởng Tài sản ngắn hạn (%)',
                'Thanh toán hiện hành (Năm trước)',
                'Thanh toán hiện hành (Năm sau)'
            ],
            'Giá trị': [
                df_result.to_markdown(index=False),
                f"{df_result[df_result['Chỉ tiêu'].str.contains('TÀI SẢN NGẮN HẠN', case=False)]['Tốc độ tăng trưởng (%)'].iloc[0]:.2f}%" if not df_result[df_result['Chỉ tiêu'].str.contains('TÀI SẢN NGẮN HẠN', case=False)].empty else 'N/A',
                f"{current_ratio_N_1}" if current_ratio_N_1 else 'N/A',
                f"{current_ratio_N}" if current_ratio_N else 'N/A'
            ]
        }).to_markdown(index=False)

        if st.button("🚀 Phân tích bằng Gemini AI"):
            if not api_key:
                st.error("❌ Vui lòng nhập API Key Gemini trước khi sử dụng tính năng này.")
            else:
                with st.spinner("🔍 Đang gửi dữ liệu đến Gemini AI..."):
                    result = get_ai_analysis(data_for_ai, api_key)
                    st.success("✅ Phân tích hoàn tất:")
                    st.info(result)

    except ValueError as ve:
        st.error(f"⚠️ Lỗi cấu trúc dữ liệu: {ve}")
    except Exception as e:
        st.error(f"⚠️ Lỗi khi xử lý file: {e}")
else:
    st.info("⬆️ Hãy tải lên file Excel để bắt đầu phân tích.")
