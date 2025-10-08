# python.py

import streamlit as st
import pandas as pd
import io
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
<p style='text-align:center; color:gray;'>Phân tích tự động, trò chuyện trực tiếp với AI và xuất báo cáo chi tiết</p>
<hr style='border:1px solid #AE1C3F'>
""", unsafe_allow_html=True)

# ==============================
# 🔑 Nhập API Key trực tiếp
# ==============================
with st.sidebar:
    st.markdown("### 🔑 Cấu hình API Key Gemini")
    api_key = st.text_input("Nhập API Key tại đây:", type="password", placeholder="AIzaSyA...")
    st.caption("👉 API Key chỉ lưu tạm thời, không gửi lên máy chủ.")

# ==============================
# 🧮 Hàm xử lý dữ liệu tài chính
# ==============================
@st.cache_data
def process_financial_data(df):
    df['Năm trước'] = pd.to_numeric(df['Năm trước'], errors='coerce').fillna(0)
    df['Năm sau'] = pd.to_numeric(df['Năm sau'], errors='coerce').fillna(0)

    # Tốc độ tăng trưởng
    df['Tốc độ tăng trưởng (%)'] = (
        (df['Năm sau'] - df['Năm trước']) / df['Năm trước'].replace(0, 1e-9)
    ) * 100

    # Tỷ trọng theo tổng tài sản
    tong_tai_san = df[df['Chỉ tiêu'].str.contains('TỔNG CỘNG TÀI SẢN', case=False, na=False)]
    if tong_tai_san.empty:
        raise ValueError("Không tìm thấy chỉ tiêu 'TỔNG CỘNG TÀI SẢN'.")
    divisor_N_1 = tong_tai_san['Năm trước'].iloc[0] or 1e-9
    divisor_N = tong_tai_san['Năm sau'].iloc[0] or 1e-9
    df['Tỷ trọng Năm trước (%)'] = (df['Năm trước'] / divisor_N_1) * 100
    df['Tỷ trọng Năm sau (%)'] = (df['Năm sau'] / divisor_N) * 100
    return df

# ==============================
# 🤖 Hàm gọi Gemini AI
# ==============================
def call_gemini(prompt, api_key):
    try:
        client = genai.Client(api_key=api_key)
        model = "gemini-2.5-flash"
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text
    except APIError as e:
        return f"⚠️ Lỗi API Gemini: {e}"
    except Exception as e:
        return f"⚠️ Lỗi khác: {e}"

# ==============================
# 📤 Upload file Excel
# ==============================
uploaded_file = st.file_uploader(
    "📂 Tải file Excel Báo cáo Tài chính (Chỉ tiêu | Năm trước | Năm sau)",
    type=["xlsx", "xls"]
)

# ==============================
# 🧩 Xử lý khi có file
# ==============================
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = ['Chỉ tiêu', 'Năm trước', 'Năm sau']
        df_result = process_financial_data(df.copy())

        # ========== GIAO DIỆN 2 CỘT ==========
        col_left, col_right = st.columns([2, 1])

        # =======================
        # 📈 CỘT TRÁI: BẢNG PHÂN TÍCH
        # =======================
        with col_left:
            st.subheader("📊 Bảng phân tích dữ liệu")
            st.dataframe(
                df_result.style.format({
                    'Năm trước': '{:,.0f}',
                    'Năm sau': '{:,.0f}',
                    'Tốc độ tăng trưởng (%)': '{:.2f}%',
                    'Tỷ trọng Năm trước (%)': '{:.2f}%',
                    'Tỷ trọng Năm sau (%)': '{:.2f}%'
                }),
                use_container_width=True
            )

            # 💰 Tính chỉ số thanh toán
            try:
                tsnh_n = df_result[df_result['Chỉ tiêu'].str.contains('TÀI SẢN NGẮN HẠN', case=False)]['Năm sau'].iloc[0]
                tsnh_n_1 = df_result[df_result['Chỉ tiêu'].str.contains('TÀI SẢN NGẮN HẠN', case=False)]['Năm trước'].iloc[0]
                no_ngan_han_N = df_result[df_result['Chỉ tiêu'].str.contains('NỢ NGẮN HẠN', case=False)]['Năm sau'].iloc[0]
                no_ngan_han_N_1 = df_result[df_result['Chỉ tiêu'].str.contains('NỢ NGẮN HẠN', case=False)]['Năm trước'].iloc[0]
                ratio_N = tsnh_n / no_ngan_han_N
                ratio_N_1 = tsnh_n_1 / no_ngan_han_N_1
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Thanh toán hiện hành (Năm trước)", f"{ratio_N_1:.2f} lần")
                with col2:
                    st.metric("Thanh toán hiện hành (Năm sau)", f"{ratio_N:.2f} lần",
                              delta=f"{ratio_N - ratio_N_1:.2f}")
            except IndexError:
                st.warning("⚠️ Thiếu chỉ tiêu 'TÀI SẢN NGẮN HẠN' hoặc 'NỢ NGẮN HẠN' trong dữ liệu.")

            # 📥 Xuất Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_result.to_excel(writer, index=False, sheet_name="Phan_tich_tai_chinh")
            st.download_button(
                label="💾 Tải xuống Báo cáo Excel",
                data=buffer.getvalue(),
                file_name="Bao_cao_Phan_tich_Tai_chinh.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # =======================
        # 💬 CỘT PHẢI: KHUNG CHAT AI
        # =======================
        with col_right:
            st.subheader("💬 Trò chuyện với Gemini AI")

            # Tạo session chat
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []

            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.chat_message("user").markdown(msg["content"])
                else:
                    st.chat_message("assistant").markdown(msg["content"])

            user_input = st.chat_input("Nhập câu hỏi hoặc yêu cầu phân tích sâu hơn...")
            if user_input:
                if not api_key:
                    st.error("❌ Vui lòng nhập API Key trước khi trò chuyện với AI.")
                else:
                    st.chat_message("user").markdown(user_input)
                    prompt = f"""
                    Dưới đây là dữ liệu báo cáo tài chính (Markdown):
                    {df_result.to_markdown(index=False)}

                    Yêu cầu của người dùng: {user_input}

                    Hãy phân tích sâu theo hướng chuyên gia tài chính, 
                    cung cấp insight về hiệu quả hoạt động, khả năng thanh toán, 
                    cơ cấu tài sản và rủi ro tiềm ẩn (nếu có).
                    """
                    with st.spinner("🤖 Đang phân tích với Gemini..."):
                        ai_response = call_gemini(prompt, api_key)
                        st.chat_message("assistant").markdown(ai_response)

                    st.session_state.chat_history.append({"role": "user", "content": user_input})
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_response})

    except Exception as e:
        st.error(f"⚠️ Lỗi khi xử lý file: {e}")
else:
    st.info("⬆️ Vui lòng tải lên file Excel để bắt đầu phân tích.")
