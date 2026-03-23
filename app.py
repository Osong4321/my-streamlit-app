import streamlit as st
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
st.set_page_config(
    page_title="ATLAS 시험일정 자동화",
    page_icon="🧪",
    layout="wide"
)

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
ws_guestbook = doc.worksheet("방명록")

# =========================================================================
# 3. 데이터 입출력 함수 (100% 구글 시트 전용)
# =========================================================================
def load_data(worksheet):
    records = worksheet.get_all_records()
    return pd.DataFrame(records)

def save_schedule(batch, tester, sample, item, status, start_date, add_inc, end_date, deadline, time_status):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 구글 시트 맨 아랫줄에 바로 추가
    ws_schedule.append_row([now, batch, tester, sample, item, status, start_date, add_inc, end_date, deadline, time_status])

def save_process(batch_no, proc_name, start_time, end_time, note):
    # (주의) 구글 시트 '공정기록' 탭 1행이 [Batch No., 공정명, 시작시간, 종료시간, 비고] 5개 열이라고 가정
    ws_process.append_row([batch_no, proc_name, start_time, end_time, note])

def save_guestbook(name, msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws_guestbook.append_row([now, name, msg])

# =========================================================================
# 4. 사이드바 구성
# =========================================================================
st.sidebar.title("ATLAS 메뉴")
menu = st.sidebar.radio("이동할 페이지를 선택하세요:", 
                        [
                            "🏠 홈 (Home)", 
                            "📊 대시보드 (Dashboard)", 
                            "📅 시험 일정 관리", 
                            "📝 공정 기록 등록",      
                            "🛠️ 공정별 일정 현황",     
                            "🗣️ 방명록 (Guestbook)"
                        ])

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
    2. **🛠️ 공정별 일정 현황**: 전체 공정의 흐름을 날짜별/배치별로 시각화 (간트차트)
    3. **📅 시험 일정 관리**: 무균/엔도톡신 등 시험 일정 자동 계산 및 마감 관리
    4. **📊 대시보드**: 전체 업무 현황과 진행률을 한눈에 파악
    """)

elif menu == "📊 대시보드 (Dashboard)":
    st.title("📊 시험 일정 현황 대시보드")
    
    # CSV 변수 대신 구글 시트 변수(ws_schedule)로 변경
    df_schedule = load_data(ws_schedule)
    
    if not df_schedule.empty:
        m1, m2, m3, m4 = st.columns(4)
        total_cnt = len(df_schedule)
        ing_cnt = len(df_schedule[df_schedule['진행여부'] == "진행 중"])
        done_cnt = len(df_schedule[df_schedule['진행여부'] == "완료"])
        over_cnt = len(df_schedule[df_schedule['기한상태'].str.contains("초과", na=False)])
        
        m1.metric("전체 시험", f"{total_cnt}건")
        m2.metric("진행 중 🟢", f"{ing_cnt}건")
        m3.metric("완료 🔵", f"{done_cnt}건")
        m4.metric("기한 초과 🔴", f"{over_cnt}건", delta=f"-{over_cnt}", delta_color="inverse")
        
        st.write("---")
        st.subheader("📅 한눈에 보는 시험 일정표")
        
        chart_df = df_schedule[['Batch No.', '시험항목', '시험시작일', '예상종료일', '마감기한']].copy()
        chart_df['Start'] = pd.to_datetime(chart_df['시험시작일'], errors='coerce')
        chart_df['End'] = pd.to_datetime(chart_df['예상종료일'], errors='coerce')
        chart_df['Deadline'] = pd.to_datetime(chart_df['마감기한'], errors='coerce')
        
        valid_df = chart_df.dropna(subset=['Start', 'Deadline'], how='all')
        
        if valid_df.empty:
            st.info("📊 데이터에 유효한 날짜(시작일 또는 마감기한)가 없습니다.")
        else:
            all_dates = pd.concat([valid_df['Start'], valid_df['End'], valid_df['Deadline']])
            default_min = all_dates.min() if not all_dates.dropna().empty else datetime.today()
            default_max = all_dates.max() if not all_dates.dropna().empty else datetime.today() + timedelta(days=30)

            col_date1, col_date2, col_search = st.columns([1, 1, 2])
            with col_date1: start_pick = st.date_input("조회 시작일", default_min)
            with col_date2: end_pick = st.date_input("조회 종료일", default_max)
            with col_search:
                batch_keyword = st.text_input("Batch No. 검색 (단어 포함)", placeholder="예: MFT031 (비워두면 전체 조회)")

            if batch_keyword:
                valid_df = valid_df[valid_df['Batch No.'].astype(str).str.contains(batch_keyword, case=False, na=False)]

            if start_pick > end_pick:
                st.error("시작일이 종료일보다 늦을 수 없습니다.")
            else:
                try:
                    date_range = pd.date_range(start=start_pick, end=end_pick)
                    date_strs = [d.strftime('%m/%d') for d in date_range] 
                    grid_data = []
                    
                    for idx, row in valid_df.iterrows():
                        has_start = pd.notna(row['Start'])
                        has_deadline = pd.notna(row['Deadline'])
                        in_range = False
                        
                        if has_start and row['Start'].date() <= end_pick and (pd.isna(row['End']) or row['End'].date() >= start_pick):
                            in_range = True
                        elif has_deadline and start_pick <= row['Deadline'].date() <= end_pick:
                            in_range = True

                        if in_range:
                            display_name = f"{row['Batch No.']} ({row['시험항목']})"
                            row_data = {'시험 정보': display_name}
                            is_empty_row = True 
                            
                            for d_idx, single_date in enumerate(date_range):
                                date_str = date_strs[d_idx]
                                cell_val = ""
                                curr_d = single_date.date()
                                
                                if has_deadline and curr_d == row['Deadline'].date():
                                    cell_val = "마감"
                                    is_empty_row = False
                                elif has_start and pd.notna(row['End']) and row['Start'].date() <= curr_d <= row['End'].date():
                                    cell_val = f"진행_{row['시험항목']}"
                                    is_empty_row = False
                                    
                                row_data[date_str] = cell_val
                            
                            if not is_empty_row:
                                grid_data.append(row_data)
                    
                    if not grid_data:
                        st.warning("선택한 기간 내에 표시할 일정이 없습니다.")
                    else:
                        grid_df = pd.DataFrame(grid_data).set_index('시험 정보')
                        
                        def color_cells(val):
                            if "진행_무균시험" in val: return 'background-color: #FFFF00; color: #FFFF00;'
                            elif "진행_엔도톡신" in val: return 'background-color: #C1E1C1; color: #C1E1C1;'
                            elif "진행" in val: return 'background-color: #E0E0E0; color: #E0E0E0;'
                            elif val == "마감": return 'background-color: #FF4B4B; color: #FFFFFF; font-weight: bold; text-align: center;' 
                            return ''
                        
                        styled_grid = grid_df.style.map(color_cells) if hasattr(grid_df.style, 'map') else grid_df.style.applymap(color_cells)
                        st.dataframe(styled_grid, use_container_width=True)
                        st.caption("🟡 노란색: 무균시험 | 🟢 연한 초록색: 엔도톡신시험 | 🔴 빨간색: 마감기한")
                        
                except Exception as e:
                    st.error(f"대시보드를 구성하는 중 오류가 발생했습니다: {e}")
                
elif menu == "📅 시험 일정 관리":
    st.title("📅 시험 일정 자동 계산 및 기록")
    
    col1, col2 = st.columns(2)
    with col1:
        batch_no = st.text_input("1. Batch No.를 입력하세요", placeholder="예: LP24001")
        tester = st.text_input("2. 시험자를 입력하세요", placeholder="예: 홍길동")
        sample_type = st.selectbox("3. 시험검체를 선택하세요", ["선택해주세요", "루피어데포주", "DWJ1483포장전", "DWJ1483포장후", "루피어에멀전", "자재", "기타"])
        
        test_items = ["무균시험", "엔도톡신시험"] if sample_type in ["루피어에멀전", "DWJ1483포장후", "기타"] else ["무균시험"]
        if sample_type == "선택해주세요": test_items = ["검체를 먼저 선택하세요"]
        
        test_item = st.selectbox("4. 시험항목을 선택하세요", test_items)
        status = st.selectbox("5. 시험 진행 여부", ["대기 중", "진행 중", "완료", "보류"])

    with col2:
        is_pending = status in ["대기 중", "보류"]
        test_date = st.date_input("6. 시험일자 (시작일)", disabled=is_pending)
        add_incubation = st.checkbox("➕ 추가 배양 진행 (선택 시 4일 연장)") if test_item == "무균시험" else False
        deadline_date = st.date_input("7. 마감 기한 (목표 종료일)")
        
        if sample_type != "선택해주세요" and test_item != "검체를 먼저 선택하세요":
            if is_pending:
                time_status, color, end_date_str = f"{status} 🔴", "#FF4B4B", "미정"
                save_start, save_end = "-", "-"
            else:
                days = 18 if add_incubation else 14 if test_item == "무균시험" else 0
                end_date = test_date + timedelta(days=days)
                time_status = "초과 🔴" if end_date > deadline_date else "준수 🟢"
                color = "#FF4B4B" if end_date > deadline_date else "#00CC96"
                end_date_str = end_date.strftime('%Y-%m-%d')
                save_start, save_end = test_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
            
            st.markdown(f"<h3 style='color: {color};'>{time_status} 예상 종료일 : {end_date_str}</h3>", unsafe_allow_html=True)
            
            if st.button("💾 이 일정 기록 저장하기"):
                if batch_no.strip() and tester.strip():
                    save_schedule(batch_no, tester, sample_type, test_item, status, 
                                  save_start, "O" if add_incubation else "X", save_end,    
                                  deadline_date.strftime('%Y-%m-%d'), time_status)
                    st.toast('성공적으로 저장되었습니다!', icon='✅')
                    st.rerun()
                else:
                    st.warning("Batch No.와 시험자를 모두 입력해주세요.")
                    
    st.divider()
    tab1, tab2 = st.tabs(["🔍 시험 일정 검색 (조회 전용)", "🛠️ 전체 일정 관리 (수정 및 삭제)"])
    
    with tab1:
        st.subheader("🔍 조건별 일정 검색")
        df_search = load_data(ws_schedule)
        
        if not df_search.empty:
            s_col1, s_col2 = st.columns([1, 2])
            with s_col1:
                search_keyword = st.text_input("Batch No. 검색 (단어 포함)", placeholder="예: MFT031")
            with s_col2:
                filter_dates = st.date_input("기간 조회 (시작일 ~ 종료일)", value=[], key="date_filter")
            
            filtered_df = df_search.copy()
            if search_keyword:
                filtered_df = filtered_df[filtered_df['Batch No.'].astype(str).str.contains(search_keyword, case=False, na=False)]
            
            if len(filter_dates) == 2:
                filtered_df['시험일자(계산용)'] = pd.to_datetime(filtered_df['시험시작일'], errors='coerce')
                start_date, end_date = filter_dates
                mask = (filtered_df['시험일자(계산용)'].dt.date >= start_date) & (filtered_df['시험일자(계산용)'].dt.date <= end_date)
                filtered_df = filtered_df.loc[mask].drop(columns=['시험일자(계산용)'])
            
            st.write(f"검색 결과: 총 **{len(filtered_df)}** 건")
            st.dataframe(filtered_df.iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("아직 저장된 일정이 없습니다.")

    with tab2:
        st.subheader("🛠️ 전체 일정 수정 및 삭제")
        df_manage = load_data(ws_schedule)
        
        if not df_manage.empty:
            df_reversed = df_manage.iloc[::-1].reset_index(drop=True)
            date_columns = ["시험시작일", "예상종료일", "마감기한"]
            for col in date_columns:
                df_reversed[col] = pd.to_datetime(df_reversed[col], errors='coerce').dt.date
            
            edited_df = st.data_editor(
                df_reversed,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "기록시간": None, 
                    "진행여부": st.column_config.SelectboxColumn("진행여부", options=["대기 중", "진행 중", "완료", "보류"], required=True),
                    "기한상태": st.column_config.SelectboxColumn("기한상태", options=["준수 🟢", "초과 🔴", "대기 중 🟡", "보류 🔴"], required=True),
                    "시험시작일": st.column_config.DateColumn("시험시작일", format="YYYY-MM-DD"),
                    "예상종료일": st.column_config.DateColumn("예상종료일", format="YYYY-MM-DD"),
                    "마감기한": st.column_config.DateColumn("마감기한", format="YYYY-MM-DD")
                },
                key="schedule_editor"
            )
            
            if st.button("💾 변경사항 안전하게 덮어쓰기", type="primary"):
                final_df = edited_df.iloc[::-1].copy()
                for col in date_columns:
                    final_df[col] = final_df[col].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else "-")
                
                # 구글 시트에 덮어쓰기 로직
                ws_schedule.clear()
                ws_schedule.update([final_df.columns.values.tolist()] + final_df.values.tolist())
                st.success("✅ 변경사항이 구글 시트에 저장되었습니다!")
                tm.sleep(1)
                st.rerun()

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

    # [1] 구글 시트 '공정기록' 탭에서 데이터를 최신으로 읽어옵니다.
    df_p = load_data(ws_process) 
    
    if df_p.empty:
        st.info("등록된 공정 기록이 없습니다. '공정 기록 등록' 메뉴에서 먼저 작성해주세요.")
    else:
        # -------------------------------------------------------------------------
        # [2] 데이터 전처리 (Pivoting을 위한 밑작업)
        # -------------------------------------------------------------------------
        # 시작/종료 시간을 날짜 형식으로 변환 (비교용)
        df_p['시작날짜_계산용'] = pd.to_datetime(df_p['시작시간']).dt.date
        df_p['종료날짜_계산용'] = pd.to_datetime(df_p['종료시간']).dt.date

        # 전체 기간 범위 가져오기 (컬럼용)
        all_dates_calc = pd.concat([df_p['시작날짜_계산용'], df_p['종료날짜_계산용']])
        min_date = all_dates_calc.min()
        max_date = all_dates_calc.max()
        
        # 상단 필터 (기간 조회) - 기존 유지
        st.subheader("🕵️‍♂️ 기간별 일정 조회")
        col_date1, col_date2 = st.columns(2)
        with col_date1: v_start = st.date_input("조회 시작일", min_date)
        with col_date2: v_end = st.date_input("조회 종료일", max_date)
        
        if v_start > v_end:
            st.error("시작일이 종료일보다 늦을 수 없습니다.")
        else:
            # 기간 필터 적용
            mask = (df_p['시작날짜_계산용'] <= v_end) & (df_p['종료날짜_계산용'] >= v_start)
            filtered_df = df_p.loc[mask]

            # 표에 표시할 날짜 범위 결정
            display_dates = pd.date_range(v_start, v_end).date
            
            # -------------------------------------------------------------------------
            # [3] ⭐ 가장 중요한 통합 테이블 구성 로직 (Pivot)
            # -------------------------------------------------------------------------
            # 시트에 저장된 Batch No.(E07447, E07447A...)에서 기준 배취(E07447)만 추출하는 주문
            def get_base_id(batch_no):
                for suffix in ["A", "B", "C", "D", "E"]: # 님이 사용하시는 꼬리표 목록
                    if str(batch_no).endswith(suffix):
                        return batch_no[:-1] # 마지막 한 글자를 떼냄
                return batch_no # 꼬리표 없으면 그대로

            # 기준 배취 목록 (E07447 등)
            unique_base_batches = sorted(filtered_df['Batch No.'].apply(get_base_id).unique())
            
            # 표에 보여줄 공정 이름 순서 (이미지와 동일하게 고정)
            fixed_processes = [
                "조제분무", "동결건조", "체화혼합", "약제부충전", 
                "용제부충전A", "용제부충전B", "용제부충전C"
            ]
            
            # 데이터를 채워 넣을 빈 리스트
            table_rows = []
            
            for base_batch in unique_base_batches:
                # 하나의 배취(E07447) 아래에 7개 공정 줄을 무조건 만듭니다.
                for proc_display_name in fixed_processes:
                    row_data = {
                        "Batch No.": base_batch,
                        "공정명": proc_display_name
                    }
                    
                    # 날짜 컬럼을 만들고 빈칸으로 초기화 ("H"는 하이라이트 표시용)
                    for date in display_dates:
                        date_col_name = date.strftime('%m/%d')
                        row_data[date_col_name] = "" 
                        
                        # -------------------------------------------------------------
                        # [4] ⭐ 시트 데이터와 표의 줄(Row)을 연결하는 핵심 로직
                        # -------------------------------------------------------------
                        is_highlight = False
                        
                        if "용제부충전" in proc_display_name:
                            # [Case B] 용제부 충전 줄 (A,B,C...)
                            # 표 줄 이름(`용제부충전A`)에서 `A` 꼬리표만 추출
                            suffix = proc_display_name.replace("용제부충전", "")
                            # 시트 데이터에서 검색할 배취명 (E07447 + A -> E07447A)
                            stored_batch_no = base_batch + suffix
                            
                            # 시트 데이터에서 해당 배취 + '용제부충전' 공정이 당일에 있는지 검색
                            match = filtered_df[
                                (filtered_df['Batch No.'] == stored_batch_no) & 
                                (filtered_df['공정명'] == "용제부충전") & 
                                (filtered_df['시작날짜_계산용'] <= date) & 
                                (filtered_df['종료날짜_계산용'] >= date)
                           ]
                            if not match.empty: is_highlight = True
                                
                        else:
                            # [Case A] 약제부 공정 줄 (조제, 동결 등)
                            # 시트 데이터에서 해당 배취(E07447) + 해당 공정이 당일에 있는지 검색
                            match = filtered_df[
                                (filtered_df['Batch No.'] == base_batch) & 
                                (filtered_df['공정명'] == proc_display_name) & 
                                (filtered_df['시작날짜_계산용'] <= date) & 
                                (filtered_df['종료날짜_계산용'] >= date)
                           ]
                            if not match.empty: is_highlight = True
                        
                        # 데이터가 있으면 하이라이트 표시("H")를 넣어줍니다.
                        if is_highlight:
                            row_data[date_col_name] = "H"
                            
                    table_rows.append(row_data)

            # [5] 리스트를 표(데이터프레임)로 만듭니다.
            wide_df = pd.DataFrame(table_rows)
            
            # Batch No.와 공정명을 기준으로 표를 정렬하고 고정
            wide_df = wide_df.set_index(['Batch No.', '공정명'])

            # -------------------------------------------------------------------------
            # [6] 데이터프레임 스타일링 (노란색 하이라이트 및 "H" 글자 숨기기)
            # -------------------------------------------------------------------------
            def highlight_cells(val):
                if val == "H":
                    # 배경색 노란색, 글자색도 노란색으로 해서 글자를 숨깁니다 (transparent 사용 가능)
                    return 'background-color: #FFFF00; color: #FFFF00; border: 1px solid #ddd;' 
                return 'border: 1px solid #ddd;'

            # 스타일 적용 및 출력
            styled_wide_df = wide_df.style.applymap(highlight_cells) # 최신 Pandas는 .style.map 사용

            st.divider()
            st.subheader("📋 통합 공정현황 간트차트")
            st.dataframe(styled_wide_df, use_container_width=True)
            st.caption("🟡 노란색: 해당 날짜 공정 진행 중")

# 메뉴 이름 일치 완료 ("🗣️ 방명록 (Guestbook)")
elif menu == "🗣️ 방명록 (Guestbook)":
    st.title("📝 시스템 개선 건의사항 및 관리")
    with st.expander("➕ 새 건의사항 작성하기", expanded=True):
        with st.form(key='guest_form', clear_on_submit=True):
            user_name = st.text_input("작성자 이름")
            user_msg = st.text_area("내용")
            if st.form_submit_button("저장하기"):
                if user_msg.strip():
                    save_guestbook(user_name if user_name else "익명", user_msg)
                    st.success("✅ 저장되었습니다!")
                    tm.sleep(1)
                    st.rerun()

    st.write("---")
    df_guest = load_data(ws_guestbook)
    if not df_guest.empty:
        edited_guest = st.data_editor(df_guest.iloc[::-1], use_container_width=True, num_rows="dynamic",
                                      column_config={"작성시간": st.column_config.TextColumn("작성시간", disabled=True)})
        if st.button("💾 방명록 변경사항 저장하기"):
            # 구글 시트에 수정사항 덮어쓰기
            ws_guestbook.clear()
            final_guest = edited_guest.iloc[::-1]
            ws_guestbook.update([final_guest.columns.values.tolist()] + final_guest.values.tolist())
            st.success("업데이트 완료! ✅")
            tm.sleep(1)
            st.rerun()
