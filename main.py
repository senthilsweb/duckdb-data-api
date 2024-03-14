from fastapi import FastAPI, Depends, HTTPException, Request, Query
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Dict, Any  # Make sure to include Dict here
import math
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from datetime import datetime
import os  # Import the os module
from dotenv import load_dotenv  # Import the load_dotenv function


# Load environment variables from .env file
load_dotenv()

DATABASE_URL = f"duckdb:///md:eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uIjoic2VudGhpbC5rYXJ1cHBhaWFoLmhpdGFjaGl2YW50YXJhLmNvbSIsImVtYWlsIjoic2VudGhpbC5rYXJ1cHBhaWFoQGhpdGFjaGl2YW50YXJhLmNvbSIsInVzZXJJZCI6ImExMWM3ZGQ1LWI0MDQtNGZmMi05MWNlLWQwOWZjZjJjNjFlMSIsImlhdCI6MTcwOTMyMTU3OSwiZXhwIjoxNzQwODc5MTc5fQ.yndoJ4nGA5PgCVB_2aveJSeJ0ByOotkH6RttRhgoK1w@my_db"

print(f"DATABASE_URL = {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

SCHEMA_NAME = 'automation'

@app.get("/")
async def root():
    return {"message": "Hello from FastAPI!"}

@app.get("/health")
async def root():
    return {"message": "I am doing great!"}

@app.get("/debug/connection")
def debug_connection(db: Session = Depends(get_db)):
    try:
        # Attempt a simple query to test the connection
        # This query can be anything that is guaranteed to succeed in your DB environment
        print(f"Checking DuckDB Connection")
        result = db.execute(text("SELECT 1"))
        print(f"Checked DuckDB Connection")
        # If the query succeeds, return a success message
        return {"status": "success", "message": "Database connection established successfully."}
    except Exception as e:
        # If an error occurs, return an error message and details
        return {"status": "error", "message": str(e)}
    
@app.get("/tables")
def list_tables(db: Session = Depends(get_db)) -> List[str]:
    # Assuming DuckDB supports this or similar command to list tables
    db.execute(text("USE automation"))
    result = db.execute(text("SHOW TABLES"))
    # The first column in each row contains the table name
    tables = [row[0] for row in result]
    return tables

# Improved utility function with more detailed logging
def prepare_where_clauses(request: Request):
    print("Inside prepare_where_clauses")
    where_clauses = []
    params = {}
    for key, value in request.query_params.items():
        original_key = key  # Keep the original key to handle special cases
        print(f"Processing query param: {key} = {value}")
        if key not in ["select", "limit", "offset", "order"]:
            operator = "="  # Default operator
            
            # Modify key based on the operator
            if key.endswith(".eq"):
                operator = "="
                key = key[:-3]  # Remove the operation part to get the actual column name
            elif key.endswith(".gt"):
                operator = ">"
                key = key[:-3]
            elif key.endswith(".gte"):
                operator = ">="
                key = key[:-4]
            elif key.endswith(".lt"):
                operator = "<"
                key = key[:-3]
            elif key.endswith(".lte"):
                operator = "<="
                key = key[:-4]
            elif key.endswith(".neq"):
                operator = "<>"
                key = key[:-4]
            elif key.endswith(".like"):
                operator = "ILIKE"  # Use "LIKE" for case-sensitive databases
                key = key[:-5]

            # For the parameter dictionary, use the original key without the operator suffix
            # This corrects the issue of parameter mismatch
            params[key] = value
            
            where_clause = f"{key} {operator} :{key}"
            where_clauses.append(where_clause)
            print(f"Added where clause: {where_clause}")

    return " AND ".join(where_clauses), params

# This utility function will convert datetime objects to strings
def default_converter(o):
    if isinstance(o, datetime):
        return o.__str__()
    
@app.get("/data/{table_name}", response_model=List[Dict[str, Any]])
def read_table_data(table_name: str, 
                    request: Request,
                    select: str = Query("*"),
                    order: str = Query(None),
                    skip: int = Query(0, alias="offset"),
                    limit: int = Query(100) ,
                    db: Session = Depends(get_db)):
    # Ensure the table name is valid to prevent SQL injection
    print(f"Received request for table: {table_name}")



    tables = list_tables(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
        # Start building the base query
    base_query = f"SELECT {select} FROM {table_name}"
    print("Base Query:", base_query)

    # Prepare WHERE clauses and parameters
    where_clauses, params = prepare_where_clauses(request)
    if where_clauses:
        base_query += f" WHERE {where_clauses}"

    print("Base Query with WHERE:", base_query)
    print("Parameters:", params)


    # Sorting
    if order:
        base_query += f" ORDER BY {order}"
        print("Added ORDER BY clause:", order)

    # Pagination logic
    if skip or limit:
        base_query += " LIMIT :limit OFFSET :offset"
        params.update({"limit": limit, "offset": skip})
        print(f"Added pagination with limit {limit} and offset {skip}")

    print("Final Query:", base_query)
    print("Final Parameters:", params)

    # Execute the query with exception handling
    try:
        result_proxy = db.execute(text(base_query), params)
        results = result_proxy.fetchall()
        print(f"Query successful, fetched {len(results)} records.")
    except Exception as e:
        print(f"Query execution failed: {e}")
        raise e
    
    # Get total count for pagination
    try:
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        if where_clauses:
            count_query += f" WHERE {where_clauses}"
        print("Count Query:", count_query)
        total_count = db.execute(text(count_query), params).scalar()
        print("Count Query successful, total count:", total_count)
    except Exception as e:
        print(f"Count query execution failed: {e}")
        raise e

    # Qualify the table name with the schema
    #qualified_table_name = f"{table_name}"
    #query = text(f"SELECT * FROM {qualified_table_name} limit 10;")
    #print(query)
    #result_proxy = db.execute(query)
    #results = result_proxy.fetchall()

    #column_names = result_proxy.keys()
    #data = [dict(zip(column_names, row)) for row in results]

    #return data


   # Prepare response
    try:
        column_names = result_proxy.keys()
        # Convert all datetime objects to strings (in ISO 8601 format)
        entities = [
            {key: (value.isoformat() if isinstance(value, datetime) else value) for key, value in dict(zip(column_names, row)).items()}
            for row in results
        ]

        page_number = math.ceil(skip / limit) + 1
        total_pages = math.ceil(total_count / limit)
        response_data = {
            "total_rows": total_count,
            "total_pages": total_pages,
            "limit": limit,
            "offset": skip,
            "current_page": page_number,
            "data": entities
        }
        print("Response prepared successfully.")
    except Exception as e:
        print(f"Error preparing response: {e}")
        raise e

    return JSONResponse(content=response_data)