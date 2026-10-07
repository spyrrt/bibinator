# Approximate row counts for each venue/article/author table, plus the overall year range.
QUICK_STATS = """
    SELECT
        (SELECT table_rows FROM information_schema.TABLES
            WHERE table_schema = DATABASE() AND table_name = 'CONF_RANKING')  AS n_conf,
        (SELECT table_rows FROM information_schema.TABLES
            WHERE table_schema = DATABASE() AND table_name = 'MAG_RANKING')   AS n_mag,
        (SELECT table_rows FROM information_schema.TABLES
            WHERE table_schema = DATABASE() AND table_name = 'ARTICLES')      AS n_papers,
        (SELECT table_rows FROM information_schema.TABLES
            WHERE table_schema = DATABASE() AND table_name = 'AUTHOR_LOOKUP') AS n_authors,
        (SELECT MIN(y) FROM (
            SELECT year AS y FROM CONF_ARTICLE_INFO
            UNION SELECT year FROM MAG_ARTICLE_INFO
        ) u) AS min_yr,
        (SELECT MAX(y) FROM (
            SELECT year AS y FROM CONF_ARTICLE_INFO
            UNION SELECT year FROM MAG_ARTICLE_INFO
        ) u) AS max_yr
"""

# Papers, total author slots, and distinct authors per year for a conference (by title or acronym).
VENUE_STATS_CONF = """
    SELECT cai.year                        AS year,
           COUNT(DISTINCT cai.article_id)  AS num_papers,
           COUNT(aa.author_id)             AS total_authors,
           COUNT(DISTINCT aa.author_id)    AS distinct_authors
    FROM CONF_ARTICLE_INFO cai
    JOIN CONF_RANKING cr    ON cr.conf_id    = cai.conf_id
    JOIN ARTICLE_AUTHORS aa ON aa.article_id = cai.article_id
    WHERE (cr.title LIKE %s OR cr.acronym LIKE %s) AND cai.year BETWEEN %s AND %s
    GROUP BY cai.year ORDER BY cai.year
"""

# Papers, total author slots, and distinct authors per year for a journal (by title).
VENUE_STATS_MAG = """
    SELECT mai.year                        AS year,
           COUNT(DISTINCT mai.article_id)  AS num_papers,
           COUNT(aa.author_id)             AS total_authors,
           COUNT(DISTINCT aa.author_id)    AS distinct_authors
    FROM MAG_ARTICLE_INFO mai
    JOIN MAG_RANKING mr     ON mr.mag_id     = mai.mag_id
    JOIN ARTICLE_AUTHORS aa ON aa.article_id = mai.article_id
    WHERE mr.title LIKE %s AND mai.year BETWEEN %s AND %s
    GROUP BY mai.year ORDER BY mai.year
"""

# Full article list (title, authors, year) published at a conference in a given year range.
VENUE_PAPERS_CONF = """
    SELECT ar.article_id AS id, ar.title,
           GROUP_CONCAT(DISTINCT au.author_name SEPARATOR ', ') AS authors,
           cai.year
    FROM ARTICLES ar
    JOIN CONF_ARTICLE_INFO cai ON cai.article_id = ar.article_id
    JOIN CONF_RANKING cr       ON cr.conf_id     = cai.conf_id
    JOIN ARTICLE_AUTHORS aa    ON aa.article_id  = ar.article_id
    JOIN AUTHOR_LOOKUP au            ON au.author_id   = aa.author_id
    WHERE (cr.title LIKE %s OR cr.acronym LIKE %s) AND cai.year BETWEEN %s AND %s
    GROUP BY ar.article_id, ar.title, cai.year
    ORDER BY cai.year DESC
"""

# Full article list (title, authors, year) published in a journal in a given year range.
VENUE_PAPERS_MAG = """
    SELECT ar.article_id AS id, ar.title,
           GROUP_CONCAT(DISTINCT au.author_name SEPARATOR ', ') AS authors,
           mai.year
    FROM ARTICLES ar
    JOIN MAG_ARTICLE_INFO mai  ON mai.article_id = ar.article_id
    JOIN MAG_RANKING mr        ON mr.mag_id      = mai.mag_id
    JOIN ARTICLE_AUTHORS aa    ON aa.article_id  = ar.article_id
    JOIN AUTHOR_LOOKUP au            ON au.author_id   = aa.author_id
    WHERE mr.title LIKE %s AND mai.year BETWEEN %s AND %s
    GROUP BY ar.article_id, ar.title, mai.year
    ORDER BY mai.year DESC
"""

# Conference and journal paper counts per year for a named author.
AUTHOR_ACTIVITY = """
    SELECT year,
           SUM(conf_papers)    AS conf_papers,
           SUM(journal_papers) AS journal_papers
    FROM (
        SELECT cai.year                        AS year,
               COUNT(DISTINCT cai.article_id)  AS conf_papers,
               0                               AS journal_papers
        FROM ARTICLE_AUTHORS aa
        JOIN AUTHOR_LOOKUP au         ON au.author_id  = aa.author_id
        JOIN CONF_ARTICLE_INFO cai ON cai.article_id = aa.article_id
        WHERE au.author_name = %s
        GROUP BY cai.year
        UNION ALL
        SELECT mai.year                        AS year,
               0                               AS conf_papers,
               COUNT(DISTINCT mai.article_id)  AS journal_papers
        FROM ARTICLE_AUTHORS aa
        JOIN AUTHOR_LOOKUP au        ON au.author_id  = aa.author_id
        JOIN MAG_ARTICLE_INFO mai ON mai.article_id = aa.article_id
        WHERE au.author_name = %s
        GROUP BY mai.year
    ) sub
    GROUP BY year ORDER BY year
"""

# Global summary stats for a given year: total papers, active conferences, journals,
# total author slots, and distinct authors across both venue types.
YEAR_STATS = """
    WITH conf AS (
        SELECT COUNT(DISTINCT cai.article_id) AS n_papers,
               COUNT(DISTINCT cai.conf_id)    AS n_venues,
               COUNT(aa.author_id)            AS n_authors
        FROM CONF_ARTICLE_INFO cai
        JOIN ARTICLE_AUTHORS aa ON aa.article_id = cai.article_id
        WHERE cai.year = %s
    ), jrnl AS (
        SELECT COUNT(DISTINCT mai.article_id) AS n_papers,
               COUNT(DISTINCT mai.mag_id)     AS n_venues,
               COUNT(aa.author_id)            AS n_authors
        FROM MAG_ARTICLE_INFO mai
        JOIN ARTICLE_AUTHORS aa ON aa.article_id = mai.article_id
        WHERE mai.year = %s
    ), dist AS (
        SELECT COUNT(DISTINCT author_id) AS n_dist FROM (
            SELECT aa.author_id FROM CONF_ARTICLE_INFO cai
            JOIN ARTICLE_AUTHORS aa ON aa.article_id = cai.article_id WHERE cai.year = %s
            UNION
            SELECT aa.author_id FROM MAG_ARTICLE_INFO mai
            JOIN ARTICLE_AUTHORS aa ON aa.article_id = mai.article_id WHERE mai.year = %s
        ) u
    )
    SELECT conf.n_papers + jrnl.n_papers   AS num_papers,
           conf.n_venues                   AS num_conf,
           jrnl.n_venues                   AS num_journals,
           conf.n_authors + jrnl.n_authors AS num_authors,
           dist.n_dist                     AS num_distinct_authors
    FROM conf, jrnl, dist
"""

# All papers (conf + journal) published in a given year, with optional filters
# for venue type, venue name, and author name.
YEAR_PAPERS = """
    SELECT * FROM (
        SELECT ar.article_id AS id, ar.title,
               GROUP_CONCAT(DISTINCT au.author_name SEPARATOR ', ') AS authors,
               cr.title AS venue_name, 'conference' AS type
        FROM ARTICLES ar
        JOIN CONF_ARTICLE_INFO cai ON cai.article_id = ar.article_id
        JOIN CONF_RANKING cr       ON cr.conf_id      = cai.conf_id
        JOIN ARTICLE_AUTHORS aa    ON aa.article_id   = ar.article_id
        JOIN AUTHOR_LOOKUP au      ON au.author_id    = aa.author_id
        WHERE cai.year = %s
          AND (%s IS NULL OR cr.title LIKE %s OR cr.acronym LIKE %s)
          AND (%s IS NULL OR ar.article_id IN (
              SELECT aa2.article_id FROM ARTICLE_AUTHORS aa2
              JOIN AUTHOR_LOOKUP au2 ON au2.author_id = aa2.author_id
              WHERE au2.author_name = %s
          ))
        GROUP BY ar.article_id, ar.title, cr.title
        UNION ALL
        SELECT ar.article_id AS id, ar.title,
               GROUP_CONCAT(DISTINCT au.author_name SEPARATOR ', ') AS authors,
               mr.title AS venue_name, 'journal' AS type
        FROM ARTICLES ar
        JOIN MAG_ARTICLE_INFO mai  ON mai.article_id = ar.article_id
        JOIN MAG_RANKING mr        ON mr.mag_id      = mai.mag_id
        JOIN ARTICLE_AUTHORS aa    ON aa.article_id  = ar.article_id
        JOIN AUTHOR_LOOKUP au      ON au.author_id   = aa.author_id
        WHERE mai.year = %s
          AND (%s IS NULL OR mr.title LIKE %s)
          AND (%s IS NULL OR ar.article_id IN (
              SELECT aa2.article_id FROM ARTICLE_AUTHORS aa2
              JOIN AUTHOR_LOOKUP au2 ON au2.author_id = aa2.author_id
              WHERE au2.author_name = %s
          ))
        GROUP BY ar.article_id, ar.title, mr.title
    ) all_papers
    WHERE (%s IS NULL OR type = %s)
"""

# iCORE rank (A*, A, B, C, …) for a conference matched by title or acronym.
VENUE_RANK_CONF = """
    SELECT cr.conf_rank AS c_rank FROM CONF_RANKING cr
    WHERE (cr.title LIKE %s OR cr.acronym LIKE %s) LIMIT 1
"""

# Kaggle best quartile (Q1–Q4) for a journal matched by title.
VENUE_RANK_MAG = """
    SELECT mr.best_quartile AS c_rank FROM MAG_RANKING mr
    WHERE mr.title LIKE %s LIMIT 1
"""

# Total distinct authors who published at a conference across the selected year range.
VENUE_DISTINCT_AUTHORS_CONF = """
    SELECT COUNT(DISTINCT aa.author_id) AS distinct_authors_ever
    FROM CONF_ARTICLE_INFO cai
    JOIN CONF_RANKING cr    ON cr.conf_id    = cai.conf_id
    JOIN ARTICLE_AUTHORS aa ON aa.article_id = cai.article_id
    WHERE (cr.title LIKE %s OR cr.acronym LIKE %s)
      AND cai.year BETWEEN %s AND %s
"""

# Total distinct authors who published in a journal across the selected year range.
VENUE_DISTINCT_AUTHORS_MAG = """
    SELECT COUNT(DISTINCT aa.author_id) AS distinct_authors_ever
    FROM MAG_ARTICLE_INFO mai
    JOIN MAG_RANKING mr     ON mr.mag_id     = mai.mag_id
    JOIN ARTICLE_AUTHORS aa ON aa.article_id = mai.article_id
    WHERE mr.title LIKE %s
      AND mai.year BETWEEN %s AND %s
"""

# First and last year a conference appears in the data.
VENUE_YEAR_RANGE_CONF = """
    SELECT MIN(cai.year) AS first_year, MAX(cai.year) AS last_year
    FROM CONF_ARTICLE_INFO cai
    JOIN CONF_RANKING cr ON cr.conf_id = cai.conf_id
    WHERE (cr.title LIKE %s OR cr.acronym LIKE %s)
"""

# First and last year a journal appears in the data.
VENUE_YEAR_RANGE_MAG = """
    SELECT MIN(mai.year) AS first_year, MAX(mai.year) AS last_year
    FROM MAG_ARTICLE_INFO mai
    JOIN MAG_RANKING mr ON mr.mag_id = mai.mag_id
    WHERE mr.title LIKE %s
"""

# Per-year trend for one metric (num_papers / total_authors / distinct_authors)
def venue_trend(metric: str, venue_type: str) -> str:
    if venue_type == "conference":
        return f"""
    SELECT cai.year                        AS year,
           COUNT(DISTINCT cai.article_id)  AS num_papers,
           COUNT(aa.author_id)             AS total_authors,
           COUNT(DISTINCT aa.author_id)    AS distinct_authors
    FROM CONF_ARTICLE_INFO cai
    JOIN CONF_RANKING cr    ON cr.conf_id    = cai.conf_id
    JOIN ARTICLE_AUTHORS aa ON aa.article_id = cai.article_id
    WHERE (cr.title LIKE %s OR cr.acronym LIKE %s) AND cai.year BETWEEN %s AND %s
    GROUP BY cai.year
    ORDER BY cai.year
    """
    else:
        return f"""
    SELECT mai.year                        AS year,
           COUNT(DISTINCT mai.article_id)  AS num_papers,
           COUNT(aa.author_id)             AS total_authors,
           COUNT(DISTINCT aa.author_id)    AS distinct_authors
    FROM MAG_ARTICLE_INFO mai
    JOIN MAG_RANKING mr     ON mr.mag_id     = mai.mag_id
    JOIN ARTICLE_AUTHORS aa ON aa.article_id = mai.article_id
    WHERE mr.title LIKE %s AND mai.year BETWEEN %s AND %s
    GROUP BY mai.year
    ORDER BY mai.year
    """

# All-time totals and per-year averages (papers, authors) for a venue of a specific type.
def venue_aggregate(venue_type: str) -> str:
    if venue_type == "conference":
        return """
    SELECT COUNT(DISTINCT cai.article_id)                                    AS total_papers,
           COUNT(DISTINCT cai.article_id) / NULLIF(COUNT(DISTINCT cai.year), 0) AS avg_papers_per_year,
           COUNT(aa.author_id)            / NULLIF(COUNT(DISTINCT cai.year), 0) AS avg_authors_per_year
    FROM CONF_ARTICLE_INFO cai
    JOIN CONF_RANKING cr         ON cr.conf_id    = cai.conf_id
    LEFT JOIN ARTICLE_AUTHORS aa ON aa.article_id = cai.article_id
    WHERE (cr.title LIKE %s OR cr.acronym LIKE %s)
    """
    else:
        return """
    SELECT COUNT(DISTINCT mai.article_id)                                    AS total_papers,
           COUNT(DISTINCT mai.article_id) / NULLIF(COUNT(DISTINCT mai.year), 0) AS avg_papers_per_year,
           COUNT(aa.author_id)            / NULLIF(COUNT(DISTINCT mai.year), 0) AS avg_authors_per_year
    FROM MAG_ARTICLE_INFO mai
    JOIN MAG_RANKING mr          ON mr.mag_id     = mai.mag_id
    LEFT JOIN ARTICLE_AUTHORS aa ON aa.article_id = mai.article_id
    WHERE mr.title LIKE %s
    """

# Distribution of journals across quartiles (Q1–Q4).
QUARTILE_DIST = """
    SELECT best_quartile, COUNT(*) AS cnt
    FROM MAG_RANKING
    WHERE best_quartile IS NOT NULL AND best_quartile != ''
    GROUP BY best_quartile ORDER BY best_quartile
"""

# Number of journals per publisher per quartile, with optional publisher name filter.
PUBLISHER_QUARTILE = """
    SELECT publisher, best_quartile, COUNT(*) AS num_journals
    FROM MAG_RANKING
    WHERE publisher IS NOT NULL AND publisher != ''
      AND best_quartile IS NOT NULL AND best_quartile != ''
      AND (%s IS NULL OR publisher LIKE %s)
    GROUP BY publisher, best_quartile
    ORDER BY publisher, best_quartile
"""

# All Kaggle metrics for every journal, cast to numeric types for scatter plotting.
JOURNAL_METRICS = """
    SELECT title AS journal,
           CAST(NULLIF(total_docs,       '') AS UNSIGNED)      AS TotalDocs,
           CAST(NULLIF(total_docs_3y,    '') AS UNSIGNED)      AS TotalDocs3y,
           CAST(NULLIF(total_cites_3y,   '') AS UNSIGNED)      AS TotalCites3y,
           CAST(NULLIF(total_refs,       '') AS UNSIGNED)      AS TotalRefs,
           CAST(NULLIF(citable_docs_3y,  '') AS UNSIGNED)      AS CitableDocs3y,
           CAST(NULLIF(cites_per_doc_2y, '') AS DECIMAL(10,4)) AS CitesPerDoc2y,
           CAST(NULLIF(refs_per_doc,     '') AS DECIMAL(10,4)) AS RefsPerDoc,
           CASE WHEN best_quartile IN ('Q1','Q2','Q3','Q4')
                THEN best_quartile ELSE NULL END AS BestQuartile
    FROM MAG_RANKING
"""

# Distinct Field of Research codes (with names) assigned to conferences.
FOR_OPTIONS_CONF = """
    SELECT DISTINCT cr.primary_for,
           COALESCE(fl.for_name, CONCAT('FoR ', cr.primary_for)) AS for_name
    FROM CONF_RANKING cr
    LEFT JOIN FOR_LOOKUP fl ON fl.for_code = cr.primary_for
    WHERE cr.primary_for IS NOT NULL
    ORDER BY cr.primary_for
"""

# Distinct subject area strings assigned to journals.
FOR_OPTIONS_MAG = """
    SELECT DISTINCT bsal.best_subject_area_name AS best_subject_area
    FROM MAG_RANKING mr
    JOIN BEST_SUBJECT_AREA_LOOKUP bsal ON bsal.best_subject_area_id = mr.best_subject_area_id
    WHERE mr.best_subject_area_id IS NOT NULL
    ORDER BY best_subject_area
"""

# Number of active conferences per Field of Research per year (for line chart).
CATEGORY_TREND_CONF = """
    SELECT cai.year, cr.primary_for, COUNT(DISTINCT cai.conf_id) AS num_venues
    FROM CONF_ARTICLE_INFO cai
    JOIN CONF_RANKING cr ON cr.conf_id = cai.conf_id
    WHERE (%s IS NULL OR cr.primary_for = %s)
      AND cai.year BETWEEN %s AND %s
    GROUP BY cai.year, cr.primary_for
    ORDER BY cai.year
"""

# Number of active journals per subject area per year (for line chart).
CATEGORY_TREND_MAG = """
    SELECT mai.year,
           bsal.best_subject_area_name AS best_subject_area,
           COUNT(DISTINCT mai.mag_id) AS num_venues
    FROM MAG_ARTICLE_INFO mai
    JOIN MAG_RANKING mr ON mr.mag_id = mai.mag_id
    JOIN BEST_SUBJECT_AREA_LOOKUP bsal ON bsal.best_subject_area_id = mr.best_subject_area_id
    WHERE (%s IS NULL OR bsal.best_subject_area_name = %s)
      AND mai.year BETWEEN %s AND %s
    GROUP BY mai.year, bsal.best_subject_area_name
    ORDER BY mai.year
"""

# Average authors per paper and total papers per year across all conferences (scatter data).
SCATTER_TREND_CONF = """
    SELECT cai.year,
           COUNT(aa.author_id) / NULLIF(COUNT(DISTINCT cai.article_id), 0) AS avg_authors,
           COUNT(DISTINCT cai.article_id) AS num_papers
    FROM CONF_ARTICLE_INFO cai
    JOIN ARTICLE_AUTHORS aa ON aa.article_id = cai.article_id
    GROUP BY cai.year ORDER BY cai.year
"""

# Average authors per paper and total papers per year across all journals (scatter data).
SCATTER_TREND_MAG = """
    SELECT mai.year,
           COUNT(aa.author_id) / NULLIF(COUNT(DISTINCT mai.article_id), 0) AS avg_authors,
           COUNT(DISTINCT mai.article_id) AS num_papers
    FROM MAG_ARTICLE_INFO mai
    JOIN ARTICLE_AUTHORS aa ON aa.article_id = mai.article_id
    GROUP BY mai.year ORDER BY mai.year
"""
