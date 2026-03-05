import streamlit as st
import pandas as pd
import os
import plotly.express as px
# ⭐ datetime 임포트 정리 (충돌 방지)
from datetime import datetime, timedelta, time
import time as tm
#from streamlit_calendar import calendar
import os
import plotly.express as px  # 시각화를 위한 라이브러리

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="ATLAS 시험일정 자동화",
    page_icon="🧪",
    layout="wide"
)

GUESTBOOK_FILE = "guestbook_data.csv"
SCHEDULE_FILE = "schedule_data.csv"
PROCESS_FILE = "process_data.csv"

# 3. CSV 파일 초기화
def init_csv():
    if not os.path.exists(GUESTBOOK_FILE):
        pd.DataFrame(columns=["이름", "메시지", "작성시간"]).to_csv(GUESTBOOK_FILE, index=False, encoding="utf-8-sig") 
    if not os.path.exists(SCHEDULE_FILE):
        pd.DataFrame(columns=["기록시간", "Batch No.", "시험자", "시험검체", "시험항목", "진행여부", "시험시작일", "추가배양", "예상종료일", "마감기한", "기한상태"]).to_csv(SCHEDULE_FILE, index=False, encoding="utf-8-sig")
    if not os.path.exists(PROCESS_FILE):
        # ⭐ 컬럼명에 '기록시간'(시스템저장용) 추가
        pd.DataFrame(columns=["Batch No.", "공정명", "시작시간", "종료시간", "비고", "기록시간"]).to_csv(PROCESS_FILE, index=False, encoding="utf-8-sig")
    # --- [공정 파일 초기화 추가 끝] ---

def load_data(file_name):
    if not os.path.exists(file_name):
        init_csv()
    return pd.read_csv(file_name, encoding="utf-8-sig")

# 4. 저장 함수들 (✅ 시험자 tester 매개변수 및 데이터 추가)
def save_schedule(batch, tester, sample, item, status, start_date, add_inc, end_date, deadline, time_status):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_data = pd.DataFrame([{
        "기록시간": now, "Batch No.": batch, "시험자": tester, "시험검체": sample, "시험항목": item, 
        "진행여부": status, "시험시작일": start_date, "추가배양": add_inc,
        "예상종료일": end_date, "마감기한": deadline, "기한상태": time_status
    }])
    new_data.to_csv(SCHEDULE_FILE, mode='a', header=False, index=False, encoding="utf-8-sig")

PROCESS_FILE = "process_data.csv"

#4.1 공정기록 # ✅ 올바른 함수 정의
# 4. 저장 함수 (여기가 제일 중요함!! 기존 함수 지우고 이거 복사하세요)
def save_process(batch_no, proc_name, start_time, end_time, note):
    df = load_data(PROCESS_FILE)
    
    # 시스템 시간을 쓰지 않고, 매개변수로 들어온 start_time을 그대로 넣습니다.
    new_data = pd.DataFrame([{
        "Batch No.": batch_no,
        "공정명": proc_name,
        "시작시간": start_time,  # 👈 (중요) 사용자가 입력한 값
        "종료시간": end_time,    # 👈 (중요) 사용자가 입력한 값
        "비고": note
    }])
    
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(PROCESS_FILE, index=False, encoding="utf-8-sig")
    
def save_guestbook(name, msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_data = pd.DataFrame([{"이름": name, "메시지": msg, "작성시간": now}])
    new_data.to_csv(GUESTBOOK_FILE, mode='a', header=False, index=False, encoding="utf-8-sig")

init_csv()

# 5. 사이드바 구성 (신규 메뉴 2종 추가)
st.sidebar.title("ATLAS 메뉴")
menu = st.sidebar.radio("이동할 페이지를 선택하세요:", 
                        [
                            "홈 (Home)", 
                            "📊 대시보드 (Dashboard)", 
                            "시험 일정 관리", 
                            "📝 공정 기록 등록",      # ✅ 추가됨
                            "🛠️ 공정별 일정 현황",     # ✅ 추가됨
                            "방명록 (Guestbook)"
                        ])
# 6. 메인 화면 구성
if menu == "홈 (Home)":
    st.title("🏠 환영합니다!")
    st.subheader("ATLAS (Automated Trend Learning and Analysis System)")
    st.write("오송루피어QC팀 미생물파트 시험일정 자동화 시스템입니다.")
    st.write("---")

elif menu == "📊 대시보드 (Dashboard)":
    st.title("📊 시험 일정 현황 대시보드")
    
    # 데이터를 새로 불러옵니다.
    df_schedule = load_data(SCHEDULE_FILE)
    
    if not df_schedule.empty:
        # --- [1] 상단 지표 카드 (기존 유지) ---
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
        
        # --- [2] 검색 및 필터링 영역 (수정됨) ---
        st.subheader("📅 한눈에 보는 시험 일정표")
        
        chart_df = df_schedule[['Batch No.', '시험항목', '시험시작일', '예상종료일', '마감기한']].copy()
        chart_df['Start'] = pd.to_datetime(chart_df['시험시작일'], errors='coerce')
        chart_df['End'] = pd.to_datetime(chart_df['예상종료일'], errors='coerce')
        chart_df['Deadline'] = pd.to_datetime(chart_df['마감기한'], errors='coerce')
        
        # 유효 데이터 필터링
        valid_df = chart_df.dropna(subset=['Start', 'Deadline'], how='all')
        
        if valid_df.empty:
            st.info("📊 데이터에 유효한 날짜(시작일 또는 마감기한)가 없습니다.")
        else:
            # 기본 날짜 범위 설정
            all_dates = pd.concat([valid_df['Start'], valid_df['End'], valid_df['Deadline']])
            default_min = all_dates.min() if not all_dates.dropna().empty else datetime.today()
            default_max = all_dates.max() if not all_dates.dropna().empty else datetime.today() + timedelta(days=30)

            # ⭐ 레이아웃 수정: 날짜 선택(1) + 날짜 선택(1) + 검색창(2) 비율로 배치
            col_date1, col_date2, col_search = st.columns([1, 1, 2])
            
            with col_date1:
                start_pick = st.date_input("조회 시작일", default_min)
            with col_date2:
                end_pick = st.date_input("조회 종료일", default_max)
            with col_search:
                # ⭐ 추가된 기능: Batch No. 텍스트 검색
                batch_keyword = st.text_input(
                    "Batch No. 검색 (단어 포함)", 
                    placeholder="예: MFT031 (비워두면 전체 조회)",
                    help="입력한 글자가 포함된 모든 배치를 보여줍니다."
                )

            # ⭐ 검색 로직 적용: 검색어가 있으면 valid_df를 먼저 필터링합니다.
            if batch_keyword:
                valid_df = valid_df[valid_df['Batch No.'].astype(str).str.contains(batch_keyword, case=False, na=False)]

            if start_pick > end_pick:
                st.error("시작일이 종료일보다 늦을 수 없습니다.")
            else:
                try:
                    # 표 만들기 로직
                    date_range = pd.date_range(start=start_pick, end=end_pick)
                    date_strs = [d.strftime('%m/%d') for d in date_range] 
                    
                    grid_data = []
                    
                    # 필터링된 valid_df를 순회하며 표 데이터 생성
                    for idx, row in valid_df.iterrows():
                        has_start = pd.notna(row['Start'])
                        has_deadline = pd.notna(row['Deadline'])
                        
                        # 기간 내에 포함되는지 확인
                        in_range = False
                        if has_start and row['Start'].date() <= end_pick and (pd.isna(row['End']) or row['End'].date() >= start_pick):
                            in_range = True
                        elif has_deadline and start_pick <= row['Deadline'].date() <= end_pick:
                            in_range = True

                        if in_range:
                            display_name = f"{row['Batch No.']} ({row['시험항목']})"
                            row_data = {'시험 정보': display_name}
                            
                            # 날짜별 셀 채우기
                            is_empty_row = True # 빈 줄 방지용 플래그
                            
                            for d_idx, single_date in enumerate(date_range):
                                date_str = date_strs[d_idx]
                                cell_val = ""
                                curr_d = single_date.date()
                                
                                # 마감 표시 (최우선)
                                if has_deadline and curr_d == row['Deadline'].date():
                                    cell_val = "마감"
                                    is_empty_row = False
                                # 진행 표시 (시작일이 있는 경우에만)
                                elif has_start and pd.notna(row['End']) and row['Start'].date() <= curr_d <= row['End'].date():
                                    cell_val = f"진행_{row['시험항목']}"
                                    is_empty_row = False
                                    
                                row_data[date_str] = cell_val
                            
                            if not is_empty_row:
                                grid_data.append(row_data)
                    
                    if not grid_data:
                        if batch_keyword:
                            st.warning(f"'{batch_keyword}'에 대한 검색 결과가 선택한 기간 내에 없습니다.")
                        else:
                            st.warning("선택한 기간 내에 표시할 일정이 없습니다.")
                    else:
                        grid_df = pd.DataFrame(grid_data).set_index('시험 정보')
                        
                        def color_cells(val):
                            if "진행_무균시험" in val:
                                return 'background-color: #FFFF00; color: #FFFF00;' # 노란색
                            elif "진행_엔도톡신" in val:
                                return 'background-color: #C1E1C1; color: #C1E1C1;' # 연두색
                            elif "진행" in val:
                                return 'background-color: #E0E0E0; color: #E0E0E0;' # 회색
                            elif val == "마감":
                                return 'background-color: #FF4B4B; color: #FFFFFF; font-weight: bold; text-align: center;' 
                            return ''
                        
                        # 스타일 적용 및 출력
                        styled_grid = grid_df.style.map(color_cells) if hasattr(grid_df.style, 'map') else grid_df.style.applymap(color_cells)
                        st.dataframe(styled_grid, use_container_width=True)
                        st.caption("🟡 노란색: 무균시험 | 🟢 연한 초록색: 엔도톡신시험 | 🔴 빨간색: 마감기한")
                        
                except Exception as e:
                    st.error(f"대시보드를 구성하는 중 오류가 발생했습니다: {e}")
                
elif menu == "시험 일정 관리":
    st.title("📅 시험 일정 자동 계산 및 기록")
    
    # ----------------------------------------------------
    # 1. 입력부
    # ----------------------------------------------------
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
                time_status = f"{status} 🔴"
                color = "#FF4B4B" 
                end_date_str = "미정"
                save_start = "-"
                save_end = "-"
            else:
                days = 18 if add_incubation else 14 if test_item == "무균시험" else 0
                end_date = test_date + timedelta(days=days)
                time_status = "초과 🔴" if end_date > deadline_date else "준수 🟢"
                color = "#FF4B4B" if end_date > deadline_date else "#00CC96"
                end_date_str = end_date.strftime('%Y-%m-%d')
                save_start = test_date.strftime('%Y-%m-%d')
                save_end = end_date.strftime('%Y-%m-%d')
            
            st.markdown(f"<h3 style='color: {color};'>{time_status} 예상 종료일 : {end_date_str}</h3>", unsafe_allow_html=True)
            
            if st.button("💾 이 일정 기록 저장하기"):
                if batch_no.strip() and tester.strip():
                    save_schedule(batch_no, tester, sample_type, test_item, status, 
                                  save_start, 
                                  "O" if add_incubation else "X", 
                                  save_end,   
                                  deadline_date.strftime('%Y-%m-%d'), time_status)
                    st.toast('성공적으로 저장되었습니다!', icon='✅')
                    st.rerun()
                else:
                    st.warning("Batch No.와 시험자를 모두 입력해주세요.")
                    
    # ----------------------------------------------------
    # 2. 검색 및 필터링 & 데이터 수정/삭제 (Tabs 기능 적용)
    # ----------------------------------------------------
    st.divider()
    
    tab1, tab2 = st.tabs(["🔍 시험 일정 검색 (조회 전용)", "🛠️ 전체 일정 관리 (수정 및 삭제)"])
    
    # ==========================================
    # [탭 1] 검색 기능 강화 (Batch No. 수기 검색 추가)
    # ==========================================
    with tab1:
        st.subheader("🔍 조건별 일정 검색")
        df_search = load_data(SCHEDULE_FILE)
        
        if not df_search.empty:
            # 검색 필터 레이아웃 (날짜 선택 + 텍스트 검색)
            s_col1, s_col2 = st.columns([1, 2])
            
            with s_col1:
                # ⭐ 여기가 추가된 Batch No. 검색 기능입니다.
                search_keyword = st.text_input(
                    "Batch No. 검색 (단어 포함)", 
                    placeholder="예: MFT031",
                    help="입력한 글자가 포함된 모든 배치를 보여줍니다."
                )
                
            with s_col2:
                filter_dates = st.date_input(
                    "기간 조회 (시작일 ~ 종료일)", 
                    value=[], 
                    key="date_filter",
                    help="기간을 선택하지 않으면 전체 기간이 조회됩니다."
                )
            
            # --- 필터링 로직 적용 ---
            filtered_df = df_search.copy()
            
            # 1. Batch No. 문자열 포함 검색 (대소문자 구분 없음)
            if search_keyword:
                # 'Batch No.' 컬럼을 문자열로 변환 후 검색 (case=False: 대소문자 무시)
                filtered_df = filtered_df[filtered_df['Batch No.'].astype(str).str.contains(search_keyword, case=False, na=False)]
            
            # 2. 날짜 기간 검색
            if len(filter_dates) == 2:
                filtered_df['시험일자(계산용)'] = pd.to_datetime(filtered_df['시험시작일'], errors='coerce')
                start_date, end_date = filter_dates
                mask = (filtered_df['시험일자(계산용)'].dt.date >= start_date) & (filtered_df['시험일자(계산용)'].dt.date <= end_date)
                filtered_df = filtered_df.loc[mask]
                filtered_df = filtered_df.drop(columns=['시험일자(계산용)']) # 출력 전 임시 컬럼 삭제
            
            st.write(f"검색 결과: 총 **{len(filtered_df)}** 건")
            st.dataframe(filtered_df.iloc[::-1], use_container_width=True, hide_index=True)
            
        else:
            st.info("아직 저장된 일정이 없습니다.")

    # ==========================================
    # [탭 2] 데이터 에디터를 활용한 수정 및 삭제
    # ==========================================
    with tab2:
        st.subheader("🛠️ 전체 일정 수정 및 삭제")
        st.info("💡 이곳에서는 전체 데이터를 조회하고 수정할 수 있습니다. 특정 데이터를 찾으려면 [Tab 1]에서 검색하세요.")
        
        df_manage = load_data(SCHEDULE_FILE)
        
        if not df_manage.empty:
            df_reversed = df_manage.iloc[::-1].reset_index(drop=True)
            
            # 날짜 형식 변환
            date_columns = ["시험시작일", "예상종료일", "마감기한"]
            for col in date_columns:
                df_reversed[col] = pd.to_datetime(df_reversed[col], errors='coerce').dt.date
            
            # 데이터 에디터 설정
            edited_df = st.data_editor(
                df_reversed,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "기록시간": None, 
                    
                    "진행여부": st.column_config.SelectboxColumn(
                        "진행여부",
                        options=["대기 중", "진행 중", "완료", "보류"],
                        required=True
                    ),
                    
                    "기한상태": st.column_config.SelectboxColumn(
                        "기한상태",
                        options=["준수 🟢", "초과 🔴", "대기 중 🟡", "보류 🔴"],
                        required=True
                    ),
                    
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
                    
                final_df.to_csv(SCHEDULE_FILE, index=False, encoding="utf-8-sig")
                st.success("✅ 변경사항이 저장되었습니다!")
                st.rerun()
                
elif menu == "📝 공정 기록 등록":
    st.title("📝 공정별 작업 시간 기록")

    # 탭을 나누어 입력과 관리를 분리합니다.
    tab1, tab2 = st.tabs(["✨ 신규 등록", "🛠️ 기록 수정/삭제"])

    # ====================================================
    # [탭 1] 신규 등록 (아까 만든 시/분 드롭다운 방식 유지)
    # ====================================================
    with tab1:
        with st.form("process_form"):
            col1, col2 = st.columns(2)
            with col1:
                proc_batch = st.text_input("Batch No.", placeholder="예: LP24001")
                proc_name = st.selectbox("공정 선택", ["조제분무", "동결건조", "체과혼합", "약제부충전", "용제부충전", "기타"])
            
            st.write("---")
            
            # 시(00~23)와 분(00~59) 목록 생성
            hours = [f"{i:02d}" for i in range(24)]
            minutes = [f"{i:02d}" for i in range(60)]
            
            # 1. 시작 일시 설정
            st.markdown("##### 🟢 공정 시작")
            c_s1, c_s2, c_s3 = st.columns([2, 1, 1])
            with c_s1:
                p_start_date = st.date_input("시작 날짜", value=datetime.now().date())
            with c_s2:
                s_hour = st.selectbox("시작 시간 (시)", hours, index=9) # 기본 09시
            with c_s3:
                s_min = st.selectbox("시작 시간 (분)", minutes, index=0)
                
            # 2. 종료 일시 설정
            st.markdown("##### 🔴 공정 종료")
            c_e1, c_e2, c_e3 = st.columns([2, 1, 1])
            with c_e1:
                p_end_date = st.date_input("종료 날짜", value=datetime.now().date())
            with c_e2:
                e_hour = st.selectbox("종료 시간 (시)", hours, index=18) # 기본 18시
            with c_e3:
                e_min = st.selectbox("종료 시간 (분)", minutes, index=0)
                
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
                    
                    st.toast(f"✅ {proc_batch} 저장 완료!", icon="💾")
                    st.success(f"저장된 시간: {start_dt_str} ~ {end_dt_str}")
                    # 저장 후 탭 2(관리)에서 바로 확인할 수 있게 데이터 갱신
                    tm.sleep(1) 
                    st.rerun()
                else:
                    st.warning("Batch No.를 입력해주세요.")

    # ====================================================
    # [탭 2] 기록 수정 및 삭제 (데이터 에디터 사용)
    # ====================================================
    with tab2:
        st.subheader("🛠️ 저장된 기록 관리")
        st.info("💡 엑셀처럼 내용을 직접 클릭해서 수정하거나, 행을 선택해 삭제할 수 있습니다.")
        
        df_edit = load_data(PROCESS_FILE)
        
        if not df_edit.empty:
            # 최신순 정렬 (역순)
            df_edit = df_edit.iloc[::-1].reset_index(drop=True)
            
            # 데이터 에디터 표시
            edited_df = st.data_editor(
                df_edit,
                use_container_width=True,
                num_rows="dynamic", # 행 추가/삭제 가능하게 설정
                key="process_editor",
                column_config={
                    "Batch No.": st.column_config.TextColumn("Batch No.", required=True),
                    "공정명": st.column_config.SelectboxColumn("공정명", options=["조제분무", "동결건조", "체과혼합", "약제부충전", "용제부충전", "기타"], required=True),
                    "시작시간": st.column_config.TextColumn("시작시간 (YYYY-MM-DD HH:MM)", help="형식을 꼭 지켜주세요"),
                    "종료시간": st.column_config.TextColumn("종료시간 (YYYY-MM-DD HH:MM)", help="형식을 꼭 지켜주세요"),
                    "비고": st.column_config.TextColumn("비고"),
                }
            )
            
            # 변경사항 저장 버튼
            if st.button("💾 수정사항 반영하기 (덮어쓰기)", type="primary"):
                try:
                    # 1. 다시 날짜순(과거순)으로 되돌리기 위해 역순 정렬
                    final_df = edited_df.iloc[::-1]
                    
                    # 2. CSV 파일에 저장
                    final_df.to_csv(PROCESS_FILE, index=False, encoding="utf-8-sig")
                    
                    st.success("✅ 수정된 내용이 성공적으로 저장되었습니다!")
                    tm.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 중 오류가 발생했습니다: {e}")
        else:
            st.info("아직 저장된 기록이 없습니다. '신규 등록' 탭에서 데이터를 추가해주세요.")
        
elif menu == "🛠️ 공정별 일정 현황":
    st.title("🛠️ 공정별 상세 일정 현황")

    df_p = load_data(PROCESS_FILE)
    
    if df_p.empty:
        st.info("등록된 공정 기록이 없습니다. '공정 기록 등록' 메뉴에서 먼저 작성해주세요.")
    else:
        # 1. 존재하는 모든 Batch No. 가져오기 (검색 목록용)
        unique_batches = sorted(df_p['Batch No.'].unique())

        # 2. 상단 필터 영역 (날짜 선택 + 배취 검색)
        # 화면 구성을 1:1:2 비율로 나눠서 배취 검색창을 넓게 줍니다.
        col_d1, col_d2, col_d3 = st.columns([1, 1, 2])
        
        with col_d1:
            v_start = st.date_input("조회 시작일", datetime.today() - timedelta(days=2))
        with col_d2:
            v_end = st.date_input("조회 종료일", datetime.today() + timedelta(days=10))
        with col_d3:
            # ⭐ 여기가 핵심! Batch No. 검색/선택 기능
            search_batches = st.multiselect(
                "Batch No. 검색 (비워두면 전체 조회)", 
                options=unique_batches,
                placeholder="배치 번호를 선택하거나 입력하세요"
            )
        
        date_range = pd.date_range(v_start, v_end)
        plot_data = []
        
        # 3. 검색 조건에 따라 보여줄 배취 결정
        if search_batches:
            target_batches = search_batches # 사용자가 선택한 것만
        else:
            target_batches = unique_batches # 선택 안 했으면 전체 다
            
        processes = ["조제분무", "동결건조", "체과혼합", "약제부충전", "용제부충전", "기타"]

        # 결정된 target_batches에 대해서만 반복문 실행
        for batch in target_batches:
            for proc in processes:
                row_dict = {"Batch No.": batch, "Process": proc}
                
                # 해당 배치 & 해당 공정의 데이터 필터링
                target = df_p[(df_p['Batch No.'] == batch) & (df_p['공정명'] == proc)]
                
                for d in date_range:
                    col_name = d.strftime('%m/%d')
                    val = ""
                    curr_date = d.date()
                    
                    if not target.empty:
                        for _, r in target.iterrows():
                            try:
                                s_dt = pd.to_datetime(r['시작시간'])
                                e_dt = pd.to_datetime(r['종료시간'])
                                
                                if s_dt.date() <= curr_date <= e_dt.date():
                                    # Case 1: 당일 종료 (09:00~18:00)
                                    if s_dt.date() == e_dt.date() == curr_date:
                                        val = f"{s_dt.strftime('%H:%M')}~{e_dt.strftime('%H:%M')}"
                                    # Case 2: 첫날 (14:00~)
                                    elif curr_date == s_dt.date():
                                        val = f"{s_dt.strftime('%H:%M')}~"
                                    # Case 3: 마지막 날 (~11:30)
                                    elif curr_date == e_dt.date():
                                        val = f"~{e_dt.strftime('%H:%M')}"
                                    # Case 4: 중간 날짜
                                    else:
                                        val = " " 
                            except:
                                continue
                                
                    row_dict[col_name] = val
                plot_data.append(row_dict)

        # 표 그리기
        if plot_data:
            final_df = pd.DataFrame(plot_data).set_index(['Batch No.', 'Process'])
            
            def color_logic(v):
                if v and str(v).strip() != "": 
                    return 'background-color: #FFFF00; color: black; border: 1px solid #ddd; font-weight: bold;'
                elif v == " ":
                    return 'background-color: #FFFF00; border: 1px solid #ddd;'
                return 'border: 1px solid #ddd; color: transparent;'

            try:
                st.dataframe(final_df.style.map(color_logic), use_container_width=True)
            except:
                st.dataframe(final_df.style.applymap(color_logic), use_container_width=True)
        else:
            st.warning("조건에 맞는 데이터가 없습니다.")

elif menu == "방명록 (Guestbook)":
    st.title("📝 시스템 개선 건의사항 및 관리")
    with st.expander("➕ 새 건의사항 작성하기", expanded=True):
        with st.form(key='guest_form', clear_on_submit=True):
            user_name = st.text_input("작성자 이름")
            user_msg = st.text_area("내용")
            if st.form_submit_button("저장하기"):
                if user_msg.strip():
                    save_guestbook(user_name if user_name else "익명", user_msg)
                    st.success("✅ 저장되었습니다!")
                    st.rerun()

    st.write("---")
    df_guest = load_data(GUESTBOOK_FILE)
    if not df_guest.empty:
        edited_guest = st.data_editor(df_guest.iloc[::-1], use_container_width=True, num_rows="dynamic",
                                      column_config={"작성시간": st.column_config.TextColumn("작성시간", disabled=True)})
        if st.button("💾 방명록 변경사항 저장하기"):
            edited_guest.iloc[::-1].to_csv(GUESTBOOK_FILE, index=False, encoding="utf-8-sig")
            st.success("업데이트 완료! ✅")
            st.rerun()