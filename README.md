
# QuantInvest

This project lays the foundation for an algorithmic trading platform built from scratch during a 3-month internship. It features a custom call writing strategy to evaluate F&O profitability, bulk buy/sell with square-off support, and intelligent order slicing to split large trades. Performance was boosted using LRU caching (80% faster loads), multithreading for background tasks, and stored procedures for faster DB operations. The backend uses a loosely coupled Django + DRF architecture and is fully Dockerized for easy deployment. Mathematical models were also used to compute key metrics like yield.


## Run Locally

Clone the project

```bash
  git clone https://github.com/atharva434/QuantInvest.git
```

Go to the project directory

```bash
  cd QuantInvest
```
Start the server

```bash
  docker compose up --build
```

