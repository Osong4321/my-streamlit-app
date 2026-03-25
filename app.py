import streamlit as st
from PIL import Image # 이미지 파일을 읽기 위해 필요
import pandas as pd
from datetime import datetime, timedelta, time
import time as tm
import os
import json
import gspread
from google.oauth2.service_account import Credentials


# =========================================================================
# 1. 페이지 기본 설정
# =========================================================================
# [중요] 모든 Streamlit 함수 중 가장 먼저 딱 한 번만 실행되어야 합니다.
st.set_page_config(
    page_title="ATLAS - QC 시험일정 자동화", # 브라우저 탭에 뜰 제목
    page_icon="🧪",                       # 브라우저 탭 아이콘 (🔬 또는 🧪 중 선택)
    layout="wide"                         # 넓은 화면 모드
)

# 관리자 인증 상태를 기억하기 위한 변수 설정
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False

# =========================================================================
# 2. 구글 시트 연결 (CSV 완전 대체)
# =========================================================================
@st.cache_resource
def init_connection():
    key_dict = json.loads(st.secrets["google_key"])
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
    return gspread.authorize(creds)

client = init_connection()

# URL 중복 수정 완료
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Ejo6Yse0iZjFc2V45yuAVNjw7Bc6VAyqF5aV73iRTng/edit"
doc = client.open_by_url(SHEET_URL)

ws_process = doc.worksheet("공정기록")
ws_schedule = doc.worksheet("시험일정")
ws_master = doc.worksheet("Master") # 마스터 리스트가 들어있는 탭 이름
ws_guestbook = doc.worksheet("방명록")

# =========================================================================
# 3. 데이터 입출력 함수 (100% 구글 시트 전용)
# =========================================================================

def save_schedule(category, p_code, batch, tester, sample, point, item, spec_bug, status, inst_date, start_date, add_incub, end_date, deadline, time_status, qct):
    # 16개 열 순서대로 리스트 생성
    row = [category, p_code, batch, tester, sample, point, item, spec_bug, status, inst_date, start_date, add_incub, end_date, deadline, time_status, qct]
    ws_schedule.append_row(row)

def load_data(worksheet):
    records = worksheet.get_all_records()
    return pd.DataFrame(records)

def save_process(batch_no, proc_name, start_time, end_time, note):
    # (주의) 구글 시트 '공정기록' 탭 1행이 [Batch No., 공정명, 시작시간, 종료시간, 비고] 5개 열이라고 가정
    ws_process.append_row([batch_no, proc_name, start_time, end_time, note])

def save_guestbook(name, msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws_guestbook.append_row([now, name, msg])

# =========================================================================
# 4. 사이드바 구성
# =========================================================================
st.markdown(
    """
    <style>
    /* 사이드바 내부 전체 컨테이너의 하단 여백 제거 */
    [data-testid="stSidebarContent"] {
        padding-bottom: 0px !important;
    }

    /* 로고 컨테이너를 더 아래로 밀착 */
    .sidebar-footer {
        margin-top: auto; 
        padding-top: 5px;
        padding-bottom: 5px; /* 20px에서 5px로 줄여서 더 바닥으로! */
        text-align: center;
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- [구성] 사이드바 내용 ---
with st.sidebar:
    # [1] 상단 제목 및 메뉴
    st.title("🔬 ATLAS")
    st.write("---")

    menu = st.radio(
        "이동할 페이지를 선택하세요:", 
        [
            "🏠 홈 (Home)", 
            "📅 시험 일정 관리", 
            "📊 대시보드 (Dashboard)", 
            "📖 항목 마스터 리스트",
            "📝 공정 기록 등록",      
            "🛠️ 공정별 일정 현황",     
            "🗣️ 방명록 (Guestbook)"
        ]
    )

    # [2] ⭐ 하단 로고 이미지 (CI.png) ⭐
    # CSS의 margin-top: auto 덕분에 메뉴가 적어도 항상 맨 아래에 붙습니다.
    st.markdown('<div class="sidebar-footer">', unsafe_allow_html=True)
    try:
        # 하단에 CI 로고 표시
        st.image("CI.png", use_container_width=True) 
        st.caption("© 2026 Daewoong Luphere QC Team")
    except:
        # 이미지가 없을 때를 대비한 텍스트 출력
        st.markdown("### 🏢 Daewoong Luphere QC")
    st.markdown('</div>', unsafe_allow_html=True)
# =========================================================================
# 5. 메인 화면 구성
# =========================================================================
if menu == "🏠 홈 (Home)":
    st.title("🏠 미생물 파트 통합 관리 시스템")
    st.write("오송루피어QC팀 미생물파트 시험일정 자동화 시스템입니다.")
    st.write("---")
    st.info("💡 구글 스프레드시트 클라우드 연동이 완료되어 24시간 안전하게 데이터가 보관됩니다!")
    st.subheader("ATLAS (Automated Trend Learning and Analysis System) 📌 시스템 주요 기능")
    st.markdown("""
    1. **📝 공정 기록 등록**: 공정별 작업 시간을 수기 및 클릭으로 간편하게 기록
    2. **🛠️ 공정별 일정 현황**: 전체 공정의 흐름을 날짜별/배치별로 시각화 (차트)
    3. **📅 시험 일정 관리**: 무균/엔도톡신 등 시험 일정 자동 계산 및 마감 관리
    4. **📊 대시보드**: 전체 업무 현황과 진행률을 한눈에 파악
    """)

elif menu == "📊 대시보드 (Dashboard)":
    st.title("📊 시험 일정 현황 대시보드")

    # 1. 📅 실시간 날짜 계산 (기본값 설정)
    today = datetime.now().date()
    seven_days_later = today + timedelta(days=7)
    
    # 2. 날짜 및 검색 필터 (상단에 통합)
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        start_date = st.date_input("조회 시작일", value=today)
    with col2:
        end_date = st.date_input("조회 종료일", value=seven_days_later)
    with col3:
        batch_keyword = st.text_input("Batch No. 검색", placeholder="예: MFT031 (비워두면 전체 조회)")

    # 3. 데이터 로드 및 필터링
    df_schedule = load_data(ws_schedule)
    
    if not df_schedule.empty:
        # 날짜 형식 변환 및 필터링 준비
        df_schedule['Start'] = pd.to_datetime(df_schedule['시험시작일'], errors='coerce')
        df_schedule['End'] = pd.to_datetime(df_schedule['예상종료일'], errors='coerce')
        df_schedule['Deadline'] = pd.to_datetime(df_schedule['마감기한'], errors='coerce')
        
        # [핵심] 선택한 날짜 범위 내의 데이터만 필터링
        # 시작일이 조회종료일보다 작고, 종료일이 조회시작일보다 큰 데이터 (기간 중첩)
        mask = (df_schedule['Start'].dt.date <= end_date) & (df_schedule['End'].dt.date >= start_date)
        display_df = df_schedule[mask].copy()

        # Batch No. 검색 필터 적용
        if batch_keyword:
            display_df = display_df[display_df['Batch No.'].astype(str).str.contains(batch_keyword, case=False, na=False)]

        # 4. 상단 메트릭 (필터링된 결과 기준)
        m1, m2, m3, m4 = st.columns(4)
        total_cnt = len(display_df)
        ing_cnt = len(display_df[display_df['진행여부'] == "진행 중"])
        done_cnt = len(display_df[display_df['진행여부'] == "완료"])
        over_cnt = len(display_df[display_df['기한상태'].str.contains("초과", na=False)])
        
        m1.metric("조회 기간 내 시험", f"{total_cnt}건")
        m2.metric("진행 중 🟢", f"{ing_cnt}건")
        m3.metric("완료 🔵", f"{done_cnt}건")
        m4.metric("기한 초과 🔴", f"{over_cnt}건")
        
        st.write("---")
        st.subheader("📅 한눈에 보는 시험 일정표")
        
        if display_df.empty:
            st.info("📊 선택한 기간 내에 해당하는 시험 일정이 없습니다.")
        else:
            # 5. 그리드 차트 생성 로직
            try:
                date_range = pd.date_range(start=start_date, end=end_date)
                date_strs = [d.strftime('%m/%d') for d in date_range] 
                grid_data = []
                
                for idx, row in display_df.iterrows():
                    display_name = f"{row['Batch No.']} ({row['시험항목']})"
                    row_data = {'시험 정보': display_name}
                    is_empty_row = True 
                    
                    for d_idx, single_date in enumerate(date_range):
                        date_str = date_strs[d_idx]
                        cell_val = ""
                        curr_d = single_date.date()
                        
                        # 마감 표시
                        if pd.notna(row['Deadline']) and curr_d == row['Deadline'].date():
                            cell_val = "마감"
                            is_empty_row = False
                        # 진행 기간 표시
                        elif pd.notna(row['Start']) and pd.notna(row['End']) and row['Start'].date() <= curr_d <= row['End'].date():
                            cell_val = f"진행_{row['시험항목']}"
                            is_empty_row = False
                            
                        row_data[date_str] = cell_val
                    
                    if not is_empty_row:
                        grid_data.append(row_data)
                
                if grid_data:
                    grid_df = pd.DataFrame(grid_data).set_index('시험 정보')
                    
                    def color_cells(val):
                        if "진행_무균시험" in val: return 'background-color: #FFFF00; color: #FFFF00;'
                        elif "진행_엔도톡신" in val: return 'background-color: #C1E1C1; color: #C1E1C1;'
                        elif "진행" in val: return 'background-color: #E0E0E0; color: #E0E0E0;'
                        elif val == "마감": return 'background-color: #FF4B4B; color: #FFFFFF; font-weight: bold; text-align: center;' 
                        return ''
                    
                    styled_grid = grid_df.style.map(color_cells)
                    st.dataframe(styled_grid, use_container_width=True)
                    st.caption("🟡 노란색: 무균시험 | 🟢 연한 초록색: 엔도톡신시험 | 🔴 빨간색: 마감기한")
            
            except Exception as e:
                st.error(f"일정표를 구성하는 중 오류가 발생했습니다: {e}")
                
elif menu == "📅 시험 일정 관리":
    st.title("📅 시험 일정 자동 계산 및 기록 (16열 시스템)")

    # [마스터 데이터 정의 - 가이드 탭과 동일하게 유지]
    df_master_raw = load_data(ws_master) # 구글 시트 로드
    if df_master_raw.empty:
        st.error("❌ Master 시트에 데이터가 없습니다. 시트를 확인해주세요!")
        st.stop()
    
    # 데이터 정리 (공백 제거 등)
    df_master = df_master_raw.copy()
    df_master.columns = [c.strip() for c in df_master.columns]

    col1, col2 = st.columns(2)
    with col1:
        # 3번 메뉴: 이제 df_master는 구글 시트에서 가져온 데이터입니다!
        sample_options = ["선택해주세요"] + sorted(df_master["검체명"].unique().tolist())
        sample_type = st.selectbox("1. 시험검체를 선택하세요", sample_options)
        
        # 마스터 데이터 연동 (검체 선택 시 품목코드, 구분 자동 추출)
        if sample_type != "선택해주세요":
            target_row = df_master[df_master["검체명"] == sample_type].iloc[0]
            current_cat = target_row["구분"]
            current_code = target_row["품목코드"]
            current_spec = target_row["특정미생물"]
            
            # 🆕 시점(Point) 처리
            point_options = ["-"]
            if current_cat == "안정성":
                point_options = [p.strip() + "M" for p in str(target_row["주기"]).split(',')]
            
            # 시험 항목 리스트 생성
            base_tests = [t.strip() for t in str(target_row["필수시험"]).split(',')]
            if sample_type == "기타(직접 입력)":
                base_tests = ["Sterility", "MLT", "endotoxin", "GPT", "직접 입력"]
        else:
            current_cat, current_code, current_spec = "-", "-", "-"
            point_options = ["-"]
            base_tests = ["검체를 먼저 선택하세요"]

        batch_no = st.text_input("2. Batch No.를 입력하세요", placeholder="예: LP24001")
        tester = st.text_input("3. 시험자를 입력하세요", placeholder="예: 홍길동")
        
        # 🆕 시점 및 특정미생물 확인
        c1, c2 = st.columns(2)
        with c1: point = st.selectbox("4. 시험 시점", point_options)
        with c2: test_item = st.selectbox("5. 시험항목", base_tests)
        
        status = st.selectbox("6. 진행 여부", ["대기 중", "진행 중", "완료", "보류"])

    with col2:
        # 7~10번 입력 및 계산
        instruction_date = st.date_input("7. 시험지시일")
        is_pending = status in ["대기 중", "보류"]
        test_date = st.date_input("8. 시험시작일", disabled=is_pending)
        deadline_date = st.date_input("9. 마감 기한")
        
        add_incubation = st.checkbox("➕ 추가 배양(4일 연장)") if "Sterility" in test_item else False
        
        # 날짜 계산 로직
        if sample_type != "선택해주세요":
            days = 0
            if "Sterility" in test_item: days = 18 if add_incubation else 14
            elif "MLT" in test_item: days = 7
            
            if is_pending:
                end_date_str, qct_days, color, time_status = "미정", 0, "#FF4B4B", f"{status} 🔴"
                save_start, save_end = "-", "-"
            else:
                end_date = test_date + timedelta(days=days)
                end_date_str = end_date.strftime('%Y-%m-%d')
                qct_days = (end_date - instruction_date).days
                time_status = "초과 🔴" if end_date > deadline_date else "준수 🟢"
                color = "#FF4B4B" if end_date > deadline_date else "#00CC96"
                save_start, save_end = test_date.strftime('%Y-%m-%d'), end_date_str

            # 안내 박스
            st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid {color};'>
                    <p style='margin:0;'>📊 <b>구분:</b> {current_cat} | <b>코드:</b> {current_code}</p>
                    <h3 style='margin:10px 0; color: {color};'>{time_status} 예상 종료: {end_date_str}</h3>
                    <h4 style='margin:0;'>⏱️ QCT: {qct_days}일</h4>
                </div>
            """, unsafe_allow_html=True)

            if st.button("💾 16열 데이터로 저장하기", use_container_width=True):
                save_schedule(
                    current_cat, current_code, batch_no, tester, sample_type, point, test_item, current_spec,
                    status, instruction_date.strftime('%Y-%m-%d'), save_start,
                    "O" if add_incubation else "X", save_end,
                    deadline_date.strftime('%Y-%m-%d'), time_status, qct_days
                )
                st.success("✅ 마스터 연동 데이터가 저장되었습니다!")
                tm.sleep(1); st.rerun()

# ---------------------------------------------------------
    # [시작점] 여기서부터 교체하세요!
    # ---------------------------------------------------------
    st.divider()
    tab1, tab2 = st.tabs(["🔍 시험 일정 검색", "🛠️ 전체 일정 관리"])
    
    # ⭐ 16개 전체 컬럼 순서 정의 (구글 시트 헤더와 반드시 일치해야 함)
    cols_order = ["구분", "품목코드", "Batch No.", "시험자", "시험검체", "시점", "시험항목", "특정미생물", "진행여부", "시험지시일", "시험시작일", "추가배양", "예상종료일", "마감기한", "기한상태", "QCT"]

    with tab1:
        st.subheader("🔍 일정 검색 및 체크박스 비교 분석")
        
        # 1. 데이터 불러오기
        df_raw = load_data(ws_schedule)
        
        if not df_raw.empty:
            # 공백 제거 및 컬럼 동기화
            df_raw.columns = [c.strip() for c in df_raw.columns]
            
            # 🔥 [QCT 로직 사수] 시트에서 불러온 날짜로 QCT 재계산 (데이터 무결성 확보)
            df_raw['예상종료일_dt'] = pd.to_datetime(df_raw['예상종료일'], errors='coerce')
            df_raw['시험지시일_dt'] = pd.to_datetime(df_raw['시험지시일'], errors='coerce')
            df_raw['QCT'] = (df_raw['예상종료일_dt'] - df_raw['시험지시일_dt']).dt.days.fillna(0).astype(int)
            
            # 2. 검색 UI
            s_col1, s_col2 = st.columns([1, 2])
            with s_col1:
                search_keyword = st.text_input("Batch No. 검색", placeholder="예: LP24001", key="tab1_search")
            with s_col2:
                filter_dates = st.date_input("기간 조회 (지시일 기준)", value=[], key="tab1_date")
            
            # 3. 데이터 필터링
            df_filtered = df_raw[cols_order].copy() # 16열 순서대로 정렬
            
            if search_keyword:
                df_filtered = df_filtered[df_filtered['Batch No.'].astype(str).str.contains(search_keyword, case=False, na=False)]
            
            if len(filter_dates) == 2:
                start_d, end_d = filter_dates
                mask = (df_raw['시험지시일_dt'].dt.date >= start_d) & (df_raw['시험지시일_dt'].dt.date <= end_d)
                df_filtered = df_filtered.loc[mask]

            if not df_filtered.empty:
                # 4. 체크박스 선택 UI
                df_with_selections = df_filtered.copy()
                df_with_selections.insert(0, "✅ 선택", False)
                
                edited_df = st.data_editor(
                    df_with_selections.iloc[::-1], # 최신순 정렬
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "✅ 선택": st.column_config.CheckboxColumn("선택", default=False),
                        "QCT": st.column_config.NumberColumn("QCT", format="%d 일")
                    },
                    disabled=[col for col in df_with_selections.columns if col != "✅ 선택"],
                    key="tab1_editor"
                )

                # 5. 실시간 QCT 분석 결과 표시
                selected_rows = edited_df[edited_df["✅ 선택"] == True]
                # 체크한 게 있으면 체크된 것만, 없으면 검색 결과 전체를 분석 대상으포 함
                df_analysis = selected_rows if not selected_rows.empty else edited_df
                
                st.write("---")
                avg_val = df_analysis['QCT'].mean()
                m1, m2, m3 = st.columns(3)
                m1.metric("📊 분석 건수", f"{len(df_analysis)} 건")
                m2.metric("⏱️ 평균 QCT", f"{avg_val:.1f} 일")
                m3.metric("⚠️ 최대 소요", f"{df_analysis['QCT'].max()} 일")
                st.caption("💡 표에서 항목을 체크하면 해당 항목들만의 평균 QCT가 계산됩니다.")
        else:
            st.info("기록된 데이터가 없습니다.")

    with tab2:
        st.subheader("🛠️ 전체 일정 수정 및 삭제")
        df_manage = load_data(ws_schedule)
        
        if not df_manage.empty:
            df_manage.columns = [c.strip() for c in df_manage.columns]
            df_reversed = df_manage[cols_order].iloc[::-1].reset_index(drop=True)
            
            # 날짜 정규화 (수정 시 달력 팝업을 위해)
            date_cols = ["시험지시일", "시험시작일", "예상종료일", "마감기한"]
            for col in date_cols:
                df_reversed[col] = pd.to_datetime(df_reversed[col], errors='coerce').dt.date
            
            edited_m = st.data_editor(
                df_reversed,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "진행여부": st.column_config.SelectboxColumn("진행여부", options=["대기 중", "진행 중", "완료", "보류"]),
                    "기한상태": st.column_config.SelectboxColumn("기한상태", options=["준수 🟢", "초과 🔴", "대기 중 🟡", "보류 🔴"])
                },
                key="tab2_editor"
            )
            
            if st.button("💾 변경사항 구글 시트에 저장하기", type="primary", use_container_width=True):
                # 저장용 데이터프레임 정리
                final_df = edited_m.iloc[::-1].copy()
                for col in date_cols:
                    final_df[col] = final_df[col].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) and hasattr(x, 'strftime') else "-")
                
                ws_schedule.clear()
                ws_schedule.update([final_df.columns.values.tolist()] + final_df.values.tolist())
                st.success("✅ 데이터가 안전하게 저장되었습니다!")
                tm.sleep(1) # 'time' 대신 'tm' 사용 확인!
                st.rerun()

elif menu == "📖 항목 마스터 리스트":
    st.title("📖 미생물 시험 가이드")
    st.info("💡 필터를 선택하지 않으면 전체 목록이 나타납니다.")

    # 1. 데이터 구성 (기존 데이터 유지)
    master_list = [
        ["원료", "폴리(디엘-락티드)", "02A1001191", "MLT, endotoxin", "-", "-"],
        ["원료", "Trypticsoy broth(Liquid)(Synergi)", "1300281", "GPT", "-", "-"],
        ["원료", "Tryptic soy broth", "1000488", "GPT", "-", "-"],
        ["원료", "Leuprolide Acetate(PPL, India)", "1000325", "MLT, endotoxin", "-", "-"],
        ["원료", "세마글루티드", "3300311", "MLT, endotoxin", "-", "E.coli"],
        ["원료", "D-Mannitol (Pyrogen Free)", "1000026", "MLT, endotoxin", "-", "E.coli"],
        ["원료", "Gelatin", "1001175", "MLT", "-", "E.coli, Salmonella"],
        ["원료", "Hydroxypropyl betadex(EP,Ashland)", "1301096", "MLT, endotoxin", "-", "E.coli, Salmonella"],
        ["자재", "LEU Syringe 104mm(블루잉크제외)", "2303718", "Sterility", "-", "-"],
        ["자재", "LLA Big", "2004102", "Sterility", "-", "-"],
        ["자재", "LLA Big(임상)", "4302447", "Sterility", "-", "-"],
        ["자재", "LEU Glass Syringe Barel 104mm", "4302270", "Sterility", "-", "-"],
        ["자재", "루피어데포주 3.75mg 24게이지 니들", "2001268", "Sterility", "-", "-"],
        ["자재", "Needle 23G 1-1/2 IN FLT (임상)(멸균)", "4302117", "Sterility", "-", "-"],
        ["자재", "Needle 23G 1-1/2 IN FLT (멸균)", "2302374", "Sterility", "-", "-"],
        ["자재", "LEU Syringe 104mm", "2004101", "Sterility", "-", "-"],
        ["자재", "루피어데포주 3.75mg PP 마개", "2001274", "Sterility", "-", "-"],
        ["자재", "Needle 23G 1IN RB_TW (멸균)", "2302293", "Sterility", "-", "-"],
        ["자재", "루피어데포주 3.75mg 테프론 고무전", "2300927", "endotoxin", "-", "-"],
        ["제품", "DWJ1483 3.75mg(류프로렐린)", "9301926", "Sterility, endotoxin", "-", "-"],
        ["제품", "루피어데포주 3.75MG(류프로렐린아세트산염) 완제품", "9000226", "Sterility", "-", "-"],
        ["제품", "루피어데포주 3.75mg 임상_YoungPEAL", "9300104", "Sterility", "-", "-"],
        ["제품", "DWP1401 2주 위약", "4302132", "Sterility, endotoxin", "-", "-"],
        ["제품", "DWP1401 2주 시험약", "4302131", "Sterility, endotoxin", "-", "-"],
        ["공정", "DWJ108U 30mg(류프로라이드)", "9300842", "Sterility, endotoxin", "-", "-"],
        ["공정", "루피어데포주3.75MG(류프로렐린아세트산염) 반제품", "8000101", "Sterility", "-", "-"],
        ["안정성", "루피어데포주 3.75mg 완제(시판후)", "9000226", "Sterility", "0, 12, 18, 24", "-"],
        ["안정성", "루피어데포주 3.75mg 완제(장기)", "9000226", "Sterility", "0, 12, 24", "-"],
        ["안정성", "Needle 23G 1-1/2 IN (멸균) 안정성", "2302374", "Sterility", "0, 6, 12, 24, 36", "-"],
        ["안정성", "Needle 23G 1IN RB_TW (멸균) 안정성", "2302374", "Sterility", "0, 6, 12, 24, 36", "-"],
        ["안정성", "DWP1401 2주 위약(장기)", "4302132", "Sterility, endotoxin", "0, 3, 12, 24, 36", "-"],
        ["안정성", "DWP1401 2주 시험약(장기)", "4302131", "Sterility, endotoxin", "0, 3, 12, 24, 36", "-"],
        ["안정성", "DWP1401 2주 위약(가속)", "4302132", "Sterility, endotoxin", "0, 1, 3, 6", "-"],
        ["안정성", "DWP1401 2주 시험약(가속)", "4302131", "Sterility, endotoxin", "0, 1, 3, 6", "-"]
    ]
    
    df_guide = pd.DataFrame(master_list, columns=["구분", "검체명", "품목코드", "필수시험", "주기", "특정미생물"])

    # 2. 필터 UI
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        sel_cat = st.multiselect("구분별 필터", options=df_guide["구분"].unique(), default=[]) # 기본값을 빈 리스트로
    with c2:
        sel_test = st.multiselect("시험별 필터", options=["Sterility", "MLT", "endotoxin", "GPT"], default=[])
    with c3:
        search_text = st.text_input("검체명 또는 품목코드 검색", placeholder="예: 루피어, 9000226")

    # 3. 데이터 필터링 로직 (스마트 필터링)
    filtered_df = df_guide.copy()
    
    # [수정포인트] 구분 필터가 비어있지 않을 때만 필터링 수행
    if sel_cat:
        filtered_df = filtered_df[filtered_df["구분"].isin(sel_cat)]
    
    # 시험 항목 필터가 비어있지 않을 때만 필터링 수행
    if sel_test:
        mask = filtered_df["필수시험"].apply(lambda x: any(test in x for test in sel_test))
        filtered_df = filtered_df[mask]
        
    if search_text:
        filtered_df = filtered_df[
            filtered_df["검체명"].str.contains(search_text, case=False) | 
            filtered_df["품목코드"].str.contains(search_text)
        ]

    # 4. 결과 출력
    st.write(f"🔍 결과: 총 **{len(filtered_df)}** 건")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    # 💡 하단 팁
    st.markdown("""
    ---
    ### 📝 마스터 데이터 관리 가이드
    * **안정성 시험**: 주기(Month)별로 시험이 계획되어야 합니다.
    * **MLT 대상**: '특정미생물' 컬럼에 명시된 균주 시험이 누락되지 않도록 주의하세요.
    * **품목코드**: 시스템 연동의 핵심 키값입니다. 정확하게 입력되었는지 확인하세요.
    """)


elif menu == "📝 공정 기록 등록":
    st.title("📝 공정별 작업 시간 기록")
    tab1, tab2 = st.tabs(["✨ 신규 등록", "🛠️ 기록 수정/삭제"])
    
    with tab1:
        with st.form("process_form"):
            col1, col2 = st.columns(2)
            with col1:
                proc_batch = st.text_input("Batch No.", placeholder="예: LP24001")
                proc_name = st.selectbox("공정 선택", ["조제분무", "동결건조", "체과혼합", "약제부충전", "용제부충전", "기타"])
            
            st.write("---")
            hours = [f"{i:02d}" for i in range(24)]
            minutes = [f"{i:02d}" for i in range(60)]
            
            st.markdown("##### 🟢 공정 시작")
            c_s1, c_s2, c_s3 = st.columns([2, 1, 1])
            with c_s1: p_start_date = st.date_input("시작 날짜", value=datetime.now().date())
            with c_s2: s_hour = st.selectbox("시작 시간 (시)", hours, index=9)
            with c_s3: s_min = st.selectbox("시작 시간 (분)", minutes, index=0)
                
            st.markdown("##### 🔴 공정 종료")
            c_e1, c_e2, c_e3 = st.columns([2, 1, 1])
            with c_e1: p_end_date = st.date_input("종료 날짜", value=datetime.now().date())
            with c_e2: e_hour = st.selectbox("종료 시간 (시)", hours, index=18)
            with c_e3: e_min = st.selectbox("종료 시간 (분)", minutes, index=0)
                
            st.write("---")
            proc_note = st.text_input("특이사항 (비고)")
            submit = st.form_submit_button("💾 공정 기록 저장")
            
            if submit:
                if proc_batch.strip():
                    p_start_time = f"{s_hour}:{s_min}"
                    p_end_time = f"{e_hour}:{e_min}"
                    start_dt_str = f"{p_start_date.strftime('%Y-%m-%d')} {p_start_time}"
                    end_dt_str = f"{p_end_date.strftime('%Y-%m-%d')} {p_end_time}"
                    
                    save_process(proc_batch, proc_name, start_dt_str, end_dt_str, proc_note)
                    st.success(f"저장된 시간: {start_dt_str} ~ {end_dt_str}")
                    tm.sleep(1) 
                    st.rerun()
                else:
                    st.warning("Batch No.를 입력해주세요.")

    with tab2:
        st.subheader("🛠️ 저장된 기록 관리")
        df_edit = load_data(ws_process)
        
        if not df_edit.empty:
            df_edit = df_edit.iloc[::-1].reset_index(drop=True)
            edited_df = st.data_editor(
                df_edit,
                use_container_width=True,
                num_rows="dynamic", 
                key="process_editor",
                column_config={
                    "Batch No.": st.column_config.TextColumn("Batch No.", required=True),
                    "공정명": st.column_config.SelectboxColumn("공정명", options=["조제분무", "동결건조", "체과혼합", "약제부충전", "용제부충전", "기타"], required=True),
                    "시작시간": st.column_config.TextColumn("시작시간 (YYYY-MM-DD HH:MM)"),
                    "종료시간": st.column_config.TextColumn("종료시간 (YYYY-MM-DD HH:MM)"),
                }
            )
            
            if st.button("💾 수정사항 반영하기 (덮어쓰기)", type="primary"):
                try:
                    final_df = edited_df.iloc[::-1]
                    ws_process.clear()
                    ws_process.update([final_df.columns.values.tolist()] + final_df.values.tolist())
                    st.success("✅ 수정된 내용이 성공적으로 저장되었습니다!")
                    tm.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 중 오류가 발생했습니다: {e}")
        else:
            st.info("아직 저장된 기록이 없습니다.")
        
elif menu == "🛠️ 공정별 일정 현황":
    st.title("🛠️ 공정별 통합 일정 현황")
    st.write("---")

    # 1. 📅 실시간 날짜 계산 (기본값: 오늘 ~ 7일 뒤)
    today = datetime.now().date()
    seven_days_later = today + timedelta(days=7)

    # 2. 데이터 미리 로드 (검색 목록 생성용)
    df_p = load_data(ws_process) 
    
    if df_p.empty:
        st.info("등록된 공정 기록이 없습니다. '공정 기록 등록' 메뉴에서 먼저 작성해주세요.")
    else:
        # 배치 ID 추출 함수
        def get_base_id(batch_no):
            for suffix in ["A", "B", "C", "D", "E"]:
                if str(batch_no).endswith(suffix): return batch_no[:-1]
            return batch_no

        all_unique_bases = sorted(df_p['Batch No.'].apply(get_base_id).unique())

        # 3. 🔍 통합 검색 바 (날짜 2칸 + 배치검색 2칸 비율)
        st.subheader("🕵️‍♂️ 기간 및 배치별 일정 조회")
        col_d1, col_d2, col_search = st.columns([1, 1, 2])
        
        with col_d1:
            # 변수명을 search_start로 통일
            search_start = st.date_input("조회 시작일", value=today, key="proc_start_date")
        with col_d2:
            # 변수명을 search_end로 통일
            search_end = st.date_input("조회 종료일", value=seven_days_later, key="proc_end_date")
        with col_search:
            search_batches = st.multiselect(
                "Batch No. 검색 (비워두면 전체 조회)", 
                options=all_unique_bases,
                placeholder="배치 번호 선택/입력"
            )

        # 4. 조회 로직 시작
        if search_start > search_end:
            st.error("시작일이 종료일보다 늦을 수 없습니다.")
        else:
            # 선택된 날짜 범위를 기반으로 차트 날짜 생성
            display_dates = pd.date_range(search_start, search_end).date
            
            # 검색 필터링
            target_base_batches = search_batches if search_batches else all_unique_bases
            
            fixed_processes = [
                "조제분무", "동결건조", "체과혼합", "약제부충전", 
                "용제부충전A", "용제부충전B", "용제부충전C"
            ]
            
            table_rows = []
            
            # 🟢 필터링된 배치에 대해서만 데이터 생성
            for base_batch in target_base_batches:
                for proc_display_name in fixed_processes:
                    row_data = {"Batch No.": base_batch, "공정명": proc_display_name}
                    
                    # 용제부충전 분기 처리
                    if "용제부충전" in proc_display_name:
                        suffix = proc_display_name.replace("용제부충전", "")
                        stored_batch_no = base_batch + suffix
                        target = df_p[(df_p['Batch No.'] == stored_batch_no) & (df_p['공정명'] == "용제부충전")]
                    else:
                        target = df_p[(df_p['Batch No.'] == base_batch) & (df_p['공정명'] == proc_display_name)]
                    
                    # 선택된 기간 내 데이터가 있는지 확인
                    has_data_in_range = False
                    for d in display_dates:
                        col_name = d.strftime('%m/%d')
                        val = ""
                        if not target.empty:
                            for _, r in target.iterrows():
                                try:
                                    s_dt = pd.to_datetime(r['시작시간'])
                                    e_dt = pd.to_datetime(r['종료시간'])
                                    if s_dt.date() <= d <= e_dt.date():
                                        has_data_in_range = True
                                        if s_dt.date() == e_dt.date() == d: val = f"{s_dt.strftime('%H:%M')}~{e_dt.strftime('%H:%M')}"
                                        elif d == s_dt.date(): val = f"{s_dt.strftime('%H:%M')}~"
                                        elif d == e_dt.date(): val = f"~{e_dt.strftime('%H:%M')}"
                                        else: val = " " 
                                except: continue
                        row_data[col_name] = val
                    
                    table_rows.append(row_data)

            # 5. 테이블 출력
            if not table_rows:
                st.warning("조회 범위 내에 데이터가 없습니다.")
            else:
                wide_df = pd.DataFrame(table_rows).set_index(['Batch No.', '공정명'])

                def color_logic(v):
                    if v and str(v).strip() != "": 
                        return 'background-color: #FFFF00; color: black; border: 1px solid #ddd; font-weight: bold; text-align: center;'
                    elif v == " ": 
                        return 'background-color: #FFFF00; border: 1px solid #ddd;'
                    return 'border: 1px solid #ddd; color: transparent;'

                styled_wide_df = wide_df.style.map(color_logic)

                st.divider()
                st.subheader("📋 통합 공정현황 차트")
                st.dataframe(styled_wide_df, use_container_width=True)
                st.caption("🟡 노란색 표시: 해당 일자에 공정 진행됨")

elif menu == "🗣️ 방명록 (Guestbook)":
    st.title("ATLAS 방명록 (비밀글 지원)")

    # [1] 데이터 로드 (이미 코드 맨 위에 연결해둔 ws_guestbook 변수 사용!)
    try:
        df_gb = load_data(ws_guestbook)
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        df_gb = pd.DataFrame()

    # [2] 관리자 세션 상태 초기화
    if 'is_admin' not in st.session_state:
        st.session_state['is_admin'] = False

    # [3] 관리자 인증 (사이드바 메뉴)
    with st.sidebar:
        st.write("---")
        if not st.session_state['is_admin']:
            admin_pw = st.text_input("마스터 비밀번호", type="password", help="관리자 전용")
            if st.button("관리자 인증"):
                if admin_pw == "0000": # 👈 원하시는 마스터 비밀번호로 바꾸세요!
                    st.session_state['is_admin'] = True
                    st.rerun()
                else:
                    st.error("❌ 비밀번호가 틀렸습니다.")
        else:
            st.success("🔓 관리자 모드 작동 중")
            if st.button("로그아웃"):
                st.session_state['is_admin'] = False
                st.rerun()

    # [4] 새 글 작성 폼
    with st.expander("📝 새 방명록 쓰기", expanded=True):
        with st.form("new_message", clear_on_submit=True):
            user_name = st.text_input("작성자")
            user_msg = st.text_area("내용")
            user_pin = st.text_input("핀번호(4자리)", type="password", help="비밀글을 확인할 때 필요합니다.")
            
            if st.form_submit_button("등록하기"):
                if user_name and user_msg and user_pin:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # 구글 시트에 바로 한 줄 추가
                    ws_guestbook.append_row([user_name, user_msg, now_str, user_pin])
                    st.success("메시지가 안전하게 등록되었습니다!")
                    st.rerun()
                else:
                    st.warning("모든 항목을 빠짐없이 입력해주세요.")

    st.divider()

    # [5] 메시지 목록 출력 (말풍선 디자인)
    st.subheader("📋 메시지 목록")
    if df_gb.empty:
        st.info("아직 등록된 메시지가 없습니다. 첫 글을 남겨보세요!")
    else:
        # 최신 글이 위로 오도록 역순 정렬
        df_gb_display = df_gb.iloc[::-1] 
        
        for i, row in df_gb_display.iterrows():
            # 관리자면 열쇠 아이콘, 일반 유저면 사람 아이콘
            avatar_icon = "🔑" if st.session_state['is_admin'] else "👤"
            
            with st.chat_message("user", avatar=avatar_icon):
                # 안전하게 데이터 가져오기 (.get 사용)
                w = row.get('작성자', '익명')
                c = row.get('내용', '')
                t = row.get('작성시간', '')
                p = str(row.get('비밀번호', ''))

                st.markdown(f"**{w}** <small>({t})</small>", unsafe_allow_html=True)
                
                if st.session_state['is_admin']:
                    # 관리자는 핀번호 없이 모든 글 프리패스!
                    st.info(f"🔓 {c}")
                    st.caption(f"🔑 설정된 PIN: {p}")
                else:
                    # 일반 사용자는 핀번호 입력
                    input_pin = st.text_input("PIN 입력", type="password", key=f"gb_pin_{i}", label_visibility="collapsed", placeholder="PIN 번호 4자리")
                    
                    if input_pin == p:
                        st.success(f"🔓 {c}")
                    elif input_pin == "":
                        st.warning("🔒 비밀글입니다. PIN을 입력하세요.")
                    else:
                        st.error("❌ 비밀번호가 틀렸습니다.")
