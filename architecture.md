```
                +--------------------+
                |  Client/Developer  |
                +---------+----------+
                          |
                          v
                +--------------------+
                | FastAPI Thin Layer  |  <-- Pass-Thru Proxy
                +---------+----------+
                          |
          +--------------+---------------+
          |                              |
          v                              v
+--------------------+          +--------------------+
| Kubernetes API     |          | ArgoCD API         |
| - Create Pod       |          | - Sync Apps       |
| - List Services    |          | - Rollback        |
| - Delete Namespace|          | - Get App Status  |
+--------------------+          +--------------------+
```
