INSERT INTO FOR_LOOKUP (for_code, for_name) VALUES
    (4601, 'for_name_1'),
    (4613, 'for_name_2');

INSERT INTO BEST_SUBJECT_AREA_LOOKUP (best_subject_area_id, best_subject_area_name) VALUES
    (1, 'subject_area_1'),
    (27, 'subject_area_2');

INSERT INTO AUTHOR_LOOKUP (author_id, author_name) VALUES
    (1, 'author1'),
    (2, 'author2'),
    (3, 'author3'),
    (4, 'author4');

INSERT INTO CONF_RANKING (conf_id, title, acronym, conf_rank, primary_for) VALUES
    (1, 'Conference 1', 'C1', 'A*', 4601),
    (2, 'Conference 2', 'C2', 'A', 4613),
    (3, 'Conference 3', 'C3', 'unranked', NULL);

INSERT INTO MAG_RANKING (mag_id, title, mag_rank, best_quartile, total_docs, total_docs_3y, total_refs, total_cites_3y, citable_docs_3y, cites_per_doc_2y, refs_per_doc, best_subject_area_id, publisher) VALUES
    (1, 'Journal 1', 1.5, 'Q1', 200, 180, 1500, 1200, 170, 8.50, 7.20, 1, 'publisher1'),
    (2, 'Journal 2', 2.0, 'Q2', 150, 120, 1200, 900, 110, 6.00, 5.50, 27, 'publisher2'),
    (3, 'Journal 3', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 1, 'publisher3');

INSERT INTO ARTICLES (article_id, title) VALUES
    (1, 'paper1'),
    (2, 'paper2'),
    (3, 'paper3'),
    (4, 'paper4'),
    (5, 'paper5'),
    (6, 'paper6'),
    (7, 'paper7'),
    (8, 'paper8'),
    (9, 'paper9'),
    (10, 'paper10');

INSERT INTO CONF_ARTICLE_INFO (article_id, conf_id, year) VALUES
    (1, 1, 2010),
    (2, 1, 2010),
    (3, 2, 2011),
    (4, 2, 2012),
    (5, 3, 2010);

INSERT INTO MAG_ARTICLE_INFO (article_id, mag_id, year) VALUES
    (6, 1, 2010),
    (7, 1, 2011),
    (8, 2, 2011),
    (9, 2, 2012),
    (10, 3, 2010);

INSERT INTO ARTICLE_AUTHORS (article_id, author_id) VALUES
    (1, 1),
    (1, 2),
    (2, 1),
    (3, 3),
    (4, 2),
    (4, 3),
    (5, 4),
    (6, 1),
    (6, 3),
    (7, 2),
    (8, 1),
    (9, 3),
    (10, 4);
