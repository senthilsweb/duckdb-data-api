# DuckDB Data Proxy and Micro ORM

## Introduction

In the evolving landscape of web development and the quest for more efficient, lightweight, and scalable solutions that can run seamlessly at the edge, the DuckDB Data Proxy project emerges as a vital tool. This project is designed to provide a RESTful interface to DuckDB and MotherDuck, enabling developers to leverage the power of DuckDB directly within their side projects or edge applications. 

## Motivation

The primary motivation behind developing this data proxy and micro ORM for DuckDB and MotherDuck was to address the need for a dynamic, RESTful interface that can support a wide array of side projects. With the rise of serverless architectures and edge computing, finding a database solution that can operate efficiently in these environments has become increasingly crucial. DuckDB, known for its high performance as an in-process SQL OLAP database management system, combined with MotherDuck's ability to run DuckDB in server mode, presents an ideal solution for applications running at the edge. This project aims to simplify the interaction with DuckDB databases by offering a standardized REST interface, making it more accessible for developers to integrate robust data management capabilities into their applications.


## Getting Started

### Python Environment Setup

1. **Create a Virtual Environment**: 
   ```bash
   python3 -m venv env
   ```
2. **Activate the Virtual Environment**: 
   ```bash
   source env/bin/activate
   ```
3. **Install Dependencies**: 
   ```bash
   pip install -r requirements.txt
   ```
### Environment Configuration

To configure the DuckDB Data Proxy for your projects, following environment variables are crucial. These variables should be defined in a `.env` file located at the root of your project. Here's how to configure them effectively:

Create a `.env` file at the root of your project and include the following lines:

```env
# .env file
DUCKDB_DATABASE_URL=
DUCKDB_SCHEMA_NAME=
```

- `DUCKDB_DATABASE_URL`: This variable specifies the connection URL to your DuckDB database, Motherduck instance, or an in-memory database.
- `DUCKDB_SCHEMA_NAME`: This variable defines the schema name for the operations conducted via the data proxy. If left blank, it defaults to considering all available schemas.

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
5. **Run the Project**:

   ```bash
   uvicorn main:app --reload
   ```

6. **Freeze Installed Packages** (for sharing or deployment): 
   ```bash
   pip freeze > requirements.txt
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

## Limitations and Future Work

Currently, the DuckDB Data Proxy expects the primary key field name to be "id". This design choice aligns with common conventions but may not fit all database schemas. Recognizing this limitation, future enhancements to the project will include support for customizable primary key field names, allowing for greater flexibility and compatibility with a wider range of database designs.

## Conclusion

The DuckDB Data Proxy project represents a significant step forward in making high-performance database management accessible for edge computing and serverless applications. By providing a dynamic and easy-to-use REST interface for DuckDB and MotherDuck, it opens new possibilities for developers to integrate advanced data management into their projects with minimal overhead. As the project evolves, it will continue to expand its capabilities, offering more flexibility and options to cater to diverse data management needs.












