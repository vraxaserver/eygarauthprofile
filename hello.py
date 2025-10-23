import psycopg2

try:
    conn = psycopg2.connect(
        host="eygardatabase-instance.cj480emqyx9y.me-central-1.rds.amazonaws.com",
        dbname="dev_eygar_listing_property",
        user="postgres",
        password="UV7bDpcLAaazRFsqVf16"
    )
    print("Connected successfully")
except Exception as error:
    print(error)
