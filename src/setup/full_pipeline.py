import time
import unicodedata
import mysql.connector
import pandas as pd
from pathlib import Path
import fuzzy_matching
import test_tables
import export_tables
import backup
import csv as _csv
from _config import DB_NAME, DB_CONFIG, RUN_TESTS, DROP_STAGING_TABLES, EXPORT_FINAL_TABLES, CREATE_BACKUP

INPUT_DIR = Path(__file__).parent.parent.parent / 'data' / 'original_files'

def _normalize_name(name):
    nfkd = unicodedata.normalize('NFKD', name)
    stripped = ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')
    return stripped.title()

def _load_infile(cursor, table, filename, fields_term, lines_term=r'\r\n', enclosed_by=None):
    path = (INPUT_DIR / filename).as_posix()
    enclosed = f"OPTIONALLY ENCLOSED BY '{enclosed_by}' " if enclosed_by else ''
    cursor.execute(
        f"LOAD DATA LOCAL INFILE '{path}' "
        f"INTO TABLE {table} "
        f"FIELDS TERMINATED BY '{fields_term}' {enclosed}"
        f"LINES TERMINATED BY '{lines_term}' "
        "IGNORE 1 LINES;"
    )


def _executemany_batched(cursor, query, records, batch_size=1000):
    for i in range(0, len(records), batch_size):
        cursor.executemany(query, records[i:i + batch_size])


#######################
### STARTING TABLES ###
#######################

def create_starting_conf_articles(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS starting_conf_articles (
            id INT, author VARCHAR(255), booktitle VARCHAR(255), cdrom VARCHAR(255),
            cite VARCHAR(255), cite_label VARCHAR(255), crossref VARCHAR(255),
            editor VARCHAR(255), ee VARCHAR(255), i VARCHAR(255), articleKey VARCHAR(255),
            mdate VARCHAR(255), month VARCHAR(255), note VARCHAR(255), number VARCHAR(255),
            pages VARCHAR(255), publtype VARCHAR(255), sub VARCHAR(255), sup VARCHAR(255),
            title VARCHAR(255), titleBibtex VARCHAR(255), tt VARCHAR(255),
            url VARCHAR(255), year INT);
    ''')
    _load_infile(cursor, 'starting_conf_articles', 'input_inproceedings.csv', ';', enclosed_by='"')
    cursor.execute("UPDATE starting_conf_articles SET booktitle = REPLACE(booktitle, '\"', '')")

def create_starting_conf_ranking(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS starting_conf_ranking (
            id INT, title VARCHAR(255), acronym VARCHAR(255), source VARCHAR(255),
            conf_rank VARCHAR(255), dblp VARCHAR(255), primaryFoR INT);
    ''')
    _load_infile(cursor, 'starting_conf_ranking', 'iCore26_KilledColumnsForLoading.csv', ',', enclosed_by='"')
    cursor.execute("UPDATE starting_conf_ranking SET title = REPLACE(title, '\"', '')")

def create_starting_mag_articles(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS starting_mag_articles (
            id INT, author VARCHAR(255), booktitle VARCHAR(255), cdrom VARCHAR(255),
            cite VARCHAR(255), citeLabel VARCHAR(255), crossref VARCHAR(255),
            editor VARCHAR(255), ee VARCHAR(255), i VARCHAR(255), journal VARCHAR(255),
            articleKey VARCHAR(255), mdate VARCHAR(255), month VARCHAR(255),
            note VARCHAR(255), number VARCHAR(255), pages VARCHAR(255),
            publisher VARCHAR(255), publtype VARCHAR(255), rating VARCHAR(255),
            reviewid VARCHAR(255), sub VARCHAR(255), sup VARCHAR(255),
            title VARCHAR(255), titleBibtex VARCHAR(255), tt VARCHAR(255),
            url VARCHAR(255), volume VARCHAR(255), year INT);
    ''')
    _load_infile(cursor, 'starting_mag_articles', 'input_article.csv', ';', enclosed_by='"')
    cursor.execute("UPDATE starting_mag_articles SET journal = REPLACE(journal, '\"', '')")

def create_starting_mag_ranking(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS starting_mag_ranking (
            mag_rank INT, Title VARCHAR(255), OA VARCHAR(255), Country VARCHAR(255),
            SJR_index DECIMAL(10,4), CiteScore VARCHAR(255), H_index VARCHAR(255),
            Best_Quartile VARCHAR(255), Best_Categories VARCHAR(255),
            Best_Subject_Area VARCHAR(255), Best_Subject_Rank VARCHAR(255),
            Total_Docs INT, Total_Docs_three_y INT,
            Total_Refs INT, Total_Cites_three_y INT,
            Citable_Docs_three_y INT, Cites_or_Doc_two_y DECIMAL(10,4),
            Refs_or_Doc DECIMAL(10,4), Publisher VARCHAR(255),
            Core_Collection VARCHAR(255), Coverage VARCHAR(255), Active VARCHAR(255),
            In_Press VARCHAR(255), ISO_Language_Code VARCHAR(255),
            ASJC_Codes VARCHAR(255), Life_Sciences VARCHAR(255),
            Social_Sciences VARCHAR(255), Physical_Sciences VARCHAR(255),
            Health_Sciences VARCHAR(255), General VARCHAR(255),
            Agricultural_and_Biological_Sciences VARCHAR(255),
            Arts_and_Humanities VARCHAR(255),
            Biochemistry_Genetics_and_Molecular_Biology VARCHAR(255),
            Business_Management_and_Accounting VARCHAR(255),
            Chemical_Engineering VARCHAR(255), Chemistry VARCHAR(255),
            Computer_Science VARCHAR(255), Decision_Sciences VARCHAR(255),
            Earth_and_Planetary_Sciences VARCHAR(255),
            Economics_Econometrics_and_Finance VARCHAR(255), Energy VARCHAR(255),
            Engineering VARCHAR(255), Environmental_Science VARCHAR(255),
            Immunology_and_Microbiology VARCHAR(255), Materials_Science VARCHAR(255),
            Mathematics VARCHAR(255), Medicine VARCHAR(255),
            Neuroscience VARCHAR(255), Nursing VARCHAR(255),
            Pharmacology_Toxicology_and_Pharmaceutics VARCHAR(255),
            Physics_and_Astronomy VARCHAR(255), Psychology VARCHAR(255),
            Social_Sciences_second_appearance VARCHAR(255), Veterinary VARCHAR(255),
            Dentistry VARCHAR(255), Health_Professions VARCHAR(255));
    ''')
    _load_infile(cursor, 'starting_mag_ranking', 'journal_ranking_data_raw.csv', ',', r'\n', enclosed_by='"')
    cursor.execute("UPDATE starting_mag_ranking SET Title = REPLACE(Title, '\"', '')")


#####################
### LOOKUP TABLES ###
#####################

def create_author_lookup(cursor):
    cursor.execute('SELECT DISTINCT author_name FROM intermediate_article_author WHERE author_name IS NOT NULL')
    unique_names = [row[0] for row in cursor.fetchall()]

    records = list(enumerate(unique_names, start=1))
    _executemany_batched(cursor,
        'INSERT INTO AUTHOR_LOOKUP (author_id, author_name) VALUES (%s, %s)',
        records
    )


def create_for_lookup(cursor):
    df = pd.read_excel(INPUT_DIR / 'icoreCategories.xlsx', header=None, names=['code', 'name'])
    df['code'] = pd.to_numeric(df['code'], errors='coerce')
    df = df.dropna(subset=['code'])
    df['code'] = df['code'].astype(int)
    top_level = df[df['code'] < 10000][['code', 'name']].drop_duplicates()
    records = [(int(code), str(name).strip()) for code, name in top_level.itertuples(index=False)]
    _executemany_batched(cursor,
        'INSERT INTO FOR_LOOKUP (for_code, for_name) VALUES (%s, %s)',
        records
    )

def create_subject_area_lookup(cursor):
    with open(INPUT_DIR / 'bestSubjectArea.csv', encoding='utf-8', newline='') as f:
        reader = _csv.reader(f)
        next(reader)
        canonical = {row[0].strip() for row in reader if row and row[0].strip()}

    cursor.execute('SELECT DISTINCT best_subject_area FROM intermediate_mag_ranking WHERE best_subject_area IS NOT NULL')
    junk = {'Q1', 'Q2', 'Q3', 'Q4'}
    extra = set()
    for (raw,) in cursor.fetchall():
        cleaned = raw.replace('[', '').replace(']', '').replace('"', '').replace("'", '').strip()
        try:
            float(cleaned)
            continue
        except ValueError:
            pass
        if cleaned and cleaned not in junk and cleaned not in canonical:
            extra.add(cleaned)

    names = sorted(canonical | extra)
    records = [(i, name) for i, name in enumerate(names, start=1)]
    _executemany_batched(cursor,
        'INSERT INTO BEST_SUBJECT_AREA_LOOKUP (best_subject_area_id, best_subject_area_name) VALUES (%s, %s)',
        records
    )


###########################
### INTERMEDIATE TABLES ###
###########################

def _format_names_article_ids(cursor, table):
    cursor.execute(f'SELECT id, author FROM {table}')
    rows = cursor.fetchall()

    ids, names = [], []
    for article_id, authors_str in rows:
        if authors_str:
            seen = set()
            for name in authors_str.split('|'):
                name = _normalize_name(name.replace('"', '').strip())
                if name and name not in seen:
                    seen.add(name)
                    ids.append(int(article_id))
                    names.append(name)
        else:
            ids.append(int(article_id))
            names.append('no_author')

    return ids, names

def create_intermediate_article_author(cursor):
    cursor.execute('DROP TABLE IF EXISTS intermediate_article_author;')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intermediate_article_author (
            article_id INT, author_name VARCHAR(255));
    ''')

    conf_article_ids, conf_author_names = _format_names_article_ids(cursor, 'starting_conf_articles')
    mag_article_ids, mag_author_names = _format_names_article_ids(cursor, 'starting_mag_articles')

    records = list(zip(conf_article_ids + mag_article_ids, conf_author_names + mag_author_names))

    _executemany_batched(cursor,
        'INSERT INTO intermediate_article_author (article_id, author_name) VALUES (%s, %s)',
        records
    )

def create_intermediate_conf_articles(cursor):
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_iaa_article_id ON intermediate_article_author (article_id);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_iaa_author_name ON intermediate_article_author (author_name);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_au_author_name  ON AUTHOR_LOOKUP (author_name);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sca_id          ON starting_conf_articles (id);')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intermediate_conf_articles (
            article_id INT, author_id INT, title VARCHAR(255), year INT, conf_title VARCHAR(255),
            FOREIGN KEY (author_id) REFERENCES AUTHOR_LOOKUP(author_id)
        );
    ''')
    cursor.execute('''
        INSERT INTO intermediate_conf_articles (article_id, author_id, title, year, conf_title)
        SELECT iaa.article_id, au.author_id, s.title, s.year, s.booktitle
        FROM intermediate_article_author iaa
        JOIN AUTHOR_LOOKUP au ON iaa.author_name = au.author_name
        JOIN starting_conf_articles s ON iaa.article_id = s.id
        WHERE iaa.article_id IS NOT NULL;
    ''')

def create_intermediate_conf_ranking(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intermediate_conf_ranking (
            conf_id INT, title VARCHAR(255), acronym VARCHAR(255), conf_rank VARCHAR(255), primary_for INT
        );
    ''')
    cursor.execute('''
        INSERT INTO intermediate_conf_ranking (conf_id, title, acronym, conf_rank, primary_for)
        SELECT id, title, acronym, conf_rank, primaryFoR
        FROM starting_conf_ranking
        WHERE id IS NOT NULL;
    ''')

def create_intermediate_mag_articles(cursor):
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sma_id ON starting_mag_articles (id);')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intermediate_mag_articles (
            article_id INT, author_id INT, title VARCHAR(255), year INT, journal VARCHAR(255),
            FOREIGN KEY (author_id) REFERENCES AUTHOR_LOOKUP(author_id)
        );
    ''')
    cursor.execute('''
        INSERT INTO intermediate_mag_articles (article_id, author_id, title, year, journal)
        SELECT iaa.article_id, au.author_id, s.title, s.year, s.journal
        FROM intermediate_article_author iaa
        JOIN AUTHOR_LOOKUP au ON iaa.author_name = au.author_name
        JOIN starting_mag_articles s ON iaa.article_id = s.id
        WHERE iaa.article_id IS NOT NULL;
    ''')

def create_intermediate_mag_ranking(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intermediate_mag_ranking (
            mag_id INT, title VARCHAR(255), sjr_index DECIMAL(10,4), best_quartile VARCHAR(255),
            total_docs INT, total_docs_3y INT, total_refs INT,
            total_cites_3y INT, citable_docs_3y INT,
            cites_per_doc_2y DECIMAL(10,4), refs_per_doc DECIMAL(10,4),
            best_subject_area VARCHAR(255), publisher VARCHAR(255)
        );
    ''')
    cursor.execute('''
        INSERT INTO intermediate_mag_ranking (
            mag_id, title, sjr_index, best_quartile,
            total_docs, total_docs_3y, total_refs, total_cites_3y,
            citable_docs_3y, cites_per_doc_2y, refs_per_doc,
            best_subject_area, publisher)
        SELECT mag_rank, Title, SJR_index, Best_Quartile,
            Total_Docs, Total_Docs_three_y, Total_Refs, Total_Cites_three_y,
            Citable_Docs_three_y, Cites_or_Doc_two_y, Refs_or_Doc,
            Best_Subject_Area, Publisher
        FROM starting_mag_ranking
        WHERE mag_rank IS NOT NULL;
    ''')


####################
### FINAL TABLES ###
####################

def create_final_tables_schema(cursor):
    for table in ['ARTICLE_AUTHORS', 'CONF_ARTICLE_INFO', 'MAG_ARTICLE_INFO',
                  'CONF_RANKING', 'MAG_RANKING', 'ARTICLES',
                  'AUTHOR_LOOKUP', 'FOR_LOOKUP', 'BEST_SUBJECT_AREA_LOOKUP']:
        cursor.execute(f'DROP TABLE IF EXISTS {table};')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS FOR_LOOKUP (
            for_code INT PRIMARY KEY, for_name VARCHAR(255)
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS BEST_SUBJECT_AREA_LOOKUP (
            best_subject_area_id INT PRIMARY KEY, best_subject_area_name VARCHAR(255)
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS AUTHOR_LOOKUP (
            author_id INT PRIMARY KEY, author_name VARCHAR(255)
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ARTICLES (
            article_id INT PRIMARY KEY, title VARCHAR(255)
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS CONF_RANKING (
            conf_id INT PRIMARY KEY, title VARCHAR(255), acronym VARCHAR(255),
            conf_rank VARCHAR(255), primary_for INT,
            CONSTRAINT fk_conf_ranking_for FOREIGN KEY (primary_for) REFERENCES FOR_LOOKUP(for_code)
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MAG_RANKING (
            mag_id INT PRIMARY KEY, title VARCHAR(255), mag_rank DECIMAL(10,4),
            best_quartile VARCHAR(2), total_docs INT,
            total_docs_3y INT, total_refs INT,
            total_cites_3y INT, citable_docs_3y INT,
            cites_per_doc_2y DECIMAL(10,4), refs_per_doc DECIMAL(10,4),
            best_subject_area_id INT, publisher VARCHAR(255),
            CONSTRAINT fk_mag_ranking_bsa FOREIGN KEY (best_subject_area_id) REFERENCES BEST_SUBJECT_AREA_LOOKUP(best_subject_area_id)
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS CONF_ARTICLE_INFO (
            article_id INT PRIMARY KEY, conf_id INT, year INT,
            CONSTRAINT fk_cai_article FOREIGN KEY (article_id) REFERENCES ARTICLES(article_id),
            CONSTRAINT fk_cai_conf FOREIGN KEY (conf_id) REFERENCES CONF_RANKING(conf_id)
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MAG_ARTICLE_INFO (
            article_id INT PRIMARY KEY, mag_id INT, year INT,
            CONSTRAINT fk_mai_article FOREIGN KEY (article_id) REFERENCES ARTICLES(article_id),
            CONSTRAINT fk_mai_mag FOREIGN KEY (mag_id) REFERENCES MAG_RANKING(mag_id)
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ARTICLE_AUTHORS (
            article_id INT, author_id INT,
            PRIMARY KEY (article_id, author_id),
            CONSTRAINT fk_aa_article FOREIGN KEY (article_id) REFERENCES ARTICLES(article_id),
            CONSTRAINT fk_aa_author FOREIGN KEY (author_id) REFERENCES AUTHOR_LOOKUP(author_id)
        );''')


def create_final_articles(cursor):
    cursor.execute('''
        INSERT INTO ARTICLES (article_id, title)
        SELECT article_id, CASE WHEN TRIM(COALESCE(title, '')) = '' THEN 'no_title' ELSE title END
        FROM intermediate_conf_articles
        UNION
        SELECT article_id, CASE WHEN TRIM(COALESCE(title, '')) = '' THEN 'no_title' ELSE title END
        FROM intermediate_mag_articles;
    ''')

def create_final_conf_ranking(cursor, c_ranking):
    cursor.execute('DROP TABLE IF EXISTS tmp_conf_categories;')
    cursor.execute('''
        CREATE TEMPORARY TABLE tmp_conf_categories (
            conf_id INT, title VARCHAR(255),
            INDEX (conf_id)
        );
    ''')
    seen = set()
    records = []
    for row in c_ranking.itertuples(index=False):
        if int(row.c_id) not in seen:
            seen.add(int(row.c_id))
            records.append((int(row.c_id), str(row.c_title) if row.c_title else None))
    _executemany_batched(cursor,
        'INSERT INTO tmp_conf_categories (conf_id, title) VALUES (%s, %s)',
        records
    )

    cursor.execute('''
        INSERT INTO CONF_RANKING (conf_id, title, acronym, conf_rank, primary_for)
        SELECT t.conf_id, t.title, MAX(r.acronym),
               COALESCE(MAX(r.conf_rank), 'unranked'),
               (SELECT for_code FROM FOR_LOOKUP WHERE for_code = MAX(r.primary_for))
        FROM tmp_conf_categories t
        LEFT JOIN intermediate_conf_ranking r ON t.conf_id = r.conf_id
        GROUP BY t.conf_id, t.title
        ORDER BY t.conf_id ASC;
    ''')
    cursor.execute('DROP TABLE IF EXISTS tmp_conf_categories;')

def create_final_mag_ranking(cursor, m_ranking):
    cursor.execute('DROP TABLE IF EXISTS tmp_mag_categories;')
    cursor.execute('''
        CREATE TEMPORARY TABLE tmp_mag_categories (
            mag_id INT, title VARCHAR(255),
            INDEX (mag_id)
        );
    ''')
    seen = set()
    records = []
    for row in m_ranking.itertuples(index=False):
        if int(row.c_id) not in seen:
            seen.add(int(row.c_id))
            records.append((int(row.c_id), str(row.c_title) if row.c_title else None))
    _executemany_batched(cursor,
        'INSERT INTO tmp_mag_categories (mag_id, title) VALUES (%s, %s)',
        records
    )

    cursor.execute('''
        INSERT INTO MAG_RANKING (
            mag_id, title, mag_rank, best_quartile,
            total_docs, total_docs_3y, total_refs, total_cites_3y,
            citable_docs_3y, cites_per_doc_2y, refs_per_doc,
            best_subject_area_id, publisher)
        SELECT t.mag_id, t.title, MAX(r.sjr_index),
            CASE WHEN MAX(r.best_quartile) IN ('Q1','Q2','Q3','Q4') THEN MAX(r.best_quartile) ELSE NULL END,
            MAX(r.total_docs), MAX(r.total_docs_3y), MAX(r.total_refs),
            MAX(r.total_cites_3y), MAX(r.citable_docs_3y),
            MAX(r.cites_per_doc_2y), MAX(r.refs_per_doc),
            (SELECT s.best_subject_area_id FROM BEST_SUBJECT_AREA_LOOKUP s
             WHERE s.best_subject_area_name = TRIM(REPLACE(REPLACE(REPLACE(REPLACE(
                 MAX(r.best_subject_area), '[', ''), ']', ''), '"', ''), "'", ''))
             LIMIT 1),
            MAX(r.publisher)
        FROM tmp_mag_categories t
        LEFT JOIN intermediate_mag_ranking r ON t.mag_id = r.mag_id
        GROUP BY t.mag_id, t.title
        ORDER BY t.mag_id ASC;
    ''')
    cursor.execute('DROP TABLE IF EXISTS tmp_mag_categories;')

def create_final_conf_articles(cursor, c_articles):
    cursor.execute('DROP TABLE IF EXISTS tmp_conf_id_map;')
    cursor.execute('''
        CREATE TEMPORARY TABLE tmp_conf_id_map (
            article_id INT, conf_id INT,
            INDEX (article_id)
        );
    ''')
    records = [
        (int(row.a_id), int(row.c_id))
        for row in c_articles.dropna(subset=['c_id']).itertuples(index=False)
    ]
    _executemany_batched(cursor,
        'INSERT INTO tmp_conf_id_map (article_id, conf_id) VALUES (%s, %s)',
        records
    )

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ica_article_id ON intermediate_conf_articles (article_id);')
    cursor.execute('''
        INSERT INTO CONF_ARTICLE_INFO (article_id, conf_id, year)
        SELECT DISTINCT a.article_id, m.conf_id, a.year
        FROM intermediate_conf_articles a
        JOIN tmp_conf_id_map m ON a.article_id = m.article_id
        WHERE a.article_id IS NOT NULL
        ORDER BY a.article_id ASC;
    ''')
    cursor.execute('DROP TABLE IF EXISTS tmp_conf_id_map;')

def create_final_mag_articles(cursor, m_articles):
    cursor.execute('DROP TABLE IF EXISTS tmp_mag_id_map;')
    cursor.execute('''
        CREATE TEMPORARY TABLE tmp_mag_id_map (
            article_id INT, mag_id INT,
            INDEX (article_id)
        );
    ''')
    records = [
        (int(row.a_id), int(row.c_id))
        for row in m_articles.dropna(subset=['c_id']).itertuples(index=False)
    ]
    _executemany_batched(cursor,
        'INSERT INTO tmp_mag_id_map (article_id, mag_id) VALUES (%s, %s)',
        records
    )

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ima_article_id ON intermediate_mag_articles (article_id);')
    cursor.execute('''
        INSERT INTO MAG_ARTICLE_INFO (article_id, mag_id, year)
        SELECT DISTINCT a.article_id, m.mag_id, a.year
        FROM intermediate_mag_articles a
        JOIN tmp_mag_id_map m ON a.article_id = m.article_id
        WHERE a.article_id IS NOT NULL
        ORDER BY a.article_id ASC;
    ''')
    cursor.execute('DROP TABLE IF EXISTS tmp_mag_id_map;')

def create_final_article_authors(cursor, conn):
    cursor.execute('''
        SELECT iaa.author_name, al.author_id
        FROM intermediate_article_author iaa
        JOIN AUTHOR_LOOKUP al ON al.author_name = iaa.author_name
    ''')
    name_to_id = {name: aid for name, aid in cursor.fetchall()}

    write_conn = _db_connection()
    write_cursor = write_conn.cursor()
    write_cursor.execute('SET SESSION wait_timeout = 28800;')
    write_cursor.execute('SET SESSION net_write_timeout = 3600;')

    cursor.execute('SELECT article_id, author_name FROM intermediate_article_author')
    chunk_size = 100000
    while True:
        rows = cursor.fetchmany(chunk_size)
        if not rows:
            break
        records = list({(aid, name_to_id[name]) for aid, name in rows if name in name_to_id})
        write_cursor.executemany(
            'INSERT INTO ARTICLE_AUTHORS (article_id, author_id) VALUES (%s, %s)',
            records
        )

    write_conn.commit()
    write_cursor.close()
    write_conn.close()
    conn.commit()


####################
### DROP STAGING ###
####################

def drop_staging_tables(cursor):
    for table in [
        'intermediate_article_author',
        'intermediate_conf_articles',
        'intermediate_conf_ranking',
        'intermediate_mag_articles',
        'intermediate_mag_ranking',
        'starting_conf_articles',
        'starting_conf_ranking',
        'starting_mag_articles',
        'starting_mag_ranking',
    ]:
        cursor.execute(f'DROP TABLE IF EXISTS {table};')


############
### MAIN ###
############

def _db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def run():
    conn = mysql.connector.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        allow_local_infile=True,
    )
    cursor = conn.cursor()

    try:
        start = time.time()
        print('Creating database...')
        cursor.execute('SET GLOBAL local_infile = 1;')
        cursor.execute('SET SESSION wait_timeout = 3600;')
        cursor.execute('SET SESSION interactive_timeout = 3600;')
        cursor.execute('SET SESSION net_read_timeout = 3600;')
        cursor.execute('SET SESSION net_write_timeout = 3600;')
        cursor.execute(f'DROP DATABASE IF EXISTS {DB_NAME};')
        cursor.execute(f'CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
        cursor.execute(f'USE {DB_NAME};')

        create_final_tables_schema(cursor)

        print('Loading starting tables...')
        create_starting_conf_articles(cursor)
        print('  [1/4] Conference articles loaded')
        create_starting_conf_ranking(cursor)
        print('  [2/4] Conference ranking loaded')
        create_starting_mag_articles(cursor)
        print('  [3/4] Magazine articles loaded')
        create_starting_mag_ranking(cursor)
        print('  [4/4] Magazine ranking loaded')

        print('Processing authors...')
        create_intermediate_article_author(cursor)
        print('  [1/2] Intermediate article-author table done')
        create_author_lookup(cursor)
        print('  [2/2] Author lookup done')

        print('Creating intermediate tables...')
        create_intermediate_conf_articles(cursor)
        print('  [1/4] Conference articles done')
        create_intermediate_conf_ranking(cursor)
        print('  [2/4] Conference ranking done')
        create_intermediate_mag_articles(cursor)
        print('  [3/4] Magazine articles done')
        create_intermediate_mag_ranking(cursor)
        print('  [4/4] Magazine ranking done')

        print('Running fuzzy matching...')
        m_articles, m_ranking, c_articles, c_ranking = fuzzy_matching.run(cursor)

        print('Creating final tables...')
        create_for_lookup(cursor)
        print('  [1/8] FoR lookup done')
        create_subject_area_lookup(cursor)
        print('  [2/8] Subject area lookup done')
        create_final_articles(cursor)
        print('  [3/8] Articles done')
        create_final_conf_ranking(cursor, c_ranking)
        print('  [4/8] Conference ranking done')
        create_final_mag_ranking(cursor, m_ranking)
        print('  [5/8] Magazine ranking done')
        create_final_conf_articles(cursor, c_articles)
        print('  [6/8] Conference article info done')
        create_final_mag_articles(cursor, m_articles)
        print('  [7/8] Magazine article info done')
        create_final_article_authors(cursor, conn)
        print('  [8/8] Article authors done')

        conn.commit()

        if RUN_TESTS:
            print('Running tests...')
            test_tables.run(cursor)

        if DROP_STAGING_TABLES:
            print('Dropping staging tables...')
            drop_staging_tables(cursor)

        if EXPORT_FINAL_TABLES:
            print('Exporting final tables...')
            export_tables.run(cursor)

        conn.commit()

        if CREATE_BACKUP:
            print('Creating backup...')
            backup.run()

        elapsed = time.time() - start
        print(f'\nSetup complete ! ({int(elapsed // 60)}m {elapsed % 60:.1f}s)')

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    run()
