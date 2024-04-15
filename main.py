"""
File Name: main.py
Author(s): Sernthilnathan Karuppaiah and ChatGPT4 :-)
Date: 14-Mar-2024
Description: This FastAPI application serves as a data proxy to DuckDB, offering endpoints for basic database
             operations such as listing tables, reading table data with optional filtering, sorting, and pagination,
             and a debug endpoint to check database connectivity. It is designed for dynamic usage, following
             the ActiveRecord design pattern akin to a Rails-type microORM, and utilizes SQLAlchemy for 
             database interaction.
"""

from fastapi import FastAPI, Depends, HTTPException, Request, Query, Path, Body
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlglot
from sqlglot import parse_one, exp
from sqlglot.optimizer import optimize
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from cache_middleware import CacheMiddleware
import os
from dotenv import load_dotenv
import math



# Initialize environment variables and set HOME for duckDB compatibility in serverless environments.
# Only load .env file if running locally and not in Vercel
if os.environ.get('VERCEL', None) != '1':
    # Clear all environment variables
    os.environ.clear()
    load_dotenv()

os.environ['HOME'] = '/tmp'
# Initialize environment variables and set HOME for duckDB compatibility in serverless environments.
# Only load .env file if running locally and not in Vercel
if os.environ.get('VERCEL', None) != '1':
    load_dotenv()

# Configuration variables
DATABASE_URL = os.getenv("DUCKDB_DATABASE_URL", default="duckdb:///tickit.duckdb")
print(f"DATABASE_URL = [{DATABASE_URL}]")
SCHEMA_NAME = os.getenv("DUCKDB_SCHEMA_NAME", default="main")
print(f"SCHEMA_NAME = [{SCHEMA_NAME}]")
BLACKLIST_KEYWORDS = [keyword for keyword in os.getenv("QUERY_BLACKLIST", "").split(",") if keyword]


# Database engine setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()
app.add_middleware(CacheMiddleware)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/")
async def root():
    """Root endpoint returning welcome message."""
    return {"message": "Welcome to DuckDB Data Proxy!"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"message": "I am doing great!"}

@app.get("/debug/connection")
def debug_connection(db: Session = Depends(get_db)):
    """
    Debug endpoint to test database connection.
    
    Attempts a simple query to verify database connectivity.
    """
    try:
        result = db.execute(text("SELECT 1"))
        return {"status": "success", "message": "Database connection established successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/metadata/tables")
def list_tables(db: Session = Depends(get_db)) -> List[str]:
    """
    Endpoint to list all tables in the database for specified schemas.
    """
    if SCHEMA_NAME:
        query = f"SELECT table_name FROM information_schema.tables WHERE table_schema IN ('{SCHEMA_NAME}')"
    else:
        # If no schema names are provided, query tables without filtering by schema
        query = "SELECT table_name FROM information_schema.tables"
    print(f"query = [{query}]")
    result = db.execute(text(query))
    tables = [row[0] for row in result]
    return tables

def prepare_where_clauses(request: Request):
    """
    Prepares WHERE clauses for SQL queries based on request query parameters.
    
    Supports various operators like .eq, .gt, .gte, .lt, .lte, .neq, and .like.
    """
    where_clauses = []
    params = {}
    for key, value in request.query_params.items():
        if key not in ["select", "limit", "offset", "order"]:
            operator = "="  # Default operator
            if key.endswith(".eq"):
                operator = "="
                key = key[:-3]
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
                operator = "ILIKE"
                key = key[:-5]
            where_clauses.append(f"{key} {operator} :{key}")
            params[key] = value
    return " AND ".join(where_clauses), params

@app.get("/{table_name}", response_model=List[Dict[str, Any]])
def get_entities(table_name: str, request: Request, select: str = Query("*"),
                    order: str = Query(None), skip: int = Query(0, alias="offset"),
                    limit: int = Query(100), db: Session = Depends(get_db)):
    """
    Endpoint to read data from a specified table with optional filtering, sorting, and pagination.
    
    Validates table name against existing tables to prevent SQL injection.
    """
    # Validate table name
    if table_name not in list_tables(db):
        raise HTTPException(status_code=404, detail="Table not found")
    
    # Construct query with optional WHERE, ORDER BY, and pagination
    base_query = f"SELECT {select} FROM  {SCHEMA_NAME}.{table_name}"
    where_clauses, params = prepare_where_clauses(request)
    if where_clauses:
        base_query += f" WHERE {where_clauses}"
        count_query = f"SELECT COUNT(*) FROM {SCHEMA_NAME}.{table_name} WHERE {where_clauses}"
            
    else:
        count_query = f"SELECT COUNT(*) FROM {SCHEMA_NAME}.{table_name}"

    if order:
        base_query += f" ORDER BY {order}"
    base_query += " LIMIT :limit OFFSET :offset"
    print(f"base_query = {base_query}")
    params.update({"limit": limit, "offset": skip})
    print(f"params = {params}")
    # Execute query and handle results
    try:
        result_proxy = db.execute(text(base_query), params)
        results = result_proxy.fetchall()
        # Use params for count query as well to respect WHERE conditions
        total_count = db.execute(text(count_query), params).scalar()
        page_number = math.ceil(skip / limit) + 1
        total_pages = math.ceil(total_count / limit)
        response_data = {
            "total_rows": total_count,
            "total_pages": total_pages,
            "limit": limit,
            "offset": skip,
            "current_page": page_number,
            "data": [{key: (value.isoformat() if isinstance(value, datetime) else value) 
                      for key, value in dict(zip(result_proxy.keys(), row)).items()} for row in results]
        }
        return JSONResponse(content=response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/{table_name}/{id}", response_model=Dict[str, Any])
def get_entity(table_name: str, id: int = Path(..., description="The ID of the entity to retrieve"), 
               db: Session = Depends(get_db)):
    """
    Dynamically fetches a single entity by its ID from a specified table.
    
    Parameters:
    - table_name: str - The name of the table from which to retrieve the entity.
    - id: int - The unique identifier of the entity to retrieve.

    Returns a single entity matching the given ID from the specified table, with datetime fields properly serialized.
    """
    # Validate table name
    if table_name not in list_tables(db):
        raise HTTPException(status_code=404, detail="Table not found")
    
    query = text(f"SELECT * FROM {SCHEMA_NAME}.{table_name} WHERE id = :id")
    result = db.execute(query, {"id": id}).fetchone()
    
    if result is None:
        raise HTTPException(status_code=404, detail=f"Record [{id}] not found in [{SCHEMA_NAME}.{table_name}]")

    # Convert the RowProxy object to a dictionary
    result_dict = {key: value for key, value in result._mapping.items()}

    # Serialize using jsonable_encoder to handle datetime and other complex types
    return jsonable_encoder(result_dict)

@app.delete("/{table_name}/{id}", response_model=Dict[str, Any])
def delete_entity(table_name: str, id: int = Path(..., description="The ID of the entity to delete"), 
                  db: Session = Depends(get_db)):
    """
    Deletes a single entity by its ID from a specified table.
    """
   # Validate table name
    if table_name not in list_tables(db):
        raise HTTPException(status_code=404, detail="Table not found")
    
    # Check if the entity exists
    exists_query = text(f"SELECT EXISTS(SELECT 1 FROM {SCHEMA_NAME}.{table_name} WHERE id = :id)")
    exists = db.execute(exists_query, {"id": id}).scalar()
    
    if not exists:
        raise HTTPException(status_code=404, detail=f"Record [{id}] not found in [{SCHEMA_NAME}.{table_name}]")

    # Delete the entity
    delete_query = text(f"DELETE FROM {SCHEMA_NAME}.{table_name} WHERE id = :id")
    db.execute(delete_query, {"id": id})
    db.commit()

    return {"message": f"Record [{id}] deleted successfully from [{SCHEMA_NAME}.{table_name}]"}

@app.post("/{table_name}", response_model=Dict[str, Any])
def create_entity(table_name: str, entity_data: Dict[str, Any] = Body(...), 
                  db: Session = Depends(get_db)):
    """
    Creates a new entity in the specified table with the provided data.
    """
    # Validate table name
    if table_name not in list_tables(db):
        raise HTTPException(status_code=404, detail="Table not found")

    # Constructing SQL INSERT statement dynamically based on entity_data
    columns = ', '.join(entity_data.keys())
    values = ', '.join([f":{key}" for key in entity_data.keys()])
    insert_query = text(f"INSERT INTO {SCHEMA_NAME}.{table_name} ({columns}) VALUES ({values}) RETURNING *")
    
    # Execute the query and fetch the newly created entity
    result = db.execute(insert_query, entity_data).fetchone()
    db.commit()
    
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to create record")
    
    # Convert the RowProxy object to a dictionary
    result_dict = {key: value for key, value in result._mapping.items()}

    # Serialize using jsonable_encoder to handle datetime and other complex types
    return jsonable_encoder(result_dict)

@app.patch("/{table_name}/{id}", response_model=Dict[str, Any])
def update_entity(table_name: str, id: int, update_data: Dict[str, Any] = Body(...), 
                  db: Session = Depends(get_db)):
    """
    Updates an existing entity in the specified table with the provided data.
    """
    # Validate table name
    if table_name not in list_tables(db):
        raise HTTPException(status_code=404, detail="Table not found")

    # First, check if the entity exists
    exists_query = text(f"SELECT EXISTS(SELECT 1 FROM {SCHEMA_NAME}.{table_name} WHERE id = :id)")
    exists = db.execute(exists_query, {"id": id}).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Constructing SQL UPDATE statement dynamically based on update_data
    set_clauses = ', '.join([f"{key} = :{key}" for key in update_data.keys()])
    update_query = text(f"UPDATE {SCHEMA_NAME}.{table_name} SET {set_clauses} WHERE id = :id RETURNING *")
    
    # Execute the query and fetch the updated entity
    result = db.execute(update_query, {**update_data, "id": id}).fetchone()
    db.commit()
    
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to update record [{id}] in [{table_name}]")

    # Convert the result row to a dict to ensure compatibility with FastAPI's response_model
    updated_entity = {column: value for column, value in result._mapping.items()}
    return updated_entity

@app.put("/{table_name}/{id}", response_model=Dict[str, Any])
def replace_entity(table_name: str, id: int, new_data: Dict[str, Any] = Body(...), 
                   db: Session = Depends(get_db)):
  
    if table_name not in list_tables(db):
        raise HTTPException(status_code=404, detail="Table not found")

    # First, check if the entity exists
    exists_query = text(f"SELECT EXISTS(SELECT 1 FROM {SCHEMA_NAME}.{table_name} WHERE id = :id)")
    exists = db.execute(exists_query, {"id": id}).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Table not found")

    # Assuming all fields must be provided for a PUT operation, construct a dynamic UPDATE statement
    set_clauses = ', '.join([f"{key} = :{key}" for key in new_data.keys()])
    update_query = text(f"UPDATE {SCHEMA_NAME}.{table_name} SET {set_clauses} WHERE id = :id RETURNING *")
    
    # Execute the query and fetch the updated entity
    result = db.execute(update_query, {**new_data, "id": id}).fetchone()
    db.commit()
    
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to replace record [{id}] in [{table_name}]")

    # Convert the result row to a dict to ensure compatibility with FastAPI's response_model
    replaced_entity = {column: value for column, value in result._mapping.items()}
    return replaced_entity

def is_query_blacklisted(query: str) -> bool:
    # Check if BLACKLIST_KEYWORDS is actually empty or contains only an empty string
    if not BLACKLIST_KEYWORDS or BLACKLIST_KEYWORDS == ['']:
        return False

    query_lower = query.lower()
    for keyword in BLACKLIST_KEYWORDS:
        # Skip empty strings which might be a result of splitting an empty environment variable
        if keyword and keyword in query_lower:
            return True
    return False

@app.post("/execute/sql")
def execute_custom_query(query: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """
    Executes a custom SQL query, which can be a SELECT statement or a DDL statement.
    Checks against a blacklist for prohibited keywords.

    Parameters:
    - query: str - The SQL query to execute.

    If the query is a SELECT statement, returns the fetched data.
    For DDL statements, returns a confirmation message.
    """
    #query = query.strip().lower()
    query = query.strip()
    if is_query_blacklisted(query):
        raise HTTPException(status_code=403, detail="The query contains prohibited keywords.")

    if query.startswith("select") or query.startswith("SELECT"):
        # It's a select query
        return execute_select_query(query, db)
    else:
        # It's a DDL query
        return execute_ddl_query(query, db)

def execute_select_query(query: str, db: Session):

    print(query)

    try:
        result_proxy = db.execute(text(query))
        results = result_proxy.mappings().all()  # Convert to list of dictionaries
        # Serialize the results using jsonable_encoder to handle special data types like datetime
        json_compatible_data = jsonable_encoder(results)
        return JSONResponse(content={"data": json_compatible_data, "total_rows": len(results)})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def execute_ddl_query(query: str, db: Session):
    try:
        db.execute(text(query))
        db.commit()  # Make sure to commit the transaction for DDL operations
        return JSONResponse(content={"message": "Query executed successfully"})
    except Exception as e:
        db.rollback()  # Rollback the transaction in case of failure
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/sqlglot/transpile")
async def sqlglot_transpile_sql(request: Request):
    try:
        # Parse JSON dynamically without a Pydantic model
        body = await request.json()
        sql = body.get("sql")
        transpile_to = body.get("transpile_to")

        if not sql:
            raise ValueError("No SQL provided for transpilation.")
        if not transpile_to:
            raise ValueError("No target language provided for transpilation.")

        # Transpile the provided SQL to the specified target language
        transpiled_sql = sqlglot.transpile(sql, write=transpile_to, identify=True, pretty=True)[0]
        return {"result_sql": transpiled_sql}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while transpiling: {e}")

@app.post("/sqlglot/prettify")
async def sqlglot_prettify_sql(request: Request):
    try:
        # Parse JSON dynamically without a Pydantic model
        body = await request.json()
        sql = body.get("sql")

        if not sql:
            raise ValueError("No SQL provided for prettify.")

        # Transpile the provided SQL to the specified target language
        prettified_sql = sqlglot.optimizer.optimize(sql).sql(pretty=True)
        return {"result_sql": prettified_sql}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while prettify: {e}")
    
@app.post("/sqlglot/extract/column")
async def sqlglot_extract_columns(request: Request):
    try:
        body = await request.json()
        sql = body.get("sql")

        if not sql:
            raise ValueError("No SQL provided.")

        parsed_sql = parse_one(sql)

        # Extract columns
        columns = [column.alias_or_name for column in parsed_sql.find_all(exp.Column)]

        return {"data": columns}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while extracting columns: {e}")

@app.post("/sqlglot/extract/table")
async def sqlglot_extract_tables(request: Request):
    try:
        body = await request.json()
        sql = body.get("sql")

        if not sql:
            raise ValueError("No SQL provided.")

        parsed_sql = parse_one(sql)

        # Extract tables
        tables = [table.name for table in parsed_sql.find_all(exp.Table)]

        return {"data": tables}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while extracting tables: {e}")

@app.post("/sqlglot/extract/projection")
async def sqlglot_extract_projections(request: Request):
    try:
        body = await request.json()
        sql = body.get("sql")

        if not sql:
            raise ValueError("No SQL provided.")

        parsed_sql = parse_one(sql)

        # Extract projections
        projections = []
        for select in parsed_sql.find_all(exp.Select):
            projections.extend([projection.alias_or_name for projection in select.expressions])

        return {"data": projections}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while extracting projections: {e}")