# new_job_project
Project for a new possible job.
curl -s -X POST http://127.0.0.1:8000/records \
  -H "Content-Type: application/json" \
  -d '{"source":"api","category":"attendance","payload":{"name":"Alice","priority":3}}' | jq .
curl -s http://127.0.0.1:8000/records/<id> | jq .
curl -s -X POST http://127.0.0.1:8000/records/<id>/process | jq .
curl -s http://127.0.0.1:8000/reports/summary | jq .
cat >> README.md <<'EX'
curl -s http://127.0.0.1:8000/reports/summary | jq .
curl -s "http://127.0.0.1:8000/reports/summary?status=processed&category=attendance" | jq .
curl -s "http://127.0.0.1:8000/records?status=pending&limit=50&offset=0" | jq .
curl -s "http://127.0.0.1:8000/records?status=pending&limit=50&offset=0" | jq .
