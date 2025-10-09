import psycopg2

try:
    conn = psycopg2.connect(
        host="eygardatabase-instance.cj480emqyx9y.me-central-1.rds.amazonaws.com",
        dbname="postgres",
        user="postgres",
        password="UV7bDpcLAaazRFsqVf16"
    )
    print("Connected successfully")
except Exception as error:
    print(error)

