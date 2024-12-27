# DuckDB Data API and Micro ORM

Ever wondered if MotherDuck offers a REST API? This project steps in to bridge that gap, enabling you to interact with DuckDB databases through a RESTful interface without writing a single line of backend code. Designed for deployment at the edge, it's a cost-effective solution for hobbyists and small projects.

The DuckDB Data API facilitates direct access to your DuckDB database, allowing for CRUD operations via HTTP.

## Motivation

- **Simplicity and Rapid Prototyping**: Offers a dynamic, RESTful interface to cater to various project requirements with minimal or no coding.
- **Adaptation to Serverless and Edge Computing**: Aims to provide a fitting database solution for applications operating at the internet's edge.
- **Leveraging DuckDB’s Speed**: While DuckDB excels in performance, integrating it directly into web applications posed challenges.
- **Filling the Gap Left by MotherDuck**: Although MotherDuck allows DuckDB to run serverlessly, it lacked a REST interface. This project aims to bridge that gap.
- **Inspiration from MongoDB's Atlas Data Proxy**: The convenience and developer-friendly nature of MongoDB's Atlas Data Proxy influenced the development of this project, promoting quick backend support for rapid prototyping.
- **Cost-Effective Deployment on Vercel**: The project prioritizes a deployment strategy that incurs minimal to no costs on platforms like Vercel.

## Design Goals

- **Adopting the ActiveRecord Pattern**: Mimics the ActiveRecord design pattern to offer an intuitive way of interacting with database records.
- **Automated CRUD Operations**: Streamlines Create, Read, Update, and Delete operations to save development time and effort.
- **Flexibility and Dynamic Nature**: Ensures the proxy can adapt to varying project needs without rigid constraints.
- **Single-File Implementation**: Strives for a lightweight solution, ideally encapsulated within a single file for ease of use and integration.


## Getting Started

### Python Environment Setup

1. **Create a Virtual Environment**: 

   ```bash
   python3 -m venv env
   source env/bin/activate
   pip install -r requirements.txt
   ```

2. Create a `.env` file at the root of your project to configure the environment settings:

```env
# .env file
DUCKDB_DATABASE_URL=duckdb:///tickit.duckdb
DUCKDB_SCHEMA_NAME=main
QUERY_BLACKLIST=DELETE,DROP,TRUNCATE,ALTER
```

- `DUCKDB_DATABASE_URL`: Specifies the connection URL to your local DuckDB database file or to a Motherduck connectionstring. Alternatively, you can set this to `:memory:` to use an in-memory database.
- `DUCKDB_SCHEMA_NAME`: Sets the default schema for database operations within the data api. If left unset, it defaults to the "main" schema.
- `QUERY_BLACKLIST`: Defines a comma-separated list of SQL keywords that the data api will reject to prevent potentially destructive operations. If this list is empty or not set, no commands will be blocked, and all types of queries will be permitted.

3. **Install Packages**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the project**:

   ```bash
   uvicorn main:app --reload
   ```

### Examples of `DUCKDB_DATABASE_URL` Configurations

Physical DuckDB file:

```env
DUCKDB_DATABASE_URL=duckdb:///path/to/your/database.duckdb
```
In-memory DuckDB instance:

```env
DUCKDB_DATABASE_URL=duckdb:///:memory:
```

Motherduck:

```env
DUCKDB_DATABASE_URL=duckdb:///md:[motherduck-token]@[db-name]
```

## RESTful Routes and Actions

Interact with your DuckDB database through the following RESTful routes by replacing `entity` with your table name:

| Method | Route             | Description                               | Query Parameter Examples                              |
|--------|-------------------|-------------------------------------------|-------------------------------------------------------|
| GET    | `/entity`         | List entities                             | `?limit=10&skip=20?select=field1..?order=field1 asc?field1.eq=value` |
| POST   | `/entity`         | Create a new entity                       | N/A                                                     |
| GET    | `/entity/:id`     | Get a single entity by ID                 | N/A                                                     |
| PUT    | `/entity/:id`     | Replace an entity by ID (full update)     | N/A                                                     |
| PATCH  | `/entity/:id`     | Update an entity by ID (partial update)   | N/A                                                     |
| DELETE | `/entity/:id`     | Delete an entity by ID                    | N/A                                                     |

### Query Parameter Examples

- **Filtering**: `?field1.eq=value` filters the list by `field1` equal to `value`.
- **Sorting**: `?order=field1 asc` sorts the list by `field1` in ascending order.
- **Pagination**: `?limit=10&skip=20` limits the list to 10 entities, skipping the first 20.
- **Selecting Fields**: `?select=field1,field2` selects only `field1` and `field2` to be returned in each entity in the list.

### Supported Filter Operators

The DuckDB Data Proxy supports a range of filter operators for querying data, allowing for precise data retrieval based on specific criteria:

- `.eq`: Equals
- `.neq`: Not equals
- `.gt`: Greater than
- `.gte`: Greater than or equal to
- `.lt`: Less than
- `.lte`: Less than or equal to
- `.like`: Like (for pattern matching)
- `.ilike`: Case-insensitive pattern matching

These operators can be used in query parameters to filter the data retrieved from the database. For example, `?name.like=%john%` would filter records where the `name` field contains "john".

It would be more organized to place `execute/sql` in the "Additional Endpoints" section if it serves a different or more specific purpose than the standard CRUD operations. It's common to separate utility or administrative endpoints from the main CRUD operations to clarify their use cases. Here's how you could mention it:


## Additional Endpoints

In addition to the core RESTful routes, the DuckDB Data Proxy provides several utility endpoints for diagnostics, metadata, and system health checks:

| Method | Route                  | Description                                                   | Query Parameter Examples |
|--------|------------------------|---------------------------------------------------------------|--------------------------|
| GET    | `/`                    | Root endpoint returning a welcome message.                   | N/A                      |
| GET    | `/health`              | Health check endpoint.                                        | N/A                      |
| GET    | `/debug/connection`    | Tests database connection.                                    | N/A                      |
| POST   | `/execute/sql`         | Execute a custom SQL query (SELECT or DDL statement).        | N/A                      |

The `POST /execute/sql` endpoint is for advanced users who need to execute custom SQL queries or DDL statements that are not covered by the standard CRUD operations. Please use this endpoint with caution, as improper use can affect database integrity and security.


### Complete Documentation for Metadata and Profiler Endpoints

---

### Metadata Endpoints

| Method | Route                      | Description                                   |
|--------|----------------------------|-----------------------------------------------|
| GET    | `/metadata/databases`      | Lists all databases in the current instance. |
| GET    | `/metadata/schemas`        | Lists all schemas in the current database.   |
| GET    | `/metadata/tables`         | Lists all tables in the current schema.      |
| GET    | `/metadata/columns`        | Lists all columns in the current schema.     |
| GET    | `/metadata/views`          | Lists all views in the current schema.       |
| GET    | `/metadata/constraints`    | Lists all constraints in the current schema. |

---

### `/metadata/{path:path}` Combinations

| Path Format                     | Description                                                       |
|---------------------------------|-------------------------------------------------------------------|
| `/metadata/{database}`          | Lists all schemas in the specified database.                     |
| `/metadata/{database}/{schema}` | Lists all tables in the specified schema of a database.          |
| `/metadata/{database}/{schema}/{table}` | Lists all columns in the specified table of a schema.            |
| `/metadata/{database}/{schema}/{table}/{column}` | Fetches metadata for the specific column in the specified table. |

---

### Table Info and Column Profiler Endpoints

| Method | Route                                    | Description                                                   |
|--------|------------------------------------------|---------------------------------------------------------------|
| GET    | `/metadata/{catalog}/{schema}/{table}/summarize` | Fetch statistical summaries for all columns in the table.      |
| GET    | `/metadata/{catalog}/{schema}/{table}/column/{column}/summarize` | Fetch statistical summaries for a specific column in a table. |
| GET    | `/profile`                               | Profiles a table or a specific column. Use `object=db.schema.table` or `object=db.schema.table.column`. |
| GET    | `/describe`         | Fetches metadata for a specific object using `object=db.schema.table`. |
---

## Playground
Interact with the following tables from **tickit** db: `sale`, `event`, `data`, `category`, `user`, `listing`, `venue`

### User Table API Endpoints

```plaintext
GET     https://duckdb-data-api.vercel.app/user?state.eq=NL&liketheatre=true&limit=10&offset=5&order=firstname%20asc    - List, filter, sort and paginate users
POST    https://duckdb-data-api.vercel.app/user                                                                         - Create a new user
GET     https://duckdb-data-api.vercel.app/user/{id}                                                                    - Get a single user by ID
PUT     https://duckdb-data-api.vercel.app/user/{id}                                                                    - Replace a user by ID (full update)
PATCH   https://duckdb-data-api.vercel.app/user/{id}                                                                    - Update a user by ID (partial update)
DELETE  https://duckdb-data-api.vercel.app/user/{id}                                                                    - Delete a user by ID
```

## Heads Up on Limitations

- **Performance Considerations**: Because of the way we jump from the edge to MotherDuck and back, and how we fetch data, especially when counting items for pagination, there might be a slight delay.
- **Primary Key Expectations**: Right now, we expect the primary key in your tables to be named "id". We know that’s not always the case, so we’re thinking of ways to work around this in future updates.

## Technology Stack

1. **FastAPI**:
2. **DuckDB and MotherDuck**:
3. **Python 3.9**:
4. **SQLAlchemy**:

## Architecture

```mermaid
flowchart LR
    Client -->|REST API Call| FastAPI
    FastAPI -->|SQLAlchemy ORM| DuckDB
    DuckDB -->|Process Query| MotherDuck
    MotherDuck -->|Return Results| DuckDB
    DuckDB -->|ORM| FastAPI
    FastAPI -->|JSON Response| Client

    style FastAPI fill:#f9f,stroke:#333,stroke-width:2px
    style DuckDB fill:#bbf,stroke:#333,stroke-width:2px
    style MotherDuck fill:#fbf,stroke:#333,stroke-width:2px
    style Client fill:#dfd,stroke:#333,stroke-width:2px
```

## Deployment in Vercel

Deploying your application to Vercel can significantly simplify the process, thanks to its support for serverless functions. For a detailed guide on deploying FastAPI applications to Vercel, check out this insightful [blog post](https://dev.to/mihaiandrei97/building-a-fastapi-application-and-deploying-it-with-vercel-ho7). It walks you through the steps to ensure your application runs smoothly in a serverless environment, making your DuckDB Data Proxy accessible from anywhere.


## From Goduck to DuckDB Data Proxy

### Transitioning from Golang to Python
Before diving into this Python project, I launched [Goduck](https://github.com/senthilsweb/goduck), a similar initiative built with Golang. It aimed to provide REST API interaction with DuckDB and MotherDuck, much like what we're doing here but in the Go ecosystem.

### Shifting Gears to Python
While trying to deploy Goduck across various environments, including serverless platforms, I faced hurdles due to the C-go dependency of the Go duckDB driver, which made the build process tricky for different Linux systems. This challenge highlighted the benefits of Python's straightforwardness and the extensive support from its community. Here are the main insights:

- **Simpler Python Driver**: Python's approach to DuckDB felt more straightforward and developer-friendly.
- **Larger Python Community**: The vast Python community meant more potential users and contributors for this project.
- **Inspiration from MongoDB**: MongoDB's Atlas Data Proxy, which simplifies database operations, inspired me to offer a similar experience for DuckDB users, facilitating quick backend setups for rapid prototyping.