"""
File Name: main.py
Author: Sernthilnathan Karuppaiah
Date: 14-Mar-2024
Description: This FastAPI application serves as a data proxy to DuckDB, offering endpoints for basic database
             operations such as listing tables, reading table data with optional filtering, sorting, and pagination,
             and a debug endpoint to check database connectivity. It is designed for dynamic usage, following
             the ActiveRecord design pattern akin to a Rails-type microORM, and utilizes SQLAlchemy for 
             database interaction.
"""

from fastapi import FastAPI, Depends, HTTPException, Request, Query, Path, Body
from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Dict, Any
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from datetime import datetime
import os
from dotenv import load_dotenv
import math

# Initialize environment variables and set HOME for duckDB compatibility in serverless environments.
load_dotenv()
os.environ['HOME'] = '/tmp'

# Configuration variables
DATABASE_URL = os.getenv("DUCKDB_DATABASE_URL", default="duckdb:///..path..to..your..local..duckdb")
SCHEMA_NAME = os.getenv("DUCKDB_SCHEMA_NAME", default="")

# Database engine setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
    Endpoint to list all tables in the database.
    
    Optionally uses a specified schema if provided.
    """
    if SCHEMA_NAME:
        db.execute(text(f"USE {SCHEMA_NAME}"))  # Work within a given Schema
    result = db.execute(text("SHOW TABLES"))
    tables = [row[0] for row in result]  # The first column in each row contains the table name
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
    tables = list_tables(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    # Construct query with optional WHERE, ORDER BY, and pagination
    base_query = f"SELECT {select} FROM {table_name}"
    where_clauses, params = prepare_where_clauses(request)
    if where_clauses:
        base_query += f" WHERE {where_clauses}"
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
        total_count = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
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
    tables = list_tables(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    query = text(f"SELECT * FROM {table_name} WHERE id = :id")
    result = db.execute(query, {"id": id}).fetchone()
    
    if result is None:
        raise HTTPException(status_code=404, detail=f"Record [{id}] not found in [{table_name}]")

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
    tables = list_tables(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")

    # Check if the entity exists
    exists_query = text(f"SELECT EXISTS(SELECT 1 FROM {table_name} WHERE id = :id)")
    exists = db.execute(exists_query, {"id": id}).scalar()
    
    if not exists:
        raise HTTPException(status_code=404, detail=f"Record [{id}] not found in [{table_name}]")

    # Delete the entity
    delete_query = text(f"DELETE FROM {table_name} WHERE id = :id")
    db.execute(delete_query, {"id": id})
    db.commit()

    return {"message": f"Record [{id}] deleted successfully from [{table_name}]"}

@app.post("/{table_name}", response_model=Dict[str, Any])
def create_entity(table_name: str, entity_data: Dict[str, Any] = Body(...), 
                  db: Session = Depends(get_db)):
    """
    Creates a new entity in the specified table with the provided data.
    """
    # Validate table name
    tables = list_tables(db)
    if table_name not in tables:
        raise HTTPException(status_code=404, detail="Table not found")

    # Constructing SQL INSERT statement dynamically based on entity_data
    columns = ', '.join(entity_data.keys())
    values = ', '.join([f":{key}" for key in entity_data.keys()])
    insert_query = text(f"INSERT INTO {table_name} ({columns}) VALUES ({values}) RETURNING *")
    
    # Execute the query and fetch the newly created entity
    result = db.execute(insert_query, entity_data).fetchone()
    db.commit()
    
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to create record")
    
    # Convert the RowProxy object to a dictionary
    result_dict = {key: value for key, value in result._mapping.items()}

    # Serialize using jsonable_encoder to handle datetime and other complex types
    return jsonable_encoder(result_dict)