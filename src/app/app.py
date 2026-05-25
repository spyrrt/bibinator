import streamlit as st
import pandas as pd
import threading
import plotly.express as px
import plotly.graph_objects as go
from theme import *
import mysql.connector
from mysql.connector import Error
import queries
from _config import DB_CONFIG, DB_NAME

_query_lock = threading.Lock()

# -------------------------------------
# --- PAGE CONFIG ---
# -------------------------------------

st.set_page_config(
    page_title="Bib-inator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------
# --- LOCAL CSS ---
#--------------------------------------
def local_css(filename):
    with open(filename) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("styles.css")

# ------------------------------------
# --- DATABASE CONNECTION ---
# ------------------------------------

@st.cache_resource
def get_connection(host, port, user, password, database):
    try:
        conn = mysql.connector.connect(
            host = host, port = port, user = user,
            password = password, database = database
        )
        return conn, None
    except Error as e:
        return None, str(e)

def run_query(conn, query, params = None):
    try:
        with _query_lock:
            conn.ping(reconnect=True)
            cursor = conn.cursor(dictionary = True)
            try:
                cursor.execute(query, params or ())
                rows = cursor.fetchall()
                return pd.DataFrame(rows), None
            except Error as e:
                return pd.DataFrame(), str(e)
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
    except Error as e:
        return pd.DataFrame(), str(e)

# --- Quick Stats (cached, runs once per session then hourly) ---
@st.cache_data(ttl=3600)
def fetch_quick_stats(_conn):
    df, _ = run_query(_conn, queries.QUICK_STATS)
    if df.empty:
        return 0, 0, 0, 0, "N/A"
    row = df.iloc[0]
    yr_range = (
        f"{int(row['min_yr'])}–{int(row['max_yr'])}"
        if row['min_yr'] is not None else "N/A"
    )
    return int(row['n_conf'] or 0), int(row['n_mag'] or 0), int(row['n_papers'] or 0), int(row['n_authors'] or 0), yr_range

# --- Metric Cards ---

def render_metrics(items):
    """items: list of (label, value, sub)"""
    cols = st.columns(len(items))
    for col, (label, value, sub) in zip(cols, items):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
                <div class="sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

# -------------------------------------
# --- SECTIONS ---
# -------------------------------------

def section_venue_profile(conn):
    st.markdown('<div class="our-header">📋 Conference / Journal Profile</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2,1])
    with col1:
        venue_type = st.radio("Venue type", ["Conference", "Journal"], horizontal=True)
    with col2:
        year_range = st.slider("Year range", 1936, 2014, (2000, 2014))

    _placeholder = "e.g. ICDE, VLDB, SIGMOD ..." if venue_type == "Conference" else "e.g. VLDB Journal, Information Systems ..."
    venue_name = st.text_input(f"Search {venue_type} name or acronym", placeholder=_placeholder)
    if not venue_name:
        st.info("Enter a venue name to load its profile")
        return

    # --- STATS ---
    like = f"%{venue_name}%"
    if venue_type == "Conference":
        df, err = run_query(conn, queries.VENUE_STATS_CONF,
                            (like, like, year_range[0], year_range[1]))
        rank_df, _ = run_query(conn, queries.VENUE_RANK_CONF, (like, like))
        yr_df,   _ = run_query(conn, queries.VENUE_YEAR_RANGE_CONF, (like, like))
        da_df,   _ = run_query(conn, queries.VENUE_DISTINCT_AUTHORS_CONF,
                                (like, like, year_range[0], year_range[1]))
    else:
        df, err = run_query(conn, queries.VENUE_STATS_MAG,
                            (like, year_range[0], year_range[1]))
        rank_df, _ = run_query(conn, queries.VENUE_RANK_MAG, (like,))
        yr_df,   _ = run_query(conn, queries.VENUE_YEAR_RANGE_MAG, (like,))
        da_df,   _ = run_query(conn, queries.VENUE_DISTINCT_AUTHORS_MAG,
                                (like, year_range[0], year_range[1]))
    if err:
        st.error(f"Query error: {err}")
        return
    rank_info = str(rank_df.iloc[0]["c_rank"]) if not rank_df.empty else "--"
    _yr_first = yr_df.iloc[0]["first_year"] if not yr_df.empty else None
    _yr_last  = yr_df.iloc[0]["last_year"]  if not yr_df.empty else None
    _df_years = df["year"] if not df.empty and "year" in df.columns else None
    abs_first = int(_yr_first) if _yr_first is not None else (int(_df_years.min()) if _df_years is not None else 0)
    abs_last  = int(_yr_last)  if _yr_last  is not None else (int(_df_years.max()) if _df_years is not None else 0)
    distinct_authors_ever = int(da_df.iloc[0]["distinct_authors_ever"]) if not da_df.empty else 0

    if df.empty:
        if rank_df.empty:
            st.warning(f"No venue found matching **{venue_name}**. Check the name and try again.")
        elif abs_first == 0 and abs_last == 0:
            st.warning(
                f"**{venue_name}** is listed in the ranking but has no linked articles in the dataset "
                f"(fuzzy matching may not have linked any papers to it)."
            )
        else:
            st.warning(
                f"No papers found for **{venue_name}** in {year_range[0]}–{year_range[1]}. "
                f"Try widening the year range."
            )
        return

    total_papers      = int(df["num_papers"].sum())
    avg_papers_yr     = round(df["num_papers"].mean(), 1)
    total_author_slots = int(df["total_authors"].sum())  # authorship slots (counts duplicates across years)
    avg_auth_paper    = round(total_author_slots / max(total_papers, 1), 2)
    avg_auth_year     = round(total_author_slots / max(len(df), 1), 1)

    render_metrics([
        ("Rank",              rank_info,                  venue_type),
        ("Total Papers",      f"{total_papers:,}",        f"avg {avg_papers_yr}/yr"),
        ("Distinct Authors",  f"{distinct_authors_ever:,}", f"avg {avg_auth_paper}/paper"),
        ("Avg Authors/Year",  str(avg_auth_year),         "in selected range"),
        ("Years Active",      f"{abs_first}–{abs_last}",  f"{len(df)} yr in range"),
    ])

    # --- LINE CHART ---
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown('<div class ="our-subheader">Annual Trends</div>', unsafe_allow_html=True)

    fig = go.Figure()
    for col, name, color in [
        ("num_papers", "Papers", COLORS[0]),
        ("total_authors", "Total Authors", COLORS[1]),
        ("distinct_authors", "Distinct Authors", COLORS[2]),
    ]:
        fig.add_trace(go.Scatter(
            x=df["year"], y=df[col], name=name,
            mode = "lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=5),
        ))
    apply_custom_theme(fig)
    fig.update_layout(height=360, margin=dict(l=0, r=0, t=20,b=0))
    st.plotly_chart(fig, width='stretch')

    # --- PAPERS TABLE ---
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown('<div class ="our-subheader">Papers</div>', unsafe_allow_html=True)

    if venue_type == "Conference":
        papers_df, err = run_query(conn, queries.VENUE_PAPERS_CONF,
                                    (like, like, year_range[0], year_range[1]))
    else:
        papers_df, err = run_query(conn, queries.VENUE_PAPERS_MAG,
                                    (like, year_range[0], year_range[1]))
    if err:
        st.error(f"Query error: {err}")
        papers_df = pd.DataFrame()

    if not papers_df.empty:
        st.dataframe(papers_df, width='stretch', hide_index=True)
    else:
        st.info("No paper details available")


def section_author_profile(conn):
    st.markdown('<div class="our-header">👤 Author Profile</div>', unsafe_allow_html=True)

    author_name = st.text_input("Author name", placeholder="e.g. Jeffrey D. Ullman")
    if not author_name:
        st.info("Enter an author name to load their profile.")
        return

    df, err = run_query(conn, queries.AUTHOR_ACTIVITY, (author_name, author_name))
    if err:
        st.error(f"Query error: {err}"); return
    if df.empty:
        st.warning("Author not found."); return
    first_yr = int(df["year"].min())
    last_yr  = int(df["year"].max())
    total    = int((df["conf_papers"] + df["journal_papers"]).sum())
    avg_py   = round(total / len(df), 2)

    render_metrics([
        ("First Published", str(first_yr), "year"),
        ("Last Published",  str(last_yr),  "year"),
        ("Total Papers",    str(total),    "all venues"),
        ("Avg / Year",      str(avg_py),   "papers"),
    ])

    fig = go.Figure()
    for col, name, color in [
        ("conf_papers",    "Conference", COLORS[0]),
        ("journal_papers", "Journal",    COLORS[1]),
    ]:
        fig.add_trace(go.Scatter(
            x=df["year"], y=df[col], name=name,
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=5),
        ))
    fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                      height=320, margin=dict(l=0, r=0, t=20, b=0),
                      xaxis_title="Year", yaxis_title="Papers")
    st.plotly_chart(fig, width='stretch')


def section_year_profile(conn):
    st.markdown('<div class="our-header">📅 Year Profile</div>', unsafe_allow_html=True)

    with st.form("year_profile_form"):
        year = st.number_input("Select year", min_value=1936, max_value=2014,
                               value=2000, step=1)
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            filter_venue = st.text_input("Filter by venue", placeholder="e.g. ICDE")
        with filter_col2:
            filter_author = st.text_input("Filter by author", placeholder="e.g. Jeffrey D. Ullman")
        with filter_col3:
            venue_kind = st.selectbox("Venue kind", ["All", "Conference", "Journal"])
        submitted = st.form_submit_button("Apply", use_container_width=True)

    if not submitted:
        st.info("Set your filters and click Apply.")
        return

    year = int(year)
    stats, err = run_query(conn, queries.YEAR_STATS, (year, year, year, year))
    if err or stats.empty:
        st.error(f"Query error: {err}"); return
    row = stats.iloc[0]
    num_papers    = int(row["num_papers"]    or 0)
    num_conf      = int(row["num_conf"]      or 0)
    num_journals  = int(row["num_journals"]  or 0)
    num_authors   = int(row["num_authors"]   or 0)
    num_dist_auth = int(row["num_distinct_authors"] or 0)

    type_val   = None if venue_kind == "All" else venue_kind.lower()
    venue_val  = f"%{filter_venue}%" if filter_venue else None
    author_val = filter_author or None
    papers_df, papers_err = run_query(
        conn, queries.YEAR_PAPERS,
        (year, venue_val, venue_val, venue_val, author_val, author_val,
         year, venue_val, venue_val, author_val, author_val,
         type_val, type_val)
    )
    if papers_err:
        st.error(f"Could not load publications: {papers_err}")
        papers_df = pd.DataFrame()

    render_metrics([
        ("Papers",          f"{num_papers:,}",    str(year)),
        ("Conferences",     str(num_conf),         "distinct"),
        ("Journals",        str(num_journals),     "distinct"),
        ("Authors",         f"{num_authors:,}",   "total"),
        ("Distinct Authors",f"{num_dist_auth:,}", "unique"),
    ])

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown('<div class="our-subheader">Publications</div>', unsafe_allow_html=True)
    if papers_df.empty:
        st.info("No paper data available for this year.")
    else:
        st.dataframe(papers_df, width='stretch', hide_index=True)


def section_linecharts(conn):
    st.markdown('<div class="our-header">📈 Line Charts</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Selected Venues", "By Category"])

    with tab1:
        venue_type = st.radio("Venue type", ["Conference", "Journal"], horizontal=True,
                              key="lc_venue_type")
        vtype = venue_type.lower()
        _placeholder = "e.g. ICDE, VLDB, SIGMOD ..." if venue_type == "Conference" else "e.g. VLDB Journal, Information Systems ..."
        venues_input = st.text_input("Venues (comma-separated)", placeholder=_placeholder)
        metric = st.selectbox("Metric", ["num_papers", "total_authors", "distinct_authors"],
                              format_func=lambda x: x.replace("_", " ").title())
        year_range = st.slider("Year range", 1936, 2014, (2000, 2014), key="lc_yr")

        venues = [v.strip() for v in venues_input.split(",") if v.strip()]
        if not venues:
            st.info("Enter venue names to generate the chart.")
        else:
            fig = go.Figure()
            for i, v in enumerate(venues):
                if vtype == "conference":
                    params = (f"%{v}%", f"%{v}%", year_range[0], year_range[1])
                else:
                    params = (f"%{v}%", year_range[0], year_range[1])
                df_v, err = run_query(conn, queries.venue_trend(metric, vtype), params)
                if err or df_v.empty: continue

                fig.add_trace(go.Scatter(
                    x=df_v["year"], y=df_v[metric],
                    name=v, mode="lines+markers",
                    line=dict(color=COLORS[i % len(COLORS)], width=2),
                    marker=dict(size=5),
                ))

            fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                              height=400, margin=dict(l=0, r=0, t=30, b=0),
                              yaxis_title=metric.replace("_", " ").title(),
                              xaxis_title="Year")
            st.plotly_chart(fig, width='stretch')

    with tab2:
        st.markdown('<div class="our-subheader">Venues per PrimaryFoR / BestSubjectArea per year</div>',
                    unsafe_allow_html=True)
        venue_cat_type = st.radio("Venue type", ["Conferences", "Journals"], horizontal=True,
                                  key="lc_cat_type")
        year_range2 = st.slider("Year range", 1936, 2014, (2000, 2014), key="lc_cat_yr")

        if venue_cat_type == "Conferences":
            opts_df, err = run_query(conn, queries.FOR_OPTIONS_CONF)
            if err:
                st.error(f"Query error: {err}")
            elif opts_df.empty:
                st.warning("No category data available (CONF_RANKING has no primary_for values).")
            else:
                opt_map = {
                    f"{int(r.primary_for)} – {r.for_name}": int(r.primary_for)
                    for r in opts_df.itertuples(index=False)
                }
                selected_labels = st.multiselect("Select PrimaryFoR categories",
                                                    list(opt_map.keys()), key="lc_cat_sel")
                if not selected_labels:
                    st.info("Select at least one category.")
                else:
                    fig = go.Figure()
                    for i, label in enumerate(selected_labels):
                        code = opt_map[label]
                        df_cat, _ = run_query(conn, queries.CATEGORY_TREND_CONF,
                                                (code, code, year_range2[0], year_range2[1]))
                        if not df_cat.empty:
                            fig.add_trace(go.Scatter(
                                x=df_cat["year"], y=df_cat["num_venues"],
                                name=label, mode="lines+markers",
                                line=dict(color=COLORS[i % len(COLORS)], width=2),
                                marker=dict(size=5),
                            ))
                    fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                                        height=360, margin=dict(l=0, r=0, t=30, b=0),
                                        yaxis_title="Venue count", xaxis_title="Year")
                    st.plotly_chart(fig, width='stretch')
        else:
            opts_df, err = run_query(conn, queries.FOR_OPTIONS_MAG)
            if err:
                st.error(f"Query error: {err}")
            elif opts_df.empty:
                st.warning("No category data available (MAG_RANKING has no best_subject_area values).")
            else:
                options = opts_df["best_subject_area"].tolist()
                selected = st.multiselect("Select Subject Areas", options,
                                            key="lc_cat_sel_mag")
                if not selected:
                    st.info("Select at least one subject area.")
                else:
                    fig = go.Figure()
                    for i, area in enumerate(selected):
                        df_cat, _ = run_query(conn, queries.CATEGORY_TREND_MAG,
                                                (area, area, year_range2[0], year_range2[1]))
                        if not df_cat.empty:
                            fig.add_trace(go.Scatter(
                                x=df_cat["year"], y=df_cat["num_venues"],
                                name=area, mode="lines+markers",
                                line=dict(color=COLORS[i % len(COLORS)], width=2),
                                marker=dict(size=5),
                            ))
                    fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                                        height=360, margin=dict(l=0, r=0, t=30, b=0),
                                        yaxis_title="Venue count", xaxis_title="Year")
                    st.plotly_chart(fig, width='stretch')


def section_barcharts(conn):
    st.markdown('<div class="our-header">📊 Bar Charts</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Venues Comparison", "Publisher Statistics"])

    with tab1:
        venue_type = st.radio("Venue type", ["Conference", "Journal"], horizontal=True,
                              key="bc_venue_type")
        vtype = venue_type.lower()
        _placeholder = "e.g. ICDE, VLDB, SIGMOD ..." if venue_type == "Conference" else "e.g. VLDB Journal, Information Systems ..."
        venues_input = st.text_input("Venues (comma-separated)", placeholder=_placeholder,
                                     key="bc_venues")
        metric = st.selectbox("Metric", [
            "total_papers", "avg_papers_per_year", "avg_authors_per_year"],
            format_func=lambda x: x.replace("_", " ").title())

        venues = [v.strip() for v in venues_input.split(",") if v.strip()]
        if not venues:
            st.info("Enter venue names to generate the chart.")
        else:
            rows = []
            for v in venues:
                if vtype == "conference":
                    params = (f"%{v}%", f"%{v}%")
                else:
                    params = (f"%{v}%",)
                df_v, _ = run_query(conn, queries.venue_aggregate(vtype), params)
                if not df_v.empty:
                    rows.append({"venue": v, metric: float(df_v.iloc[0][metric] or 0)})
            df_bar = pd.DataFrame(rows)

            if df_bar.empty:
                st.warning("No data to display.")
            else:
                fig = go.Figure(go.Bar(
                    x=df_bar["venue"], y=df_bar[metric],
                    marker=dict(color=COLORS[:len(df_bar)]),
                ))
                fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                                  height=350, margin=dict(l=0, r=0, t=30, b=0),
                                  yaxis_title=metric.replace("_", " ").title())
                fig.update_yaxes(rangemode="tozero")
                st.plotly_chart(fig, width='stretch')

    with tab2:
        st.markdown('<div class="our-subheader">Journal count per publisher, split by quartile</div>',
                    unsafe_allow_html=True)
        publisher_filter = st.text_input("Filter by publisher", placeholder="e.g. Elsevier, IEEE",
                                         key="bc_pub_filter")
        if not publisher_filter:
            st.info("Enter a publisher name to load the chart.")
        else:
            pub_like = f"%{publisher_filter}%" if publisher_filter else None
            df_pub, err = run_query(conn, queries.PUBLISHER_QUARTILE, (pub_like, pub_like))
            if err:
                st.error(err)
            elif df_pub.empty:
                st.warning("No data found.")
            else:
                pivot = df_pub.pivot_table(
                    index="publisher", columns="best_quartile",
                    values="num_journals", fill_value=0,
                )
                fig = go.Figure()
                for i, q in enumerate(["Q1", "Q2", "Q3", "Q4"]):
                    if q in pivot.columns:
                        fig.add_trace(go.Bar(
                            name=q,
                            x=pivot.index.tolist(),
                            y=pivot[q].tolist(),
                            marker_color=COLORS[i],
                        ))
                quartile_cols = [q for q in ["Q1", "Q2", "Q3", "Q4"] if q in pivot.columns]
                pivot["Total"] = pivot[quartile_cols].sum(axis=1)
                fig.add_trace(go.Bar(
                    name="Total",
                    x=pivot.index.tolist(),
                    y=pivot["Total"].tolist(),
                    marker_color=COLORS[4 % len(COLORS)],
                ))
                fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                                  barmode="group", height=380,
                                  margin=dict(l=0, r=0, t=30, b=0))
                fig.update_yaxes(rangemode="tozero")
                st.plotly_chart(fig, width='stretch')


def section_scatterplots(conn):
    st.markdown('<div class="our-header">🔵 Scatter Plots</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Journal Metrics", "Avg Authors vs. Papers per Year"])

    with tab1:
        numeric_cols = ["TotalDocs", "TotalDocs3y", "TotalCites3y", "TotalRefs",
                        "CitableDocs3y", "CitesPerDoc2y", "RefsPerDoc"]
        with st.form("sp_tab1_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                x_col = st.selectbox("X axis", numeric_cols, index=0)
            with c2:
                y_col = st.selectbox("Y axis", numeric_cols, index=1)
            with c3:
                color_col = st.selectbox("Color by", ["BestQuartile", "(none)"])
            submitted1 = st.form_submit_button("Apply", use_container_width=True)

        if not submitted1:
            st.info("Set your parameters and click Apply.")
        else:
            @st.cache_data(ttl=3600)
            def _fetch_journal_metrics(_conn):
                return run_query(_conn, queries.JOURNAL_METRICS)
            df_sc, err = _fetch_journal_metrics(conn)
            if err:
                st.error(err)
            else:
                color_arg = color_col if color_col != "(none)" else None
                fig = px.scatter(
                    df_sc, x=x_col, y=y_col,
                    color=color_arg,
                    hover_name="journal" if "journal" in df_sc.columns else None,
                    color_discrete_sequence=COLORS,
                    template="plotly_dark",
                )
                fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                                  height=480, margin=dict(l=0, r=0, t=30, b=0))
                fig.update_traces(marker=dict(size=7, opacity=0.8))
                st.plotly_chart(fig, width='stretch')

    with tab2:
        with st.form("sp_tab2_form"):
            venue_type = st.radio("Venue type", ["Conferences", "Journals"], horizontal=True,
                                  key="sp_type")
            submitted2 = st.form_submit_button("Apply", use_container_width=True)

        if not submitted2:
            st.info("Set your parameters and click Apply.")
        else:
            query = queries.SCATTER_TREND_CONF if venue_type == "Conferences" else queries.SCATTER_TREND_MAG
            df_avgs, err = run_query(conn, query)
            if err:
                st.error(err)
            elif df_avgs.empty:
                st.warning("No data found.")
            else:
                fig = px.scatter(df_avgs, x="num_papers", y="avg_authors",
                                 color="year", hover_data=["year"],
                                 color_continuous_scale="Blues",
                                 template="plotly_dark")
                fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                                  height=420, margin=dict(l=0, r=0, t=30, b=0),
                                  xaxis_title="Number of Papers",
                                  yaxis_title="Avg Authors per Paper")
                fig.update_traces(marker=dict(size=10, opacity=0.85))
                st.plotly_chart(fig, width='stretch')


# ------------------------------------
# --- AUTO-CONNECT ON FIRST LOAD ---
# ------------------------------------

if "db_conn" not in st.session_state:
    _conn, _err = get_connection(
        DB_CONFIG['host'], DB_CONFIG['port'],
        DB_CONFIG['user'], DB_CONFIG['password'], DB_NAME
    )
    st.session_state["db_conn"]     = _conn
    st.session_state["db_conn_err"] = _err or ""

# -------------------------------------
# --- SIDEBAR ---
# -------------------------------------

with st.sidebar:
    st.markdown("## 📚 Bibinator")
    st.markdown("MYE030 - Spring 2026")
    st.markdown("4443 - 4922 - 5373")
    st.markdown("---")

    st.markdown("### Navigation")
    page = st.radio("Navigation", [
        "🏠 Home",
        "📋 Venue Profile",
        "👤 Author Profile",
        "📅 Year Profile",
        "📈 Line Charts",
        "📊 Bar Charts",
        "🔵 Scatter Plots",
    ], label_visibility="collapsed")
    st.markdown("---")

    st.markdown("### Database Connection")

    db_host = st.text_input("Host", value=DB_CONFIG['host'])
    db_port = st.number_input("Port", value=DB_CONFIG['port'], step=1)
    db_user = st.text_input("User", value=DB_CONFIG['user'])
    db_password = st.text_input("Password", value=DB_CONFIG['password'], type="password")
    db_name = st.text_input("Database", value=DB_NAME)

    connect_btn = st.button("Connect", width='stretch')
    conn_state = st.session_state.get("db_conn", None)

    if connect_btn:
        conn_state, err = get_connection(db_host, int(db_port), db_user, db_password, db_name)
        if err:
            st.session_state["db_conn"]     = None
            st.session_state["db_conn_err"] = err
            st.markdown(f'<p class="conn-err"> {err}</p>', unsafe_allow_html=True)
        else:
            st.session_state["db_conn"]     = conn_state
            st.session_state["db_conn_err"] = ""
            st.markdown('<p class="conn-ok"> Connected!</p>', unsafe_allow_html=True)

    _conn_err = st.session_state.get("db_conn_err", "")
    if st.session_state.get("db_conn") is not None:
        st.markdown('<p class="conn-ok"> Live Database</p>', unsafe_allow_html=True)
    elif _conn_err:
        st.markdown(f'<p class="conn-err"> Not connected: {_conn_err}</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="conn-err"> Not connected</p>', unsafe_allow_html=True)
    st.markdown("---")

# -------------------------------------
# --- MAIN ---
# -------------------------------------

conn = st.session_state.get("db_conn", None)

if page == "🏠 Home":
    st.markdown('<div class="our-header">Bibinator - Bibliographic Data Explorer</div>', unsafe_allow_html=True)
    st.markdown("""
                Welcome to **Bibinator**, an interactive tool for exploring publication data from
    conferences and journals (sourced from *dblp*, *iCORE*, and *Kaggle*).

    **Available sections:**

    | Section | What you can explore |
    |---|---|
    | 📋 Venue Profile | Stats & trends for a specific conference or journal |
    | 👤 Author Profile | Publication history of a given author |
    | 📅 Year Profile | Overview of a publication year with filters |
    | 📈 Line Charts | Multi-venue or per-category annual trends |
    | 📊 Bar Charts | Venue comparisons; publisher-quartile breakdown |
    | 🔵 Scatter Plots | Correlations between journal metrics |

    Use the **sidebar** to verify or update the database connection.
    """)

    st.markdown("---")
    st.markdown("#### Quick Stats")
    if conn is None:
        st.warning("Connect to the database to see stats.")
    else:
        with st.spinner("Loading stats..."):
            n_conf, n_mag, n_papers, n_authors, yr_range = fetch_quick_stats(conn)
        render_metrics([
            ("Conferences", f"{n_conf:,}",    "indexed"),
            ("Journals",    f"{n_mag:,}",     "indexed"),
            ("Papers",      f"{n_papers:,}",  "total"),
            ("Authors",     f"{n_authors:,}", "unique"),
            ("Years",       yr_range,          "coverage"),
        ])

elif conn is None:
    st.warning("⚠ Database not connected. Check the connection settings in the sidebar.")

elif page == "📋 Venue Profile":
    section_venue_profile(conn)

elif page == "👤 Author Profile":
    section_author_profile(conn)

elif page == "📅 Year Profile":
    section_year_profile(conn)

elif page == "📈 Line Charts":
    section_linecharts(conn)

elif page == "📊 Bar Charts":
    section_barcharts(conn)

elif page == "🔵 Scatter Plots":
    section_scatterplots(conn)
