# Agent Handoff - Mayz Monitoring

## Agent Mode
Ponytail Agent

## Current Phase
Docker Local Demo - Completed

## Current Status
- Docker compose config: PASS
- Docker build: PASS
- Backend container: PASS (/health 200, /docs 200)
- Frontend container: PASS (localhost:8080 200)
- Worker container: PASS (Idle, no crash)
- Small job test: PASS (Job TEST-20260712191542 SUCCESS)
- Database connection: PASS
- Telegram spam: none

## Small Job Results (2026-07-12)
- Job ID: TEST-20260712191542
- Status: SUCCESS
- Accounts: djpbmaluku, djpbntb, djpbaceh
- Total rows: 36
- Inserted: 14
- Login wall: 0
- Browser closed: yes

## Rules
- Do not run scraping without approval
- Do not run cold/warm/backfill
- Do not change application code
- Do not change scraper/parser
- Do not change database schema
- Do not expose secrets/passwords
- Do not stop Docker services

## Next Approved Action
Dashboard demo to mentor

## Recommended Actions (Require Approval)
1. Dashboard demo: http://localhost:8080
2. Medium test (5-10 akun)
3. Scale to full batch (34 akun)

## Forbidden
- 34 akun full scrape without approval
- Cold/warm/backfill
- Production deployment
- Schema changes


# Agent Handoff - Mayz Monitoring

## Agent Mode
Ponytail Agent

## Current Phase
Docker Local Demo - Compose Config Validation

## Current Goal
Validate Docker Compose config only.

## Rules
- Do not run docker build.
- Do not run docker compose up.
- Do not run worker.
- Do not scrape.
- Do not migrate database.
- Do not change application code.
- Do not change scraper/parser.
- Do not change database schema.
- Do not expose secrets.

## Allowed Action
Run only:

docker compose -f deployment/docker-local/docker-compose.yml --env-file deployment/docker-local/.env.docker.local config

## Not Approved Yet
- docker build
- docker compose up
- worker run
- scraping
- DB migration  