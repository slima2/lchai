import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='oncology_xai', user='oncology', password='oncology_secret'
)
cur = conn.cursor()

cur.execute("SELECT id, external_id FROM patients WHERE external_id LIKE '%%69-7979%%'")
patients = cur.fetchall()
print('Patient:', patients)

if patients:
    pid = patients[0][0]
    cur.execute('SELECT id, patient_id, status, tags FROM cases WHERE patient_id = %s', (pid,))
    cases = cur.fetchall()
    print('Cases:', cases)
    if cases:
        cid = cases[0][0]
        cur.execute('SELECT id, case_id, format, storage_uri, size_bytes FROM images WHERE case_id = %s', (cid,))
        images = cur.fetchall()
        print('Images:', images)
        cur.execute('SELECT id, case_id, image_id, status FROM ml_jobs WHERE case_id = %s', (cid,))
        jobs = cur.fetchall()
        print('ML Jobs:', jobs)
        cur.execute('SELECT id, case_id, image_id, predominant_pattern FROM result_bundles WHERE case_id = %s', (cid,))
        bundles = cur.fetchall()
        print('Result Bundles:', bundles)
        if bundles:
            rbid = bundles[0][0]
            cur.execute('SELECT id, result_bundle_id, artifact_type, gene, uri FROM xai_artifacts WHERE result_bundle_id = %s', (rbid,))
            artifacts = cur.fetchall()
            print('XAI Artifacts:', artifacts)

conn.close()
