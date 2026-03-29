from sqlalchemy import create_engine, text
e = create_engine("postgresql://oncology:LchaiProd2026Secure@lchai-prod-postgres.cslc0oga28vr.us-east-1.rds.amazonaws.com:5432/oncology_xai?sslmode=prefer")
with e.connect() as c:
    r = c.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"))
    for row in r:
        print(row[0])
